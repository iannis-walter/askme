---
title: "Ask Me — Conversational Candidate Profile"
slug: ask-me-candidate-os
stack: [Next.js, TypeScript, Tailwind, FastAPI, Claude API]
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
- Provider-agnostic LLM layer: production runs on the Claude API (official Anthropic SDK), and switching to Mistral, Groq, OpenRouter or a local Ollama model is a configuration change. Streaming responses for a real product feel.
- Two-tier model routing: a fast model (Claude Haiku) sorts each question first. Facts that can be read off the CV (years of experience, stack, dates) are answered by Claude Haiku; questions that need judgment ("why is he a good fit for this role?") go to Claude Sonnet. Cheap and fast where it doesn't matter, stronger where it does.
- Next.js front end + FastAPI micro-service: the UI is a thin TypeScript layer, while retrieval, prompts and LLM orchestration live in Python.

## Tradeoffs
- No auth / DB / document upload at MVP — deliberately scoped to ship something polished and finished fast.
- Simple retrieval over a vector DB — transparency and speed over sophistication for a small, curated corpus.

## Why this matters for Mistral
It's a real applied-AI product, not a portfolio gadget: grounded generation, a clean conversational UX, and a concrete use case (decision support for hiring). It runs on the Claude API behind a provider-agnostic LLM layer, so moving it to the Mistral API is a configuration change, and it is built on the exact stack the Applied AI Engineer Fullstack role asks for (Python + TypeScript, React/Next).
