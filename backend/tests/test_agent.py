import asyncio

import agent
import llm_client
import tools
from agent import AgentConfig, ProposedCall, Step
from content_loader import Chunk, Document


class FakeRetriever:
    def __init__(self, chunks=None, delay=0.0):
        self._chunks = chunks if chunks is not None else [
            Chunk("vigie", "Vigie", "project", "COCO-SSD computer vision")
        ]
        self.delay = delay

    async def retrieve(self, query, k=6):
        if self.delay:
            await asyncio.sleep(self.delay)
        return [(c, 1.0) for c in self._chunks[:k]]


def _ctx(retriever=None):
    return tools.ToolContext(
        retriever=retriever or FakeRetriever(),
        docs=[Document("bio", "Bio", "bio", "x")],
    )


class ScriptedBackend:
    """Feeds the loop a fixed list of Steps; loops on the last one if exhausted."""

    mode = "native"

    def __init__(self, steps, repeat_last=False):
        self._steps = list(steps)
        self.repeat_last = repeat_last
        self._last = steps[-1] if steps else Step(kind="final", final_text="done")

    def system_prompt(self):
        return "SYS"

    async def step(self, messages):
        if self._steps:
            self._last = self._steps.pop(0)
            return self._last
        return self._last if self.repeat_last else Step(kind="final", final_text="done")

    def append_assistant(self, messages, step):
        messages.append({"role": "assistant", "content": "x"})

    def append_tool_result(self, messages, call, wrapped):
        messages.append({"role": "tool", "content": wrapped})


def _run(backend, ctx=None, cfg=None, events=None):
    ctx = ctx or _ctx()

    async def on_event(evt):
        if events is not None:
            events.append(evt)

    return asyncio.run(
        agent.run_agent(
            "Tell me about the candidate", [], ctx,
            request_id="test", backend=backend, cfg=cfg, on_event=on_event,
        )
    )


def _tool_step(name, args):
    return Step(kind="tool", calls=[ProposedCall(id=f"c-{name}", name=name, raw_args=args)], requested_tools=[name])


def test_happy_path_tool_then_answer():
    events = []
    backend = ScriptedBackend([
        _tool_step("search_kb", {"query": "computer vision", "top_k": 3}),
        Step(kind="final", final_text="He shipped Vigie, on-device computer vision."),
    ])
    outcome = _run(backend, events=events)

    assert not outcome.truncated
    assert "Vigie" in outcome.answer
    assert outcome.trace.stop_reason == "completed"
    assert any(s.kind == "tool" and s.tool == "search_kb" for s in outcome.trace.steps)
    assert {s["id"] for s in outcome.sources} == {"vigie"}
    assert any(e["type"] == "step" for e in events)
    assert any(e["type"] == "sources" for e in events)


def test_max_steps_triggers_graceful_partial(monkeypatch):
    async def fake_complete_chat(messages, **kwargs):
        return llm_client.ChatResult(message={"role": "assistant", "content": "Partial but honest answer."})

    monkeypatch.setattr(llm_client, "complete_chat", fake_complete_chat)
    # Always asks for a tool, never a final step -> the loop runs out of steps.
    backend = ScriptedBackend(
        [_tool_step("search_kb", {"query": f"q{i}"}) for i in range(10)]
    )
    cfg = AgentConfig(max_steps=3)
    outcome = _run(backend, cfg=cfg)

    assert outcome.truncated
    assert outcome.trace.stop_reason == "max_steps"
    assert outcome.answer == "Partial but honest answer."


def test_loop_detection_cuts_repeated_call(monkeypatch):
    async def fake_complete_chat(messages, **kwargs):
        return llm_client.ChatResult(message={"role": "assistant", "content": "stopped on a loop"})

    monkeypatch.setattr(llm_client, "complete_chat", fake_complete_chat)
    same = {"query": "same", "top_k": 4}
    backend = ScriptedBackend([_tool_step("search_kb", same), _tool_step("search_kb", same)])
    outcome = _run(backend, cfg=AgentConfig(max_steps=5))

    assert outcome.truncated
    assert outcome.trace.stop_reason == "loop_detected"


