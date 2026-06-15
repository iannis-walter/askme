---
title: "Ask Me — Conversational Candidate Profile"
slug: ask-me-candidate-os
stack: [Next.js, TypeScript, Tailwind, Mistral API, FastAPI]
tags: [llm, rag, fullstack, ux, recruiter-tool]
role_relevance: [applied-ai, fullstack, recruiter-tool]
---

## Problem
A CV is a flat document. A recruiter or hiring manager can't interrogate it, can't ask "show me proof of full-stack ability" or "how does he fit *this* role" without a call. I wanted to turn my profile into something queryable.

## What I built
A conversational interface (inspired by Mistral / Vibe) where anyone can ask natural questions about my background and get grounded, sourced answers — plus a "Job fit" mode where you paste a job description and get a structured match: strengths, gaps, relevant projects, and a tailored pitch.

## Technical decisions
- Knowledge base as structured JSON/Markdown (bio, experience, skills, projects, FAQ) — quality of content over model complexity.
- Lightweight, transparent retrieval (keyword scoring → top chunks) before calling the model; embeddings as a later upgrade.
- Every answer cites its internal sources, so responses are grounded and not hallucinated.
- Mistral API for generation; streaming responses for a real product feel.
- TODO_CONFIRM: Next.js-only (Version A) vs Next.js + FastAPI micro-service (Version B, shows Python + TS).

## Tradeoffs
- No auth / DB / document upload at MVP — deliberately scoped to ship something polished and finished fast.
- Simple retrieval over a vector DB — transparency and speed over sophistication for a small, curated corpus.

## Why this matters for Mistral
It's a real applied-AI product, not a portfolio gadget: grounded generation, a clean conversational UX, and a concrete use case (decision support for hiring). It uses the Mistral API end to end and is built on the exact stack the Applied AI Engineer Fullstack role asks for (Python + TypeScript, React/Next).
