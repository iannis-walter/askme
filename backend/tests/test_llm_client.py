import asyncio
import json
from types import SimpleNamespace

import llm_client


def _anthropic_env(monkeypatch, **extra):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    for name in ("LLM_MODEL", "LLM_MODEL_SIMPLE", "LLM_EFFORT_SIMPLE", "LLM_EFFORT_COMPLEX", "LLM_ROUTING"):
        monkeypatch.delenv(name, raising=False)
    for k, v in extra.items():
        monkeypatch.setenv(k, v)
    return llm_client.LLMConfig()


def _usage(i=10, o=5):
    return SimpleNamespace(input_tokens=i, output_tokens=o, cache_read_input_tokens=0, cache_creation_input_tokens=0)


# --- config -------------------------------------------------------------------

def test_anthropic_tiers_default_to_haiku_and_sonnet(monkeypatch):
    cfg = _anthropic_env(monkeypatch)
    assert cfg.model_for("simple") == "claude-haiku-5-5"
    assert cfg.model_for("complex") == "claude-sonnet-5-5"
    assert cfg.effort_for("simple") == "low"
    assert cfg.effort_for("complex") == "medium"


def test_anthropic_reads_its_own_key_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-anthropic-env")
    assert llm_client.LLMConfig().api_key == "from-anthropic-env"


def test_other_providers_use_one_model_for_both_tiers(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_MODEL_SIMPLE", raising=False)
    cfg = llm_client.LLMConfig()
    assert cfg.model_for("simple") == cfg.model_for("complex") == "mistral-small-latest"


# --- message translation -------------------------------------------------------

def test_leading_system_becomes_system_param():
    system, turns = llm_client._to_anthropic(
        [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "more"},
        ]
    )
    assert system == "rules"
    assert [t["role"] for t in turns] == ["user", "assistant", "user"]


def test_consecutive_tool_results_share_one_user_turn():
    _, turns = llm_client._to_anthropic(
        [
            {"role": "system", "content": "s"},
            {"role": "user", "content": "q"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": "a", "type": "function", "function": {"name": "search_kb", "arguments": '{"query": "x"}'}},
                    {"id": "b", "type": "function", "function": {"name": "get_doc", "arguments": '{"id": "y"}'}},
                ],
            },
            {"role": "tool", "tool_call_id": "a", "name": "search_kb", "content": "r1"},
            {"role": "tool", "tool_call_id": "b", "name": "get_doc", "content": "r2"},
        ]
    )
    assert turns[1]["content"][0] == {"type": "tool_use", "id": "a", "name": "search_kb", "input": {"query": "x"}}
    assert turns[2]["role"] == "user"
    assert [b["tool_use_id"] for b in turns[2]["content"]] == ["a", "b"]


def test_raw_claude_content_is_replayed_unchanged():
    raw = [SimpleNamespace(type="thinking", thinking="", signature="sig")]
    _, turns = llm_client._to_anthropic(
        [{"role": "user", "content": "q"}, {"role": "assistant", "content": "", "_anthropic_content": raw}]
    )
    assert turns[1]["content"] is raw


# --- request building -----------------------------------------------------------

def test_complex_tier_uses_sonnet_with_fallback(monkeypatch):
    cfg = _anthropic_env(monkeypatch)
    beta, kw = llm_client._anthropic_request(cfg, [{"role": "user", "content": "q"}], "complex", max_tokens=100)
    assert beta is True
    assert kw["model"] == "claude-sonnet-5-5"
    assert kw["fallbacks"] == "default"
    assert kw["output_config"] == {"effort": "medium"}
    assert "temperature" not in kw


def test_simple_tier_uses_haiku_without_fallback(monkeypatch):
    cfg = _anthropic_env(monkeypatch)
    beta, kw = llm_client._anthropic_request(cfg, [{"role": "user", "content": "q"}], "simple", max_tokens=100)
    assert beta is False
    assert kw["model"] == "claude-haiku-5-5"
    assert "fallbacks" not in kw and "betas" not in kw


def test_tools_and_schema_are_translated(monkeypatch):
    cfg = _anthropic_env(monkeypatch)
    tools = [{"type": "function", "function": {"name": "t", "description": "d", "parameters": {"type": "object"}}}]
    schema = {"type": "json_schema", "schema": {"type": "object"}}
    _, kw = llm_client._anthropic_request(
        cfg, [{"role": "user", "content": "q"}], "complex", max_tokens=100, tools=tools, output_format=schema
    )
    assert kw["tools"] == [{"name": "t", "description": "d", "input_schema": {"type": "object"}}]
    assert kw["output_config"]["format"] == schema


# --- response translation --------------------------------------------------------

def test_tool_use_response_becomes_tool_calls():
    msg = SimpleNamespace(
        stop_reason="tool_use",
        usage=_usage(),
        content=[
            SimpleNamespace(type="thinking", thinking="", signature="s"),
            SimpleNamespace(type="tool_use", id="tu1", name="search_kb", input={"query": "rag"}),
        ],
    )
    res = llm_client._from_anthropic(msg)
    assert res.tool_calls == [
        {"id": "tu1", "type": "function", "function": {"name": "search_kb", "arguments": json.dumps({"query": "rag"})}}
    ]
    assert res.message["_anthropic_content"] == msg.content
    assert res.usage == {"prompt_tokens": 10, "completion_tokens": 5}


def test_refusal_returns_polite_text_and_no_tools():
    msg = SimpleNamespace(
        stop_reason="refusal",
        usage=_usage(),
        content=[SimpleNamespace(type="tool_use", id="x", name="search_kb", input={})],
    )
    res = llm_client._from_anthropic(msg)
    assert res.tool_calls == []
    assert res.content == llm_client.REFUSAL_TEXT


def test_truncated_tool_call_is_not_run():
    msg = SimpleNamespace(
        stop_reason="max_tokens",
        usage=_usage(),
        content=[SimpleNamespace(type="tool_use", id="x", name="search_kb", input={"query": "par"})],
    )
    assert llm_client._from_anthropic(msg).tool_calls == []


# --- routing ------------------------------------------------------------------

def test_router_skipped_for_other_providers(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    assert asyncio.run(llm_client.route_question("How many years of experience?")) == "complex"


def test_router_off_switch(monkeypatch):
    _anthropic_env(monkeypatch, LLM_ROUTING="off")
    assert asyncio.run(llm_client.route_question("How many years of experience?")) == "complex"


class _FakeMessages:
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.reply


def _fake_client(monkeypatch, messages):
    client = SimpleNamespace(messages=messages)
    client.with_options = lambda **_: client
    monkeypatch.setattr(llm_client, "_anthropic_client", lambda cfg: client)


def test_router_returns_model_choice(monkeypatch):
    _anthropic_env(monkeypatch)
    fake = _FakeMessages(
        reply=SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text='{"tier": "simple"}')])
    )
    _fake_client(monkeypatch, fake)
    assert asyncio.run(llm_client.route_question("How many years of experience?")) == "simple"
    assert fake.calls[0]["model"] == "claude-haiku-5-5"


def test_router_failure_falls_back_to_complex(monkeypatch):
    _anthropic_env(monkeypatch)
    _fake_client(monkeypatch, _FakeMessages(error=RuntimeError("boom")))
    assert asyncio.run(llm_client.route_question("Why is he a good fit?")) == "complex"
