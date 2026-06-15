---
title: "Vigie — Real-time visual watch"
slug: vigie
stack: [TensorFlow.js, COCO-SSD, Computer Vision, Next.js, Canvas]
tags: [applied-ai, computer-vision, edge, on-device, critical]
role_relevance: [applied-ai, fullstack]
---

## Problem
Watch-keeping from a ship's bridge is demanding: an operator has to spot vessels, small craft, people overboard and birds on a live video feed, in real time, without help. The goal was a watch aid — not a science demo — that respects privacy in a sensitive context.

## What I built
Real-time object detection (vessels, craft, people, birds) on a video feed, running **100% on-device in the browser** — playable live demo. The user can switch between three sources: a looping archive sequence, a live camera, or imported media.

## Technical decisions
- COCO-SSD object detection executed with **TensorFlow.js, entirely in the browser** — no image is ever sent or stored. This is the core privacy property, and it matters in a critical environment.
- Rendering via Canvas for smooth real-time overlays.
- **Honest framing**: positioned as a watch aid (anti-collision, traffic, man-overboard, spotting craft and birds), not as a species classifier. Knowing the limits of a model is part of shipping it responsibly.

## Tradeoffs
- On-device inference trades raw accuracy/model size for privacy and zero-latency, no-backend operation — the right call for the use case.

## Why this matters for Mistral
This is applied AI shipped as a usable product: a real model (COCO-SSD) running on the edge, privacy-first, with honest scoping of what it can and can't do. It's the most direct evidence of turning an AI capability into something an operator could actually use.
