"""Abuse protection, exercised through the real FastAPI app.

The model is stubbed, so nothing here makes a network call. Requests go through
httpx's ASGI transport, which lets each test choose the peer address the app sees
— the address of the proxy in production, never the visitor's.
"""
import asyncio
import json
from datetime import date
from pathlib import Path

import httpx
import pytest
from starlette.requests import Request

import llm_client
import main
import ratelimit

CONTENT_DIR = str(Path(__file__).resolve().parents[2] / "content")
PROXY = "10.201.7.33"  # the one peer every request arrives from in production
SECRET = "s3cret-shared-with-the-front"

REAL_STREAM_CHAT = llm_client.stream_chat


@pytest.fixture(autouse=True)
def isolated_app(monkeypatch):
    monkeypatch.setenv("CONTENT_DIR", CONTENT_DIR)
    monkeypatch.setenv("RETRIEVER", "keyword")
    for name in ("BACKEND_SHARED_SECRET", "DAILY_REQUEST_BUDGET", "AGENT_DEBUG"):
        monkeypatch.delenv(name, raising=False)

    async def stream_chat(messages, *, tier="complex"):
        yield "ok"

    async def complete_chat(messages, **kwargs):
        return llm_client.ChatResult(message={"role": "assistant", "content": "final answer"})

    async def complete_json(messages, **kwargs):
        return {"summary": "s", "strengths": [], "gaps": [], "relevant_projects": [], "pitch": "p"}

    async def route_question(question, history=None):
        return "complex"

    monkeypatch.setattr(llm_client, "stream_chat", stream_chat)
    monkeypatch.setattr(llm_client, "complete_chat", complete_chat)
    monkeypatch.setattr(llm_client, "complete_json", complete_json)
    monkeypatch.setattr(llm_client, "route_question", route_question)

    # Limiters live for the life of the process; start every test from zero.
    for limiter in (main.chat_burst, main.chat_rate, main.jobfit_rate, main.agent_rate):
        limiter._hits.clear()
    budget = getattr(main, "daily_budget", None)
    if budget is not None:
        budget._spent = 0


def send(*requests, peer=PROXY):
    """Send (method, path, kwargs) requests in order; return their responses."""

    async def go():
        async with main.lifespan(main.app):
            transport = httpx.ASGITransport(app=main.app, client=(peer, 50000))
            async with httpx.AsyncClient(transport=transport, base_url="http://backend") as client:
                return [await client.request(method, path, **kwargs) for method, path, kwargs in requests]

    return asyncio.run(go())


def chat(headers=None):
    return ("POST", "/chat", {"json": {"message": "hi"}, "headers": headers or {}})


def from_visitor(ip, secret=SECRET):
    return {"X-Proxy-Secret": secret, "X-Client-IP": ip}


def last_event(response):
    return json.loads(response.text.strip().splitlines()[-1])


# --- rate limiting -------------------------------------------------------------

def test_visitors_behind_the_same_proxy_get_separate_rate_limit_buckets(monkeypatch):
    monkeypatch.setenv("BACKEND_SHARED_SECRET", SECRET)

    responses = send(
        *[chat(from_visitor("203.0.113.66")) for _ in range(5)],  # one visitor uses up the burst
        chat(from_visitor("198.51.100.7")),                       # another visitor, same proxy
    )

    assert [r.status_code for r in responses] == [200, 200, 200, 200, 200, 200]


def test_one_visitor_is_still_limited_behind_the_proxy(monkeypatch):
    monkeypatch.setenv("BACKEND_SHARED_SECRET", SECRET)

    responses = send(*[chat(from_visitor("203.0.113.66")) for _ in range(6)])

    assert [r.status_code for r in responses] == [200, 200, 200, 200, 200, 429]


def test_client_ip_header_cannot_dodge_the_limit_when_no_secret_is_configured():
    responses = send(
        *[chat({"X-Client-IP": "203.0.113.66"}) for _ in range(5)],
        chat({"X-Client-IP": "198.51.100.7"}),  # same peer pretending to be someone else
    )

    assert responses[-1].status_code == 429


