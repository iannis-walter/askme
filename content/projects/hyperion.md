---
title: "Hyperion — Narrative real-time monitoring"
slug: hyperion
stack: [React, TypeScript, WebSocket, Fastify, uPlot, Docker, Fly.io, Vercel]
tags: [fullstack, real-time, observability, product-thinking]
role_relevance: [fullstack, applied-ai]
---

## Problem
Most monitoring dashboards drown the operator under 200 metrics. The hard part isn't collecting data — it's making each pixel carry actionable information so a human can decide fast.

## What I built
A real-time supervision dashboard that **stages the incident** rather than dumping raw metrics:
- Multi-host real-time monitoring (CPU, memory, disk, network) pushed over **WebSocket**.
- **Narrative alerts** that explain the probable cause and time horizon, instead of a wall of numbers.
- Smooth 60 fps graphs (uPlot) and a built-in incident simulator — zero agent to install.

## Technical decisions
- WebSocket push for low-latency live updates; Fastify backend for throughput.
- uPlot for high-performance time-series rendering at 60 fps.
- Built-in simulator so the product is demoable and testable without wiring up real infrastructure.
- Containerised (Docker) and deployed to Fly.io / Vercel.

## Tradeoffs
- "Narrative" alerting adds interpretation logic over raw thresholds — more design effort, but far more useful to the person on call.

## Why this matters for Mistral
Real-time fullstack with strong product/UX judgement applied to a technical domain — the same instinct an applied engineer needs when turning a model's raw output into something a user can act on.
