"""Ask Me — FastAPI service.

Owns the applied-AI work: load the knowledge base, retrieve and rank the most
relevant chunks for a question, build grounded prompts, and orchestrate the LLM
through a provider-agnostic client. The Next.js front-end is a thin product
layer over this.
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import llm_client
import prompts
from content_loader import all_chunks, load_documents
from ratelimit import RateLimiter
from retrieve import Retriever
from schemas import ChatRequest, JobFitRequest, JobFitResponse, Source

load_dotenv()

STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    content_dir = os.getenv("CONTENT_DIR", "../content")
    docs = load_documents(content_dir)
    STATE["docs"] = docs
    STATE["by_id"] = {doc.id: doc for doc in docs}
    STATE["retriever"] = Retriever(all_chunks(docs))
    print(f"[ask-me] loaded {len(docs)} documents, {len(all_chunks(docs))} chunks from {content_dir}")
    yield
    STATE.clear()


app = FastAPI(title="Ask Me — Candidate API", lifespan=lifespan)

# Per-IP rate limiting (abuse protection). The upstream free-tier pacing lives in
# llm_client; these guard the service itself against a single client hammering it.
chat_burst = RateLimiter(limit=5, window_s=1.0)     # no bursts
chat_rate = RateLimiter(limit=30, window_s=60.0)    # sustained per minute
jobfit_rate = RateLimiter(limit=10, window_s=60.0)  # heavier call, tighter cap

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _dedupe_sources(scored) -> list[Source]:
    seen: dict[str, Source] = {}
    for chunk, score in scored:
        if chunk.source_id not in seen:
            seen[chunk.source_id] = Source(
                id=chunk.source_id,
                title=chunk.source_title,
                kind=chunk.source_kind,
                score=round(float(score), 3),
            )
    return list(seen.values())


@app.get("/health")
async def health():
    return {"status": "ok", "documents": len(STATE.get("docs", []))}


@app.post("/chat")
async def chat(
    req: ChatRequest,
    _burst: None = Depends(chat_burst),
    _rate: None = Depends(chat_rate),
):
    retriever: Retriever = STATE["retriever"]
    scored = retriever.retrieve(req.message, k=6)
    chunks = [chunk for chunk, _ in scored]
    sources = _dedupe_sources(scored)

    async def event_stream() -> AsyncIterator[bytes]:
        # Retrieval happens before generation, so we can send sources first.
        yield (json.dumps({"type": "sources", "sources": [s.model_dump() for s in sources]}) + "\n").encode()
        history = [t.model_dump() for t in req.conversation]
        messages = prompts.build_chat_messages(req.message, chunks, history)
        async for delta in llm_client.stream_chat(messages):
            yield (json.dumps({"type": "delta", "text": delta}) + "\n").encode()
        yield (json.dumps({"type": "done"}) + "\n").encode()

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.post("/job-fit", response_model=JobFitResponse)
async def job_fit(req: JobFitRequest, _rate: None = Depends(jobfit_rate)):
    retriever: Retriever = STATE["retriever"]
    # Retrieve broadly: blend the job text with role-fit framing.
    query = f"{req.job_description} {req.focus or ''}"
    scored = retriever.retrieve(query, k=10)
    chunks = [chunk for chunk, _ in scored]
    sources = _dedupe_sources(scored)

    messages = prompts.build_job_fit_messages(req.job_description, req.focus, chunks)
    try:
        data = await llm_client.complete_json(messages)
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the UI
        return JobFitResponse(
            summary=f"Could not generate a fit report: {exc}",
            strengths=[],
            gaps=[],
            relevant_projects=[],
            pitch="",
            sources=sources,
        )

    return JobFitResponse(
        summary=data.get("summary", ""),
        strengths=data.get("strengths", []) or [],
        gaps=data.get("gaps", []) or [],
        relevant_projects=data.get("relevant_projects", []) or [],
        pitch=data.get("pitch", ""),
        sources=sources,
    )


@app.get("/sources")
async def get_source(id: str):
    doc = STATE.get("by_id", {}).get(id)
    if not doc:
        return {"error": "not found"}
    return {"id": doc.id, "title": doc.title, "kind": doc.kind, "text": doc.text}
