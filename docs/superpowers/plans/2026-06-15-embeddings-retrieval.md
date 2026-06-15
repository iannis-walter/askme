# Mistral Embeddings Retrieval — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace keyword+IDF retrieval with semantic retrieval via `mistral-embed`, behind the existing retriever interface, with a committed embedding cache and keyword fallback.

**Architecture:** A new `embeddings.py` (HTTP + vector math) and an `EmbeddingRetriever` in `retrieve.py` sit alongside the existing keyword `Retriever`. Chunk vectors are precomputed by a script into a committed, content-hash-keyed `embeddings.json` (baked into the image → instant cold start). A `build_retriever` factory picks embeddings (Mistral + key) or keyword (Ollama/no key), and falls back to keyword if a query embedding fails. The retriever interface becomes `async` (correct for I/O in async FastAPI handlers); `main.py` awaits it.

**Tech Stack:** Python, FastAPI, httpx (async), Mistral embeddings API, pytest.

---

## Deviation from spec (intentional)

The spec said `retrieve()` stays sync. Embedding the query is a network call, and a blocking sync call inside an async FastAPI handler would stall the event loop. So `retrieve()` becomes `async def` on **both** retrievers, and `main.py` awaits it (2-line change). No route/schema change — the spec's intent (drop-in retriever, no API change) holds.

## File structure

- Create `backend/embeddings.py` — embedding HTTP call + vector math + cache helpers
- Create `backend/build_embeddings.py` — one-off script to generate `embeddings.json`
- Create `backend/embeddings.json` — committed cache (generated in Task 7)
- Modify `backend/retrieve.py` — `Retriever.retrieve` → async; add `EmbeddingRetriever`, `build_retriever`
- Modify `backend/main.py` — lifespan uses `await build_retriever(...)`; endpoints `await retriever.retrieve(...)`
- Create `backend/conftest.py` — put `backend/` on `sys.path` for tests
- Create `backend/tests/test_embeddings.py`, `backend/tests/test_retrieve.py`
- Create `backend/requirements-dev.txt` — `pytest`
- Modify `backend/.env.example`, `render.yaml`, `README.md` — document `RETRIEVER`, `LLM_EMBED_MODEL`, regen step

---

## Task 1: Vector math + test scaffolding

**Files:**
- Create: `backend/requirements-dev.txt`, `backend/conftest.py`, `backend/embeddings.py`, `backend/tests/test_embeddings.py`

- [ ] **Step 1: Add dev deps + conftest**

`backend/requirements-dev.txt`:
```
pytest==8.3.4
```

`backend/conftest.py`:
```python
import os
import sys

# Make the flat backend modules importable from tests/.
sys.path.insert(0, os.path.dirname(__file__))
```

Install: `cd backend && ../.venv/bin/pip install -r requirements-dev.txt`

- [ ] **Step 2: Write the failing test**

`backend/tests/test_embeddings.py`:
```python
import math

import embeddings


def test_l2_normalize_unit_length():
    v = embeddings.l2_normalize([3.0, 4.0])
    assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, rel_tol=1e-9)


def test_l2_normalize_zero_vector_is_safe():
    assert embeddings.l2_normalize([0.0, 0.0]) == [0.0, 0.0]


def test_cosine_identical_is_one():
    assert math.isclose(embeddings.cosine([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]), 1.0, rel_tol=1e-9)


def test_cosine_orthogonal_is_zero():
    assert math.isclose(embeddings.cosine([1.0, 0.0], [0.0, 1.0]), 0.0, abs_tol=1e-9)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && ../.venv/bin/pytest tests/test_embeddings.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'embeddings'`

- [ ] **Step 4: Write minimal implementation**

`backend/embeddings.py`:
```python
"""Embedding HTTP calls, vector math, and the on-disk embedding cache.

Semantic retrieval uses Mistral's OpenAI-compatible embeddings endpoint. Vectors
are L2-normalised on load so cosine similarity reduces to a dot product.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import httpx

import llm_client


def l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return list(vec)
    return [x / norm for x in vec]


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def cosine(a: list[float], b: list[float]) -> float:
    return dot(l2_normalize(a), l2_normalize(b))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && ../.venv/bin/pytest tests/test_embeddings.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/requirements-dev.txt backend/conftest.py backend/embeddings.py backend/tests/test_embeddings.py
git commit -m "feat(embeddings): vector math + test scaffolding"
```

