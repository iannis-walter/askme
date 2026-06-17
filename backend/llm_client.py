"""Provider-agnostic LLM client.

Speaks the OpenAI-compatible Chat Completions API, which every major runtime
implements — Groq, Ollama, Mistral, OpenRouter, Together, vLLM. Switching
provider is a matter of environment variables; the code never changes.

  LLM_PROVIDER   groq | ollama | mistral | openrouter   (default: ollama)
  LLM_MODEL      overrides the provider's default model
  LLM_API_URL    overrides the provider's default endpoint
  LLM_API_KEY    API key (not needed for a local Ollama)

Typical setups:
  - Local dev   → Ollama (LLM_PROVIDER=ollama): free, no key, fully private.
  - Production  → Groq (LLM_PROVIDER=groq): open-source models, free tier,
                  zero infra — the only sane choice when the front-end is on a
                  serverless host like Vercel that cannot run a model itself.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx

# Per-provider defaults. Any field can be overridden by an explicit env var.
PROVIDERS: dict[str, dict[str, str]] = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        "key_env": "GROQ_API_KEY",
    },
    "ollama": {
        "url": "http://localhost:11434/v1/chat/completions",
        "model": "llama3.1",
        "key_env": "",  # local runtime, no auth
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/chat/completions",
        "model": "mistral-small-latest",
        "key_env": "MISTRAL_API_KEY",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "key_env": "OPENROUTER_API_KEY",
    },
}


class LLMConfig:
    """Resolves provider settings from the environment at call time."""

    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        preset = PROVIDERS.get(self.provider, PROVIDERS["ollama"])
        self.url = os.getenv("LLM_API_URL") or preset["url"]
        self.model = os.getenv("LLM_MODEL") or preset["model"]
        # A generic LLM_API_KEY wins; otherwise the provider's own key env var.
        self.api_key = os.getenv("LLM_API_KEY") or (
            os.getenv(preset["key_env"], "") if preset["key_env"] else ""
        )

    @property
    def needs_key(self) -> bool:
        return self.provider != "ollama"

    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def _config() -> LLMConfig:
    return LLMConfig()


# An async gate that spaces upstream calls out to respect the provider's rate
# limit (the Mistral free tier allows ~1 req/s). Concurrent callers queue here
# and wait their turn instead of receiving 429s from the provider — so a real
# visitor sees a slightly slower answer, never an error. Off when interval ≤ 0.
_throttle_gate = asyncio.Lock()
_last_call = 0.0


async def _respect_rate_limit() -> None:
    interval = float(os.getenv("LLM_MIN_INTERVAL_S", "0") or 0)
    if interval <= 0:
        return
    global _last_call
    async with _throttle_gate:
        wait = interval - (time.monotonic() - _last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call = time.monotonic()


async def stream_chat(messages: list[dict]) -> AsyncIterator[str]:
    """Yield text deltas from a streamed, OpenAI-compatible completion."""
    cfg = _config()
    if cfg.needs_key and not cfg.api_key:
        yield f"[Configuration error: no API key set for provider '{cfg.provider}'.]"
        return

    await _respect_rate_limit()
    payload = {"model": cfg.model, "messages": messages, "stream": True, "temperature": 0.2}

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", cfg.url, json=payload, headers=cfg.headers()) as resp:
            if resp.status_code != 200:
                body = (await resp.aread()).decode("utf-8", "ignore")
                yield f"[LLM API error {resp.status_code}: {body[:300]}]"
                return
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content")
                    if delta:
                        yield delta
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


@dataclass
class ChatResult:
    """One non-streamed assistant turn plus token accounting.

    `message` is the raw assistant message dict (`role`, `content`, and an
    optional `tool_calls` list). `usage` carries the provider's token counts
    when reported (`{}` otherwise). This is the building block of the agent
    loop: each reasoning step is one ChatResult.
    """

    message: dict
    usage: dict = field(default_factory=dict)

    @property
    def tool_calls(self) -> list[dict]:
        return self.message.get("tool_calls") or []

    @property
    def content(self) -> str:
        return self.message.get("content") or ""


async def complete_chat(
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    tool_choice: str = "auto",
    stop: list[str] | None = None,
    timeout: float = 60.0,
) -> ChatResult:
    """One non-streamed completion that may request tool calls.

    Tool-aware sibling of `complete_json`/`stream_chat`. When `tools` is given,
    the model can answer with `tool_calls` (OpenAI-compatible — Mistral, Groq,
    OpenRouter). `stop` lets the ReAct fallback halt generation at the
    `Observation:` boundary. The existing single-shot helpers stay untouched.
    """
    cfg = _config()
    if cfg.needs_key and not cfg.api_key:
        raise RuntimeError(f"No API key set for provider '{cfg.provider}'.")

    await _respect_rate_limit()
    payload: dict = {"model": cfg.model, "messages": messages, "temperature": 0.2}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice
    if stop:
        payload["stop"] = stop

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(cfg.url, json=payload, headers=cfg.headers())
        resp.raise_for_status()
        body = resp.json()

    message = body["choices"][0]["message"]
    usage = body.get("usage") or {}
    return ChatResult(message=message, usage=usage)


async def complete_json(messages: list[dict]) -> dict:
    """Single (non-streamed) completion that returns parsed JSON."""
    cfg = _config()
    if cfg.needs_key and not cfg.api_key:
        raise RuntimeError(f"No API key set for provider '{cfg.provider}'.")

    await _respect_rate_limit()
    payload = {
        "model": cfg.model,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(cfg.url, json=payload, headers=cfg.headers())
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        content = content[content.find("{"):]
    return json.loads(content)