def test_invalid_args_reported_not_crashed():
    backend = ScriptedBackend([
        _tool_step("search_kb", {"query": "x", "top_k": 999}),  # invalid: top_k > 8
        Step(kind="final", final_text="answer after recovering"),
    ])
    outcome = _run(backend)

    assert not outcome.truncated
    assert outcome.answer == "answer after recovering"
    bad = [s for s in outcome.trace.steps if s.kind == "tool"][0]
    assert bad.ok is False and "top_k" in (bad.result_preview or "")


def test_unparseable_args_reported():
    call = ProposedCall(id="c", name="search_kb", parse_error="arguments were not valid JSON")
    backend = ScriptedBackend([
        Step(kind="tool", calls=[call], requested_tools=["search_kb"]),
        Step(kind="final", final_text="recovered"),
    ])
    outcome = _run(backend)
    assert outcome.answer == "recovered"
    assert any(s.kind == "tool" and s.ok is False for s in outcome.trace.steps)


def test_unknown_tool_reported():
    backend = ScriptedBackend([
        _tool_step("nonexistent_tool", {}),
        Step(kind="final", final_text="ok"),
    ])
    outcome = _run(backend)
    assert outcome.answer == "ok"
    bad = [s for s in outcome.trace.steps if s.kind == "tool"][0]
    assert bad.ok is False and "Unknown tool" in (bad.result_preview or "")


def test_tool_timeout_is_caught():
    backend = ScriptedBackend([
        _tool_step("search_kb", {"query": "slow", "top_k": 2}),
        Step(kind="final", final_text="answered despite timeout"),
    ])
    ctx = _ctx(retriever=FakeRetriever(delay=0.2))
    outcome = _run(backend, ctx=ctx, cfg=AgentConfig(tool_timeout_s=0.01))

    assert outcome.answer == "answered despite timeout"
    bad = [s for s in outcome.trace.steps if s.kind == "tool"][0]
    assert bad.ok is False and "timed out" in (bad.result_preview or "")


def test_llm_error_degrades_gracefully():
    class BoomBackend(ScriptedBackend):
        async def step(self, messages):
            raise RuntimeError("provider down")

    outcome = _run(BoomBackend([Step(kind="final", final_text="never")]))
    assert outcome.truncated
    assert outcome.trace.stop_reason == "error"


# --- ReAct backend parsing ---------------------------------------------------

def _react_with(content, monkeypatch):
    async def fake_complete_chat(messages, **kwargs):
        return llm_client.ChatResult(message={"role": "assistant", "content": content})

    monkeypatch.setattr(llm_client, "complete_chat", fake_complete_chat)
    backend = agent.ReactBackend(AgentConfig())
    return asyncio.run(backend.step([]))


def test_react_parses_action(monkeypatch):
    step = _react_with(
        'Thought: I should search.\nAction: search_kb\nAction Input: {"query": "vision", "top_k": 3}',
        monkeypatch,
    )
    assert step.kind == "tool"
    assert step.calls[0].name == "search_kb"
    assert step.calls[0].raw_args == {"query": "vision", "top_k": 3}


def test_react_parses_final_answer(monkeypatch):
    step = _react_with("Thought: I know this.\nFinal Answer: He is a full-stack engineer.", monkeypatch)
    assert step.kind == "final"
    assert step.final_text == "He is a full-stack engineer."


def test_react_bad_action_input_flagged(monkeypatch):
    step = _react_with("Action: search_kb\nAction Input: not-json", monkeypatch)
    assert step.kind == "tool" and step.calls[0].parse_error


def test_react_plain_text_is_final(monkeypatch):
    step = _react_with("He is based in Aix-en-Provence.", monkeypatch)
    assert step.kind == "final" and "Aix" in step.final_text


# --- backend selection -------------------------------------------------------

def test_select_backend_auto_by_provider():
    assert agent.select_backend(AgentConfig(mode="auto"), "mistral").mode == "native"
    assert agent.select_backend(AgentConfig(mode="auto"), "ollama").mode == "react"
    assert agent.select_backend(AgentConfig(mode="react"), "mistral").mode == "react"
    assert agent.select_backend(AgentConfig(mode="native"), "ollama").mode == "native"
