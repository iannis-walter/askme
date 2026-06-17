"""The tools the agent can call.

Each tool wraps existing project capabilities — the retriever, the knowledge
base, the job-fit logic — behind a validated, self-describing interface. Three
things make a tool production-grade here:

  * a Pydantic argument model (validated BEFORE the handler runs),
  * a clear description the model reads to decide when to call it,
  * isolated execution: the agent loop runs every handler under a timeout and
    a catch-all, turning any failure into a `ToolResult(ok=False, ...)` the
    model can read and recover from — a tool never crashes the loop.

Tools depend on a `ToolContext`, not on global server state, so they can be
exercised in isolation by the test suite and the eval runner.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError

import llm_client
import prompts


@dataclass
class ToolContext:
    """Everything the tools need to run, injected rather than imported.

    `retriever` and `docs` come from the loaded knowledge base. `complete_json`
    is the LLM entry point for the job-fit tool — injectable so tests can stub
    the model out.
    """

    retriever: Any
    docs: list[Any]
    complete_json: Callable[[list[dict]], Awaitable[dict]] = llm_client.complete_json


@dataclass
class ToolResult:
    """What a tool hands back to the loop.

    `content` is the text fed to the model (untrusted data — the loop delimits
    it). `sources` surfaces any KB documents touched, so the UI can cite them.
    """

    ok: bool
    content: str
    sources: list[dict] = field(default_factory=list)


# --- argument schemas --------------------------------------------------------

class SearchKbArgs(BaseModel):
    """Search the candidate's knowledge base for relevant passages."""

    query: str = Field(..., min_length=1, max_length=400, description="A focused search query.")
    top_k: int = Field(4, ge=1, le=8, description="How many passages to return (1-8).")


class ListTopicsArgs(BaseModel):
    """List the high-level themes available in the knowledge base. No arguments."""


class EvaluateJobFitArgs(BaseModel):
    """Assess how the candidate fits a specific job description."""

    job_description: str = Field(..., min_length=1, max_length=8000, description="The target job post text.")


# --- handlers ----------------------------------------------------------------

def _sources_from_scored(scored) -> list[dict]:
    seen: OrderedDict[str, dict] = OrderedDict()
    for chunk, score in scored:
        if chunk.source_id not in seen:
            seen[chunk.source_id] = {
                "id": chunk.source_id,
                "title": chunk.source_title,
                "kind": chunk.source_kind,
                "score": round(float(score), 3),
            }
    return list(seen.values())


async def _run_search_kb(args: SearchKbArgs, ctx: ToolContext) -> ToolResult:
    scored = await ctx.retriever.retrieve(args.query, k=args.top_k)
    if not scored:
        return ToolResult(ok=True, content=f"No matching passages for query: {args.query!r}.")
    blocks = [
        f"[{chunk.source_id}] ({chunk.source_title})\n{chunk.text}"
        for chunk, _ in scored
    ]
    return ToolResult(
        ok=True,
        content="\n\n---\n\n".join(blocks),
        sources=_sources_from_scored(scored),
    )


async def _run_list_topics(args: ListTopicsArgs, ctx: ToolContext) -> ToolResult:
    by_kind: OrderedDict[str, list[str]] = OrderedDict()
    for doc in ctx.docs:
        by_kind.setdefault(doc.kind, [])
        if doc.title not in by_kind[doc.kind]:
            by_kind[doc.kind].append(doc.title)
    lines = [f"{kind}: {', '.join(titles)}" for kind, titles in by_kind.items()]
    return ToolResult(ok=True, content="Knowledge base topics by section:\n" + "\n".join(lines))


async def _run_evaluate_job_fit(args: EvaluateJobFitArgs, ctx: ToolContext) -> ToolResult:
    scored = await ctx.retriever.retrieve(args.job_description, k=10)
    chunks = [chunk for chunk, _ in scored]
    messages = prompts.build_job_fit_messages(args.job_description, None, chunks)
    data = await ctx.complete_json(messages)
    summary = data.get("summary", "")
    strengths = data.get("strengths", []) or []
    gaps = data.get("gaps", []) or []
    content = (
        f"Fit summary: {summary}\n"
        f"Strengths: {'; '.join(strengths) or 'n/a'}\n"
        f"Gaps: {'; '.join(gaps) or 'n/a'}"
    )
    return ToolResult(ok=True, content=content, sources=_sources_from_scored(scored))


# --- registry ----------------------------------------------------------------

@dataclass
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[BaseModel, ToolContext], Awaitable[ToolResult]]

    def spec(self) -> dict:
        """OpenAI/Mistral-compatible tool definition for the `tools` param."""
        schema = self.args_model.model_json_schema()
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }

    def validate(self, raw: dict) -> BaseModel:
        """Validate raw arguments. Raises ValidationError on bad input."""
        return self.args_model.model_validate(raw)


_TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        Tool(
            name="search_kb",
            description=(
                "Search the candidate's knowledge base (bio, experience, skills, FAQ, "
                "projects, role notes) for passages relevant to a query. Call it MULTIPLE "
                "times with different queries to gather everything you need before answering."
            ),
            args_model=SearchKbArgs,
            handler=_run_search_kb,
        ),
        Tool(
            name="list_topics",
            description=(
                "List the high-level themes and documents available in the knowledge base. "
                "Use it first when a question is broad or you are unsure what exists."
            ),
            args_model=ListTopicsArgs,
            handler=_run_list_topics,
        ),
        Tool(
            name="evaluate_job_fit",
            description=(
                "Assess how the candidate fits a specific job description, returning a short "
                "summary with strengths and gaps. Use it only when the user supplies an actual "
                "job posting to evaluate against."
            ),
            args_model=EvaluateJobFitArgs,
            handler=_run_evaluate_job_fit,
        ),
    ]
}


def get_tool(name: str) -> Tool | None:
    return _TOOLS.get(name)


def all_tools() -> list[Tool]:
    return list(_TOOLS.values())


def tool_specs() -> list[dict]:
    """The `tools` array passed to a native function-calling model."""
    return [t.spec() for t in _TOOLS.values()]


def validation_error_message(name: str, exc: ValidationError) -> str:
    """A compact, model-readable description of why arguments were rejected."""
    problems = "; ".join(
        f"{'.'.join(str(p) for p in e['loc']) or 'arguments'}: {e['msg']}"
        for e in exc.errors()
    )
    return f"Invalid arguments for {name}: {problems}. Fix the arguments and try again."
