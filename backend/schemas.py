"""Request/response models for the Ask Me backend."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation: list[Turn] = Field(default_factory=list)


class Source(BaseModel):
    id: str
    title: str
    kind: str  # bio | experience | skills | faq | project | role
    score: float | None = None


class JobFitRequest(BaseModel):
    job_description: str
    focus: str | None = None


class JobFitResponse(BaseModel):
    summary: str
    strengths: list[str]
    gaps: list[str]
    relevant_projects: list[str]
    pitch: str
    sources: list[Source]
