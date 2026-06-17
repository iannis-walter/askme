"""Structured tracing for the agent loop.

One `Trace` per request, holding an ordered list of steps (LLM turns and tool
calls) with latency, tokens and truncated previews. This is what lets us answer
"how do you debug an agent?" — every decision the model made is recorded and
exposed at `/trace/{request_id}`.

The store is a tiny in-memory ring buffer. Traces are an observability aid, not
durable state, so a bounded dict is enough and keeps the service dependency-free.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass, field

_PREVIEW_CHARS = 600


def _preview(text: str, limit: int = _PREVIEW_CHARS) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + f"… (+{len(text) - limit} chars)"


@dataclass
class StepTrace:
    """A single step in the loop: an LLM turn or a tool execution."""

    index: int
    kind: str  # "llm" | "tool"
    latency_ms: int = 0
    # LLM-step fields
    tokens_in: int = 0
    tokens_out: int = 0
    requested_tools: list[str] = field(default_factory=list)
    # Tool-step fields
    tool: str | None = None
    args: dict | None = None
    ok: bool | None = None
    result_preview: str | None = None
    error: str | None = None

    def set_result(self, value: str) -> None:
        self.result_preview = _preview(value)


@dataclass
class Trace:
    """The full record of one agent request."""

    request_id: str
    provider: str
    model: str
    mode: str  # "native" | "react"
    question: str
    max_steps: int
    steps: list[StepTrace] = field(default_factory=list)
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_latency_ms: int = 0
    truncated: bool = False
    stop_reason: str = "completed"  # completed | max_steps | loop_detected | error
    final_answer_preview: str = ""

    def add_step(self, step: StepTrace) -> StepTrace:
        self.steps.append(step)
        self.total_latency_ms += step.latency_ms
        self.total_tokens_in += step.tokens_in
        self.total_tokens_out += step.tokens_out
        return step

    def finish(self, answer: str) -> None:
        self.final_answer_preview = _preview(answer)

    def to_dict(self) -> dict:
        return asdict(self)


class TraceStore:
    """Bounded in-memory store, newest-wins eviction."""

    def __init__(self, capacity: int = 200):
        self._capacity = capacity
        self._traces: OrderedDict[str, Trace] = OrderedDict()

    def put(self, trace: Trace) -> None:
        self._traces[trace.request_id] = trace
        self._traces.move_to_end(trace.request_id)
        while len(self._traces) > self._capacity:
            self._traces.popitem(last=False)

    def get(self, request_id: str) -> Trace | None:
        return self._traces.get(request_id)
