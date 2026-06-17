import asyncio

import pytest
from pydantic import ValidationError

import tools
from content_loader import Chunk, Document


class FakeRetriever:
    """Returns canned (chunk, score) pairs; records the last query/k."""

    def __init__(self, chunks):
        self._chunks = chunks
        self.calls = []

    async def retrieve(self, query, k=6):
        self.calls.append((query, k))
        return [(c, 1.0 - i * 0.1) for i, c in enumerate(self._chunks[:k])]


def _ctx(chunks=None, docs=None, complete_json=None):
    chunks = chunks if chunks is not None else [
        Chunk("vigie", "Vigie", "project", "COCO-SSD on-device computer vision"),
        Chunk("bio", "Bio", "bio", "Iannis Vasselet, full-stack engineer"),
    ]
    kwargs = {}
    if complete_json is not None:
        kwargs["complete_json"] = complete_json
    return tools.ToolContext(
        retriever=FakeRetriever(chunks),
        docs=docs if docs is not None else [Document("bio", "Bio", "bio", "x")],
        **kwargs,
    )


def test_search_kb_returns_content_and_sources():
    ctx = _ctx()
    tool = tools.get_tool("search_kb")
    args = tool.validate({"query": "computer vision", "top_k": 2})
    result = asyncio.run(tool.handler(args, ctx))
    assert result.ok
    assert "COCO-SSD" in result.content
    assert {s["id"] for s in result.sources} == {"vigie", "bio"}
    assert ctx.retriever.calls == [("computer vision", 2)]


def test_search_kb_no_results_is_ok():
    ctx = _ctx(chunks=[])
    tool = tools.get_tool("search_kb")
    args = tool.validate({"query": "nothing"})
    result = asyncio.run(tool.handler(args, ctx))
    assert result.ok and "No matching" in result.content


@pytest.mark.parametrize("bad", [{"query": ""}, {"query": "x", "top_k": 0}, {"query": "x", "top_k": 99}, {}])
def test_search_kb_rejects_invalid_args(bad):
    tool = tools.get_tool("search_kb")
    with pytest.raises(ValidationError):
        tool.validate(bad)


def test_list_topics_groups_by_kind():
    docs = [
        Document("bio", "Bio", "bio", "x"),
        Document("p1", "Vigie", "project", "x"),
        Document("p2", "Aria", "project", "x"),
    ]
    ctx = _ctx(docs=docs)
    tool = tools.get_tool("list_topics")
    args = tool.validate({})
    result = asyncio.run(tool.handler(args, ctx))
    assert result.ok
    assert "project: Vigie, Aria" in result.content
    assert "bio: Bio" in result.content


def test_evaluate_job_fit_uses_injected_llm():
    async def fake_complete_json(messages):
        return {"summary": "strong fit", "strengths": ["python"], "gaps": ["llm years"]}

    ctx = _ctx(complete_json=fake_complete_json)
    tool = tools.get_tool("evaluate_job_fit")
    args = tool.validate({"job_description": "Applied AI Engineer, Python + TS"})
    result = asyncio.run(tool.handler(args, ctx))
    assert result.ok
    assert "strong fit" in result.content and "python" in result.content


def test_tool_spec_is_openai_compatible():
    spec = tools.get_tool("search_kb").spec()
    assert spec["type"] == "function"
    assert spec["function"]["name"] == "search_kb"
    props = spec["function"]["parameters"]["properties"]
    assert "query" in props and "top_k" in props


def test_validation_error_message_is_compact():
    tool = tools.get_tool("search_kb")
    try:
        tool.validate({"query": "x", "top_k": 99})
    except ValidationError as exc:
        msg = tools.validation_error_message("search_kb", exc)
        assert "search_kb" in msg and "top_k" in msg
    else:
        raise AssertionError("expected ValidationError")
