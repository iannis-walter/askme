"""A small, transparent retrieval layer.

No vector database yet — deliberately. For a small, curated corpus, a readable
keyword scorer with inverse-document-frequency weighting is fast, has zero
infrastructure, and is easy to explain to whoever reviews the code. Embeddings
are the obvious next upgrade, behind the same interface.
"""
from __future__ import annotations

import math
import re
from collections import Counter

import embeddings
from content_loader import Chunk

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "as", "at", "by", "this", "that",
    "it", "its", "he", "she", "they", "his", "her", "their", "i", "you", "we",
    "what", "which", "who", "how", "why", "do", "does", "did", "can", "could",
    "about", "from", "has", "have", "had", "not", "would", "should",
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9+#.]+", text.lower())
    return [t for t in tokens if len(t) >= 2 and t not in _STOPWORDS]


class Retriever:
    """Builds an IDF table over chunks and scores them against a query."""

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self._tokenized = [tokenize(c.text) for c in chunks]
        self._idf = self._build_idf()

    def _build_idf(self) -> dict[str, float]:
        n = len(self.chunks) or 1
        df: Counter[str] = Counter()
        for tokens in self._tokenized:
            for term in set(tokens):
                df[term] += 1
        return {term: math.log((1 + n) / (1 + count)) + 1.0 for term, count in df.items()}

    def score(self, query_tokens: list[str], doc_tokens: list[str]) -> float:
        if not doc_tokens:
            return 0.0
        counts = Counter(doc_tokens)
        length_norm = 1.0 / math.sqrt(len(doc_tokens))
        total = 0.0
        for term in query_tokens:
            if term in counts:
                total += counts[term] * self._idf.get(term, 1.0)
        return total * length_norm

    def retrieve(self, query: str, k: int = 6) -> list[tuple[Chunk, float]]:
        query_tokens = tokenize(query)
        scored = [
            (chunk, self.score(query_tokens, tokens))
            for chunk, tokens in zip(self.chunks, self._tokenized)
        ]
        scored = [pair for pair in scored if pair[1] > 0]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]


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