---

## Task 2: `embed_texts` HTTP call

**Files:**
- Modify: `backend/embeddings.py`
- Modify: `backend/tests/test_embeddings.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_embeddings.py`:
```python
import asyncio
import json as _json


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../.venv/bin/pytest tests/test_embeddings.py::test_embed_texts_batches_and_parses -v`
Expected: FAIL — `AttributeError: module 'embeddings' has no attribute 'embed_texts'`

- [ ] **Step 3: Write minimal implementation**

Append to `backend/embeddings.py`:
```python
def _embed_model() -> str:
    return os.getenv("LLM_EMBED_MODEL", "mistral-embed")


def _embed_url() -> str:
    return os.getenv("LLM_EMBED_API_URL", "https://api.mistral.ai/v1/embeddings")


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts via the Mistral embeddings endpoint."""
    cfg = llm_client.LLMConfig()
    if not cfg.api_key:
        raise RuntimeError("No API key set for embeddings.")
    payload = {"model": _embed_model(), "input": texts}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(_embed_url(), json=payload, headers=cfg.headers())
        resp.raise_for_status()
        data = resp.json()["data"]
    return [item["embedding"] for item in data]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ../.venv/bin/pytest tests/test_embeddings.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/embeddings.py backend/tests/test_embeddings.py
git commit -m "feat(embeddings): batched embed_texts via Mistral endpoint"
```

---

## Task 3: Cache helpers + `resolve_chunk_vectors`

**Files:**
- Modify: `backend/embeddings.py`
- Modify: `backend/tests/test_embeddings.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_embeddings.py`:
```python
from content_loader import Chunk


async def _fake_embed(texts):
    # Deterministic bag-of-words vector: stable across processes.
    dim = 32
    out = []
    for t in texts:
        v = [0.0] * dim
        for tok in t.lower().split():
            idx = int(hashlib_sha(tok)) % dim
            v[idx] += 1.0
        out.append(v)
    return out


def hashlib_sha(s):
    import hashlib
    return int(hashlib.sha1(s.encode()).hexdigest(), 16)


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../.venv/bin/pytest tests/test_embeddings.py -k "cache_key or resolve" -v`
Expected: FAIL — `AttributeError: module 'embeddings' has no attribute 'cache_key'`

- [ ] **Step 3: Write minimal implementation**

Append to `backend/embeddings.py`:
```python
CACHE_PATH = Path(__file__).with_name("embeddings.json")


def cache_key(text: str, model: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest() + ":" + model


def load_cache(path: Path = CACHE_PATH) -> dict[str, list[float]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


async def resolve_chunk_vectors(chunks, cache: dict[str, list[float]]) -> list[list[float]]:
    """Return one L2-normalised vector per chunk, embedding any cache misses."""
    model = _embed_model()
    keys = [cache_key(c.text, model) for c in chunks]
    missing = [c.text for c, key in zip(chunks, keys) if key not in cache]
    if missing:
        print(f"[ask-me] embedding {len(missing)} uncached chunk(s)")
        fresh = await embed_texts(missing)
        for text, vec in zip(missing, fresh):
            cache[cache_key(text, model)] = vec
    return [l2_normalize(cache[key]) for key in keys]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ../.venv/bin/pytest tests/test_embeddings.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/embeddings.py backend/tests/test_embeddings.py
git commit -m "feat(embeddings): content-hash cache + resolve_chunk_vectors"
```

---

## Task 4: `EmbeddingRetriever`

