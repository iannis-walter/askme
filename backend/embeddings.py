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
