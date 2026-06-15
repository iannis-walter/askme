import asyncio
import hashlib
import math

import embeddings
from content_loader import Chunk


def test_l2_normalize_unit_length():
    v = embeddings.l2_normalize([3.0, 4.0])
    assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, rel_tol=1e-9)


def test_l2_normalize_zero_vector_is_safe():
    assert embeddings.l2_normalize([0.0, 0.0]) == [0.0, 0.0]


def test_cosine_identical_is_one():
    assert math.isclose(embeddings.cosine([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]), 1.0, rel_tol=1e-9)


def test_cosine_orthogonal_is_zero():
    assert math.isclose(embeddings.cosine([1.0, 0.0], [0.0, 1.0]), 0.0, abs_tol=1e-9)


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeClient:
    captured = {}

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def post(self, url, json=None, headers=None):
        _FakeClient.captured = {"url": url, "json": json, "headers": headers}
        # Echo a 2-d vector per input so callers can assert ordering/count.
        return _FakeResponse({"data": [{"embedding": [float(i), 1.0]} for i, _ in enumerate(json["input"])]})


def test_embed_texts_batches_and_parses(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setattr(embeddings.httpx, "AsyncClient", _FakeClient)

    vectors = asyncio.run(embeddings.embed_texts(["alpha", "beta"]))

    assert vectors == [[0.0, 1.0], [1.0, 1.0]]
    assert _FakeClient.captured["json"]["input"] == ["alpha", "beta"]
    assert _FakeClient.captured["headers"]["Authorization"] == "Bearer test-key"


async def _fake_embed(texts):
    # Deterministic bag-of-words vector: stable across processes.
    dim = 32
    out = []
    for t in texts:
        v = [0.0] * dim
        for tok in t.lower().split():
            idx = int(hashlib.sha1(tok.encode()).hexdigest(), 16) % dim
            v[idx] += 1.0
        out.append(v)
    return out


def test_cache_key_changes_with_text():
    a = embeddings.cache_key("hello", "mistral-embed")
    b = embeddings.cache_key("hello!", "mistral-embed")
    assert a != b
    assert a.endswith(":mistral-embed")


def test_resolve_uses_cache_and_embeds_missing(monkeypatch):
    monkeypatch.setattr(embeddings, "embed_texts", _fake_embed)
    chunks = [
        Chunk("a", "A", "faq", "machine learning python"),
        Chunk("b", "B", "faq", "swift ios mobile"),
    ]
    model = embeddings._embed_model()
    # Pre-seed the cache for the first chunk only.
    seeded = asyncio.run(_fake_embed([chunks[0].text]))[0]
    cache = {embeddings.cache_key(chunks[0].text, model): seeded}

    vectors = asyncio.run(embeddings.resolve_chunk_vectors(chunks, cache))

    assert len(vectors) == 2
    # Normalised → unit length.
    assert math.isclose(math.sqrt(sum(x * x for x in vectors[0])), 1.0, rel_tol=1e-9)