**Files:**
- Modify: `backend/retrieve.py`
- Create: `backend/tests/test_retrieve.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_retrieve.py`:
```python
import asyncio
import hashlib

import embeddings
import retrieve
from content_loader import Chunk


async def _fake_embed(texts):
    dim = 32
    out = []
    for t in texts:
        v = [0.0] * dim
        for tok in t.lower().split():
            idx = int(hashlib.sha1(tok.encode()).hexdigest(), 16) % dim
            v[idx] += 1.0
        out.append(v)
    return out


def test_embedding_retriever_ranks_semantic_match_first(monkeypatch):
    monkeypatch.setattr(embeddings, "embed_texts", _fake_embed)
    chunks = [
        Chunk("ml", "ML", "faq", "machine learning python data"),
        Chunk("ios", "iOS", "faq", "swift mobile app design"),
    ]
    vectors = asyncio.run(embeddings.resolve_chunk_vectors(chunks, {}))
    r = retrieve.EmbeddingRetriever(chunks, vectors, keyword=retrieve.Retriever(chunks))

    results = asyncio.run(r.retrieve("machine learning", k=2))

    assert results[0][0].source_id == "ml"


def test_embedding_retriever_falls_back_on_embed_error(monkeypatch):
    async def _boom(texts):
        raise RuntimeError("embedding API down")

    monkeypatch.setattr(embeddings, "embed_texts", _fake_embed)
    chunks = [Chunk("ml", "ML", "faq", "machine learning python")]
    vectors = asyncio.run(embeddings.resolve_chunk_vectors(chunks, {}))
    r = retrieve.EmbeddingRetriever(chunks, vectors, keyword=retrieve.Retriever(chunks))

    # Now break query embedding; retrieve must fall back to keyword, not raise.
    monkeypatch.setattr(embeddings, "embed_texts", _boom)
    results = asyncio.run(r.retrieve("machine learning", k=1))
    assert results and results[0][0].source_id == "ml"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../.venv/bin/pytest tests/test_retrieve.py -v`
Expected: FAIL — `AttributeError: module 'retrieve' has no attribute 'EmbeddingRetriever'`

- [ ] **Step 3: Write minimal implementation**

In `backend/retrieve.py`, add at the top with the other imports:
```python
import embeddings
```

Append to `backend/retrieve.py`:
```python
class EmbeddingRetriever:
    """Semantic retriever over precomputed, L2-normalised chunk vectors."""

    def __init__(self, chunks: list[Chunk], vectors: list[list[float]], keyword: "Retriever"):
        self.chunks = chunks
        self.vectors = vectors
        self.keyword = keyword  # runtime fallback if a query embedding fails

    async def retrieve(self, query: str, k: int = 6) -> list[tuple[Chunk, float]]:
        try:
            qvec = embeddings.l2_normalize((await embeddings.embed_texts([query]))[0])
        except Exception as exc:  # noqa: BLE001 - never surface to the user
            print(f"[ask-me] query embedding failed ({exc}); falling back to keyword")
            return await self.keyword.retrieve(query, k)
        scored = [
            (chunk, embeddings.dot(qvec, vec))
            for chunk, vec in zip(self.chunks, self.vectors)
        ]
        scored = [pair for pair in scored if pair[1] > 0]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ../.venv/bin/pytest tests/test_retrieve.py -v`
Expected: FAIL — `Retriever.retrieve` is still sync, so `await self.keyword.retrieve(...)` raises `TypeError`. This is fixed in Task 5. For now run only the first test:

Run: `cd backend && ../.venv/bin/pytest tests/test_retrieve.py::test_embedding_retriever_ranks_semantic_match_first -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/retrieve.py backend/tests/test_retrieve.py
git commit -m "feat(retrieve): EmbeddingRetriever with keyword fallback"
```

---

## Task 5: Async `Retriever.retrieve` + `build_retriever` factory

**Files:**
- Modify: `backend/retrieve.py`
- Modify: `backend/tests/test_retrieve.py`

- [ ] **Step 1: Make the existing `Retriever.retrieve` async**

In `backend/retrieve.py`, change the method signature only:
```python
    async def retrieve(self, query: str, k: int = 6) -> list[tuple[Chunk, float]]:
```
(The body is unchanged — it is pure CPU work; `async` just makes the interface uniform so callers always `await`.)

