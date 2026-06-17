"""The agentic loop.

A single function-calling loop that lets the model decide which tools to call,
how many times, until it can answer — wrapped in the guardrails a production
agent needs:

  * MAX_STEPS bounds the loop; a graceful partial answer is returned if hit.
  * a per-tool timeout and a per-LLM-call timeout cap latency.
  * tool arguments are validated (Pydantic) BEFORE execution; bad input is
    reported back to the model instead of crashing.
  * loop detection cuts off a model that calls the same tool with the same
    arguments twice.
  * every failure mode degrades to a clean answer — never a raw exception.

Two interchangeable backends keep it multi-provider: NATIVE function calling
(Mistral/Groq/OpenRouter) and a hand-parsed ReAct fallback (Ollama / small
models). The loop itself is backend-agnostic.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from pydantic import ValidationError

import llm_client
import prompts
import tools as tools_mod
from tracing import StepTrace, Trace

EventSink = Callable[[dict], Awaitable[None]]

_NATIVE_PROVIDERS = {"mistral", "groq", "openrouter"}

_FALLBACK_ANSWER = (
    "I couldn't gather enough grounded information to answer reliably. "
    "Try rephrasing, or ask about the candidate's experience, skills or projects."
)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "") or default)
    except ValueError:
        return default


@dataclass
class AgentConfig:
    max_steps: int = field(default_factory=lambda: _env_int("AGENT_MAX_STEPS", 4))
    tool_timeout_s: float = field(default_factory=lambda: _env_float("AGENT_TOOL_TIMEOUT_S", 15.0))
    llm_timeout_s: float = field(default_factory=lambda: _env_float("AGENT_LLM_TIMEOUT_S", 60.0))
    mode: str = field(default_factory=lambda: os.getenv("AGENT_MODE", "auto").lower())


@dataclass
class ProposedCall:
    """One tool invocation the model asked for, pre-validation."""

    id: str
    name: str
    raw_args: dict = field(default_factory=dict)
    parse_error: str | None = None


@dataclass
class Step:
    """One model turn: either a batch of tool calls, or the final answer."""

    kind: str  # "tool" | "final"
    calls: list[ProposedCall] = field(default_factory=list)
    final_text: str = ""
    assistant_message: dict | None = None
    usage: dict = field(default_factory=dict)
    requested_tools: list[str] = field(default_factory=list)


@dataclass
class AgentOutcome:
    answer: str
    sources: list[dict]
    truncated: bool
    trace: Trace


# --- backends ----------------------------------------------------------------

def _extract_json_object(text: str) -> dict:
    """Best-effort parse of a JSON object embedded in free text (ReAct args)."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    return json.loads(text[start : end + 1])


class NativeBackend:
    """Provider-native function calling via the `tools` parameter."""

    mode = "native"

    def __init__(self, cfg: AgentConfig):
        self.cfg = cfg
        self._specs = tools_mod.tool_specs()

    def system_prompt(self) -> str:
        return prompts.AGENT_SYSTEM

    async def step(self, messages: list[dict]) -> Step:
        res = await llm_client.complete_chat(
            messages, tools=self._specs, timeout=self.cfg.llm_timeout_s
        )
        if not res.tool_calls:
            return Step(kind="final", final_text=res.content, assistant_message=res.message, usage=res.usage)

        calls: list[ProposedCall] = []
        for tc in res.tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            raw = fn.get("arguments", "") or "{}"
            try:
                args = json.loads(raw) if isinstance(raw, str) else dict(raw)
                calls.append(ProposedCall(id=tc.get("id", name), name=name, raw_args=args))
            except (json.JSONDecodeError, TypeError):
                calls.append(
                    ProposedCall(id=tc.get("id", name), name=name, parse_error="arguments were not valid JSON")
                )
        return Step(
            kind="tool",
            calls=calls,
            assistant_message=res.message,
            usage=res.usage,
            requested_tools=[c.name for c in calls],
        )

    def append_assistant(self, messages: list[dict], step: Step) -> None:
        messages.append(step.assistant_message or {"role": "assistant", "content": ""})

    def append_tool_result(self, messages: list[dict], call: ProposedCall, wrapped: str) -> None:
        messages.append(
            {"role": "tool", "tool_call_id": call.id, "name": call.name, "content": wrapped}
        )


