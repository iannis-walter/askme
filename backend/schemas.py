"""Request/response models for the Ask Me backend."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: str  # "user" | "assistant"
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(max_length=4000)
    conversation: list[Turn] = Field(default_factory=list, max_length=20)


class Source(BaseModel):
    id: str
    title: str
    kind: str  # bio | experience | skills | faq | project | role
    score: float | None = None


class JobFitRequest(BaseModel):
    job_description: str = Field(max_length=8000)
    focus: str | None = Field(default=None, max_length=200)


class JobFitResponse(BaseModel):
    summary: str
    strengths: list[str]
    gaps: list[str]
    relevant_projects: list[str]
    pitch: str
    sources: list[Source]
