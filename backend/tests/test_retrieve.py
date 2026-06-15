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