- [ ] **Step 2: Write the failing test for the factory**

Append to `backend/tests/test_retrieve.py`:
```python
def test_build_retriever_keyword_without_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("RETRIEVER", "auto")
    chunks = [Chunk("a", "A", "faq", "hello world")]
    r = asyncio.run(retrieve.build_retriever(chunks))
    assert isinstance(r, retrieve.Retriever)


def test_build_retriever_embeddings_with_key(monkeypatch):
    monkeypatch.setattr(embeddings, "embed_texts", _fake_embed)
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("RETRIEVER", "auto")
    chunks = [Chunk("a", "A", "faq", "machine learning")]
    r = asyncio.run(retrieve.build_retriever(chunks))
    assert isinstance(r, retrieve.EmbeddingRetriever)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && ../.venv/bin/pytest tests/test_retrieve.py -k build_retriever -v`
Expected: FAIL — `AttributeError: module 'retrieve' has no attribute 'build_retriever'`

- [ ] **Step 4: Write minimal implementation**

Append to `backend/retrieve.py`:
```python
import os

import llm_client


async def build_retriever(chunks: list[Chunk]):
    """Pick the retriever: embeddings when Mistral + key, else keyword."""
    mode = os.getenv("RETRIEVER", "auto").lower()
    keyword = Retriever(chunks)
    if mode == "keyword":
        return keyword

    cfg = llm_client.LLMConfig()
    can_embed = cfg.provider == "mistral" and bool(cfg.api_key)
    if not can_embed:
        if mode == "embeddings":
            print("[ask-me] RETRIEVER=embeddings but no Mistral key; using keyword")
        return keyword

    cache = embeddings.load_cache()
    vectors = await embeddings.resolve_chunk_vectors(chunks, cache)
    print(f"[ask-me] embedding retriever ready ({len(chunks)} chunks)")
    return EmbeddingRetriever(chunks, vectors, keyword=keyword)
```

- [ ] **Step 5: Run the full retrieve + embeddings suites**

Run: `cd backend && ../.venv/bin/pytest tests/ -v`
Expected: PASS (all tests, including the Task 4 fallback test that needed async keyword)

- [ ] **Step 6: Commit**

```bash
git add backend/retrieve.py backend/tests/test_retrieve.py
git commit -m "feat(retrieve): async retrieve + build_retriever factory"
```

---

## Task 6: Wire into `main.py`

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Use the factory in lifespan**

In `backend/main.py`, replace the retriever construction line:
```python
    STATE["retriever"] = Retriever(all_chunks(docs))
```
with:
```python
    STATE["retriever"] = await build_retriever(all_chunks(docs))
```
And change the import:
```python
from retrieve import Retriever
```
to:
```python
from retrieve import build_retriever
```

- [ ] **Step 2: Await retrieve in both endpoints**

In `chat`:
```python
    scored = await retriever.retrieve(req.message, k=6)
```
In `job_fit`:
```python
    scored = await retriever.retrieve(query, k=10)
```
Also remove the now-unused `retriever: Retriever = STATE["retriever"]` type annotation, using:
```python
    retriever = STATE["retriever"]
```
in both endpoints.

- [ ] **Step 3: Verify boot with keyword (no network)**

Run:
```bash
cd backend && RETRIEVER=keyword ../.venv/bin/python -c "
import asyncio, main
from fastapi.testclient import TestClient
with TestClient(main.app) as c:
    print(c.get('/health').json())
"
```
Expected: `{'status': 'ok', 'documents': 18}` and no errors.

- [ ] **Step 4: Run full test suite**

Run: `cd backend && ../.venv/bin/pytest tests/ -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add backend/main.py
git commit -m "feat(retrieve): wire build_retriever into the API"
```

---

## Task 7: Generate & commit the embedding cache

**Files:**
- Create: `backend/build_embeddings.py`
- Create: `backend/embeddings.json` (generated)

- [ ] **Step 1: Write the generator script**