def test_rate_limiter_forgets_addresses_whose_window_has_passed(monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(ratelimit.time, "monotonic", lambda: clock["now"])
    limiter = ratelimit.RateLimiter(limit=5, window_s=1.0)

    def request_from(ip):
        return Request({"type": "http", "headers": [], "client": (ip, 1234)})

    for i in range(50):
        asyncio.run(limiter(request_from(f"192.0.2.{i}")))
    clock["now"] += 60.0
    asyncio.run(limiter(request_from("198.51.100.7")))

    assert list(limiter._hits) == ["198.51.100.7"]


# --- shared secret between the front-end and the backend -----------------------

def test_requests_without_the_proxy_secret_are_refused_once_one_is_configured(monkeypatch):
    monkeypatch.setenv("BACKEND_SHARED_SECRET", SECRET)

    no_header, wrong_header, sources = send(
        chat(),
        chat(from_visitor("203.0.113.66", secret="guess")),
        ("GET", "/sources?id=bio", {}),
    )

    assert [no_header.status_code, wrong_header.status_code, sources.status_code] == [403, 403, 403]


def test_health_check_needs_no_secret(monkeypatch):
    monkeypatch.setenv("BACKEND_SHARED_SECRET", SECRET)

    (health,) = send(("GET", "/health", {}))

    assert health.status_code == 200


# --- daily budget --------------------------------------------------------------

def test_requests_are_refused_once_the_daily_budget_is_spent(monkeypatch):
    monkeypatch.setenv("DAILY_REQUEST_BUDGET", "3")

    responses = send(*[chat() for _ in range(4)])  # 4 < burst limit, so only the budget can refuse

    assert [r.status_code for r in responses] == [200, 200, 200, 429]


def test_an_agent_request_spends_four_units_of_the_daily_budget(monkeypatch):
    monkeypatch.setenv("DAILY_REQUEST_BUDGET", "5")

    agent, first_chat, second_chat = send(
        ("POST", "/chat/agent", {"json": {"message": "hi"}}),
        chat(),
        chat(),
    )

    assert [agent.status_code, first_chat.status_code, second_chat.status_code] == [200, 200, 429]


def test_the_daily_budget_starts_fresh_the_next_day(monkeypatch):
    monkeypatch.setenv("DAILY_REQUEST_BUDGET", "1")
    monkeypatch.setattr(ratelimit, "_today", lambda: date(2031, 3, 1))
    spent = send(chat(), chat())
    assert [r.status_code for r in spent] == [200, 429]

    monkeypatch.setattr(ratelimit, "_today", lambda: date(2031, 3, 2))
    (next_day,) = send(chat())

    assert next_day.status_code == 200


# --- agent trace exposure ------------------------------------------------------

def test_debug_query_param_alone_does_not_expose_the_trace():
    (response,) = send(("POST", "/chat/agent?debug=1", {"json": {"message": "hi"}}))

    assert "trace" not in last_event(response)


def test_trace_is_attached_when_agent_debug_is_enabled(monkeypatch):
    monkeypatch.setenv("AGENT_DEBUG", "1")

    (response,) = send(("POST", "/chat/agent", {"json": {"message": "hi"}}))

    assert last_event(response)["trace"]["question"] == "hi"


def test_trace_endpoint_is_not_served_unless_agent_debug_is_enabled():
    (response,) = send(("POST", "/chat/agent", {"json": {"message": "hi"}}))
    request_id = last_event(response)["request_id"]

    (trace,) = send(("GET", f"/trace/{request_id}", {}))

    assert trace.status_code == 404


def test_trace_endpoint_serves_the_trace_when_agent_debug_is_enabled(monkeypatch):
    monkeypatch.setenv("AGENT_DEBUG", "1")
    (response,) = send(("POST", "/chat/agent", {"json": {"message": "hi"}}))
    request_id = last_event(response)["request_id"]

    (trace,) = send(("GET", f"/trace/{request_id}", {}))

    assert trace.json()["request_id"] == request_id


# --- error text ----------------------------------------------------------------

def test_job_fit_failure_does_not_reveal_the_upstream_error(monkeypatch):
    async def failing(messages, **kwargs):
        raise RuntimeError("401 Unauthorized for url 'https://internal-gateway.example/v1' key=abc123")

    monkeypatch.setattr(llm_client, "complete_json", failing)

    (response,) = send(("POST", "/job-fit", {"json": {"job_description": "Senior backend engineer"}}))

    assert response.status_code == 200
    assert "internal-gateway" not in response.text
    assert "abc123" not in response.text


def test_stream_failure_does_not_reveal_the_upstream_error_body(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.delenv("LLM_MIN_INTERVAL_S", raising=False)

    def upstream(request):
        return httpx.Response(401, json={"message": "Unauthorized: key sk-live-123 belongs to org-777"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        llm_client.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(upstream), **kw)
    )

    async def collect():
        return "".join([delta async for delta in REAL_STREAM_CHAT([{"role": "user", "content": "q"}])])

    shown = asyncio.run(collect())

    assert shown  # the visitor still gets a message
    assert "sk-live-123" not in shown
    assert "org-777" not in shown


# --- request size --------------------------------------------------------------

def test_an_oversized_body_is_refused():
    body = json.dumps({"message": "hi", "padding": "x" * 2_000_000})

    (response,) = send(("POST", "/chat", {"content": body, "headers": {"Content-Type": "application/json"}}))

    assert response.status_code == 413


def test_an_oversized_body_sent_without_a_length_is_refused():
    async def chunks():
        yield b'{"message": "hi", "padding": "'
        for _ in range(40):
            yield b"x" * 50_000
        yield b'"}'

    (response,) = send(("POST", "/chat", {"content": chunks(), "headers": {"Content-Type": "application/json"}}))

    assert response.status_code == 413


def test_a_normal_body_is_accepted():
    turn = {"role": "user", "content": "y" * 4000}

    (response,) = send(("POST", "/chat", {"json": {"message": "x" * 4000, "conversation": [turn] * 20}}))

    assert response.status_code == 200


# --- API docs ------------------------------------------------------------------

def test_api_docs_are_not_served_by_default():
    docs, schema = send(("GET", "/docs", {}), ("GET", "/openapi.json", {}))

    assert [docs.status_code, schema.status_code] == [404, 404]


def test_an_unreachable_provider_yields_a_message_instead_of_breaking_the_stream(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.delenv("LLM_MIN_INTERVAL_S", raising=False)

    def upstream(request):
        raise httpx.ConnectError("connection refused: internal-gateway.example:443")

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        llm_client.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(upstream), **kw)
    )

    async def collect():
        return "".join([delta async for delta in REAL_STREAM_CHAT([{"role": "user", "content": "q"}])])

    shown = asyncio.run(collect())

    assert shown
    assert "internal-gateway" not in shown
