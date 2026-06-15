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