`backend/build_embeddings.py`:
```python
"""Generate backend/embeddings.json from content/. Run after editing content.

    cd backend && LLM_PROVIDER=mistral LLM_API_KEY=... python build_embeddings.py
"""
import asyncio
import json
import os

from dotenv import load_dotenv

import embeddings
from content_loader import all_chunks, load_documents


async def main() -> None:
    load_dotenv()
    content_dir = os.getenv("CONTENT_DIR", "../content")
    chunks = all_chunks(load_documents(content_dir))
    model = embeddings._embed_model()
    print(f"[build] embedding {len(chunks)} chunks with {model}")
    vectors = await embeddings.embed_texts([c.text for c in chunks])
    cache = {embeddings.cache_key(c.text, model): v for c, v in zip(chunks, vectors)}
    embeddings.CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")
    print(f"[build] wrote {embeddings.CACHE_PATH} ({len(cache)} entries)")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Generate the cache (needs the real Mistral key)**

Run:
```bash
cd backend && ../.venv/bin/python build_embeddings.py
```
Expected: `wrote .../embeddings.json (44 entries)` (count matches `all_chunks`).

- [ ] **Step 3: Sanity-check real end-to-end embeddings retrieval**

Run:
```bash
cd backend && ../.venv/bin/python -c "
import json, main
from fastapi.testclient import TestClient
with TestClient(main.app) as c:
    r = c.post('/chat', json={'message':'machine learning experience','conversation':[]})
    evt = [json.loads(l) for l in r.text.splitlines() if l.strip()]
    srcs = next(e for e in evt if e['type']=='sources')['sources']
    print('status', r.status_code, '| sources', [s['id'] for s in srcs])
"
```
Expected: status 200 and a non-empty, relevant source list. (Boot log should say "embedding retriever ready", not "embedding N uncached chunk(s)" — confirming the cache is complete.)

- [ ] **Step 4: Commit**

```bash
git add backend/build_embeddings.py backend/embeddings.json
git commit -m "feat(embeddings): generator script + committed cache"
```

---

## Task 8: Configuration docs

**Files:**
- Modify: `backend/.env.example`, `render.yaml`, `README.md`

- [ ] **Step 1: `.env.example`** — under the production block, add:
```
# Retrieval: auto (embeddings when Mistral+key, else keyword) | embeddings | keyword
# RETRIEVER=auto
# LLM_EMBED_MODEL=mistral-embed
```

- [ ] **Step 2: `render.yaml`** — add to `envVars`:
```yaml
      - key: RETRIEVER
        value: auto
```

- [ ] **Step 3: `README.md`** — in the retrieval section, replace the "keyword + IDF" description with a note that prod uses `mistral-embed` semantic retrieval (keyword fallback for local/dev), and document regenerating the cache: "After editing `content/`, run `python backend/build_embeddings.py` and commit `backend/embeddings.json`."

- [ ] **Step 4: Commit**

```bash
git add backend/.env.example render.yaml README.md
git commit -m "docs: document embeddings retrieval + cache regen"
```

---

## Task 9: Final verification

- [ ] **Step 1: Full test suite green**

Run: `cd backend && ../.venv/bin/pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 2: Frontend build still clean**

Run: `cd web && npm run build 2>&1 | tail -5`
Expected: compiles, routes unchanged.

- [ ] **Step 3: Push**

```bash
git push origin main
```
Expected: Render redeploys with `RETRIEVER=auto` + committed cache (instant cold start, no boot-time embedding calls); Vercel unaffected.

---

## Self-review notes

- **Spec coverage:** embeddings.py (Tasks 1-3), committed cache (Tasks 3, 7), EmbeddingRetriever (Task 4), factory + fallback (Tasks 4-5), config (Task 8), tests (Tasks 1-6), generator (Task 7). All spec sections mapped.
- **Async deviation** documented above; `main.py` updated in Task 6.
- **Type consistency:** `embed_texts`, `resolve_chunk_vectors(chunks, cache)`, `cache_key(text, model)`, `EmbeddingRetriever(chunks, vectors, keyword=...)`, `build_retriever(chunks)` are used identically across tasks and tests.
