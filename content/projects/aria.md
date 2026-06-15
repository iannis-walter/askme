---
title: "Aria — Personal safety companion"
slug: aria
stack: [Swift, SwiftUI, NestJS, TypeScript, Next.js, Redis, Vercel]
tags: [fullstack, mobile, ios, backend, critical, end-to-end]
role_relevance: [fullstack]
---

## Problem
Personal safety in a risky moment: how do you alert your relatives, find a place of refuge, and defuse a dangerous situation — while also building, on the partner side, a network of certified "Safe Places" that shops and institutions can join.

## What I built
The **entire chain, designed and built solo**: a native iOS app (SwiftUI), a NestJS backend, and a web site.
- Emergency alert to relatives, a map of "Safe Places", and a fake incoming call to defuse a situation.
- A refuge-location network for partners: SIRET-based registration, a dashboard, and a certified badge.

## Technical decisions
- Native iOS in SwiftUI for the on-the-ground experience; NestJS + TypeScript backend shared with the web front; Redis for fast lookups; Next.js for the web side.
- One person owning mobile + backend + web means consistent contracts and fast iteration end to end.

## Tradeoffs
- Going native (SwiftUI) rather than cross-platform was a deliberate choice for reliability of safety-critical features over reach.

## Why this matters for Mistral
Demonstrates genuine end-to-end ownership across mobile, backend and web — the breadth and autonomy expected of an engineer who has to ship complete solutions, not just one layer.