class ReactBackend:
    """Hand-parsed Thought/Action/Observation protocol for non-tool providers."""

    mode = "react"

    def __init__(self, cfg: AgentConfig):
        self.cfg = cfg
        self._specs = tools_mod.tool_specs()

    def system_prompt(self) -> str:
        return prompts.REACT_SYSTEM.format(tool_list=prompts.react_tool_list(self._specs))

    async def step(self, messages: list[dict]) -> Step:
        res = await llm_client.complete_chat(
            messages, stop=["Observation:"], timeout=self.cfg.llm_timeout_s
        )
        text = res.content
        assistant = {"role": "assistant", "content": text}

        if "Final Answer:" in text:
            answer = text.split("Final Answer:", 1)[1].strip()
            return Step(kind="final", final_text=answer, assistant_message=assistant, usage=res.usage)

        if "Action:" in text and "Action Input:" in text:
            name = text.split("Action:", 1)[1].split("\n", 1)[0].strip()
            after = text.split("Action Input:", 1)[1].strip()
            try:
                args = _extract_json_object(after)
                call = ProposedCall(id=f"react-{name}", name=name, raw_args=args)
            except (ValueError, json.JSONDecodeError):
                call = ProposedCall(id=f"react-{name}", name=name, parse_error="Action Input was not valid JSON")
            return Step(
                kind="tool", calls=[call], assistant_message=assistant, usage=res.usage, requested_tools=[name]
            )

        # No protocol markers: treat whatever the model said as the final answer.
        return Step(kind="final", final_text=text.strip(), assistant_message=assistant, usage=res.usage)

    def append_assistant(self, messages: list[dict], step: Step) -> None:
        messages.append(step.assistant_message or {"role": "assistant", "content": ""})

    def append_tool_result(self, messages: list[dict], call: ProposedCall, wrapped: str) -> None:
        # ReAct convention: the observation re-enters as the next user turn.
        messages.append({"role": "user", "content": f"Observation: {wrapped}"})


def select_backend(cfg: AgentConfig, provider: str):
    if cfg.mode == "native":
        return NativeBackend(cfg)
    if cfg.mode == "react":
        return ReactBackend(cfg)
    # auto
    return NativeBackend(cfg) if provider in _NATIVE_PROVIDERS else ReactBackend(cfg)


# --- the loop ----------------------------------------------------------------

def _ms_since(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


async def run_agent(
    question: str,
    history: list[dict],
    ctx: tools_mod.ToolContext,
    *,
    request_id: str,
    cfg: AgentConfig | None = None,
    backend=None,
    on_event: EventSink | None = None,
) -> AgentOutcome:
    cfg = cfg or AgentConfig()
    provider = llm_client.LLMConfig().provider
    model = llm_client.LLMConfig().model
    backend = backend or select_backend(cfg, provider)

    trace = Trace(
        request_id=request_id,
        provider=provider,
        model=model,
        mode=getattr(backend, "mode", "native"),
        question=question,
        max_steps=cfg.max_steps,
    )

    messages = prompts.build_agent_messages(question, history, backend.system_prompt())
    seen_calls: set[str] = set()
    sources: "OrderedDict[str, dict]" = OrderedDict()

    async def emit(event: dict) -> None:
        if on_event is not None:
            await on_event(event)

    async def add_sources(new: list[dict]) -> None:
        changed = False
        for src in new:
            if src["id"] not in sources:
                sources[src["id"]] = src
                changed = True
        if changed:
            await emit({"type": "sources", "sources": list(sources.values())})

    for step_idx in range(cfg.max_steps):
        # --- model turn ---
        t0 = time.monotonic()
        try:
            step = await backend.step(messages)
        except Exception as exc:  # noqa: BLE001 - any provider/transport error degrades gracefully
            trace.add_step(StepTrace(index=step_idx, kind="llm", latency_ms=_ms_since(t0), error=str(exc)[:300]))
            trace.stop_reason = "error"
            trace.truncated = True
            answer = _FALLBACK_ANSWER
            trace.finish(answer)
            return AgentOutcome(answer=answer, sources=list(sources.values()), truncated=True, trace=trace)

        usage = step.usage or {}
        trace.add_step(
            StepTrace(
                index=step_idx,
                kind="llm",
                latency_ms=_ms_since(t0),
                tokens_in=int(usage.get("prompt_tokens", 0) or 0),
                tokens_out=int(usage.get("completion_tokens", 0) or 0),
                requested_tools=step.requested_tools,
            )
        )

        if step.kind == "final":
            trace.stop_reason = "completed"
            trace.finish(step.final_text)
            return AgentOutcome(
                answer=step.final_text or _FALLBACK_ANSWER,
                sources=list(sources.values()),
                truncated=False,
                trace=trace,
            )

        # --- tool turn ---
        backend.append_assistant(messages, step)
        looped = False
        for call in step.calls:
            tool_t0 = time.monotonic()
            tool = tools_mod.get_tool(call.name)

            # unknown tool
            if tool is None:
                content = f"Unknown tool '{call.name}'. Available: {', '.join(t.name for t in tools_mod.all_tools())}."
                await self_emit_tool(emit, trace, step_idx, call, ok=False, content=content, t0=tool_t0)
                backend.append_tool_result(messages, call, prompts.wrap_tool_result(call.name, content))
                continue

            # model produced unparseable arguments
            if call.parse_error:
                content = f"Invalid arguments for {call.name}: {call.parse_error}. Retry with valid JSON."
                await self_emit_tool(emit, trace, step_idx, call, ok=False, content=content, t0=tool_t0)
                backend.append_tool_result(messages, call, prompts.wrap_tool_result(call.name, content))
                continue

            # validate BEFORE executing
            try:
                args = tool.validate(call.raw_args)
            except ValidationError as exc:
                content = tools_mod.validation_error_message(call.name, exc)
                await self_emit_tool(emit, trace, step_idx, call, ok=False, content=content, t0=tool_t0)
                backend.append_tool_result(messages, call, prompts.wrap_tool_result(call.name, content))
                continue

            # loop detection (same tool + same validated args). Close the call
            # with a notice instead of leaving a dangling tool_call — a dangling
            # call would make the message sequence invalid for the final turn.
            signature = call.name + ":" + json.dumps(args.model_dump(), sort_keys=True)
            if signature in seen_calls:
                looped = True
                content = (
                    f"Duplicate call: '{call.name}' was already run with these exact arguments. "
                    "Do not repeat it — answer now using what you already have."
                )
                await self_emit_tool(
                    emit, trace, step_idx, call, ok=False, content=content, t0=tool_t0, args_dump=args.model_dump()
                )
                backend.append_tool_result(messages, call, prompts.wrap_tool_result(call.name, content))
                continue
            seen_calls.add(signature)

            # execute, isolated + time-bounded
            try:
                result = await asyncio.wait_for(tool.handler(args, ctx), timeout=cfg.tool_timeout_s)
                ok, content, new_sources = result.ok, result.content, result.sources
            except asyncio.TimeoutError:
                ok, content, new_sources = False, f"Tool {call.name} timed out after {cfg.tool_timeout_s:.0f}s.", []
            except Exception as exc:  # noqa: BLE001 - a tool must never crash the loop
                ok, content, new_sources = False, f"Tool {call.name} failed: {exc}", []

            await self_emit_tool(
                emit, trace, step_idx, call, ok=ok, content=content, t0=tool_t0, args_dump=args.model_dump()
            )
            backend.append_tool_result(messages, call, prompts.wrap_tool_result(call.name, content))
            if new_sources:
                await add_sources(new_sources)

        if looped:
            trace.stop_reason = "loop_detected"
            break

    # --- exhausted MAX_STEPS or cut for a loop: graceful partial answer ---
    trace.truncated = True
    if trace.stop_reason == "completed":
        trace.stop_reason = "max_steps"
    answer = await _finalize_partial(messages, backend, cfg)
    trace.finish(answer)
    return AgentOutcome(answer=answer, sources=list(sources.values()), truncated=True, trace=trace)


async def self_emit_tool(
    emit: EventSink,
    trace: Trace,
    step_idx: int,
    call: ProposedCall,
    *,
    ok: bool,
    content: str,
    t0: float,
    args_dump: dict | None = None,
) -> None:
    """Record a tool step in the trace and stream it to the client."""
    st = StepTrace(
        index=step_idx,
        kind="tool",
        latency_ms=_ms_since(t0),
        tool=call.name,
        args=args_dump if args_dump is not None else call.raw_args,
        ok=ok,
    )
    st.set_result(content)
    trace.add_step(st)
    await emit(
        {
            "type": "step",
            "index": step_idx,
            "tool": call.name,
            "args": st.args,
            "ok": ok,
            "error": None if ok else content[:300],
        }
    )


async def _finalize_partial(messages: list[dict], backend, cfg: AgentConfig) -> str:
    """Ask the model for its best grounded answer now, tools disabled.

    Used when the loop is cut short (MAX_STEPS or a detected loop). If even this
    call fails, fall back to a static, honest message — never an exception.
    """
    nudge = list(messages) + [
        {
            "role": "user",
            "content": (
                "Stop using tools and answer now. Use ONLY facts you actually retrieved above. "
                "Do NOT invent or guess anything you did not retrieve — no locations, employers, "
                "dates or metrics that are not in the tool results. If part of the question is not "
                "supported by what you gathered, say plainly that you don't have that information. "
                "Be concise."
            ),
        }
    ]
    try:
        res = await llm_client.complete_chat(nudge, timeout=cfg.llm_timeout_s)
        return res.content.strip() or _FALLBACK_ANSWER
    except Exception:  # noqa: BLE001
        return _FALLBACK_ANSWER
