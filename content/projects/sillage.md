---
title: "Sillage — Expedition booking experience"
slug: sillage
stack: [Next.js, TypeScript, Prisma, Stripe, Server Actions, Tailwind, Vercel]
tags: [fullstack, nextjs, production-grade, testing, seo]
role_relevance: [fullstack]
---

## Problem
Build a premium expedition-cruise booking experience that goes all the way from a filterable listing to a confirmed booking — not a landing page, but a real product with production-grade engineering. (Fictional "Sillage" brand, self-directed showcase.)

## What I built
A complete end-to-end flow:
- Filterable listing with **state kept in the URL**, an expedition page (day-by-day itinerary, gallery, cabin selection), a booking funnel (**React Hook Form + Zod**) and confirmation.
- **Next.js App Router**: SSG/ISR, server actions for booking and back-office, full SEO (sitemap, robots, JSON-LD), plus a traveler space and an admin area.

## Technical decisions
- Prisma for the data layer, Stripe for payments, server actions to keep mutations close to the server.
- URL-encoded filter state for shareable, back-button-friendly browsing.
- **Engineering rigor as a first-class goal**: tests (Vitest + Playwright), CI, accessibility and performance — explicitly "not a simple landing page".

## Tradeoffs
- Server actions over a separate API layer: faster to build and tightly typed, at the cost of some portability.

## Why this matters for Mistral
Shows fullstack craft and discipline on the exact frontend stack the role asks for (Next.js + TypeScript): a real booking funnel, payments, SEO, and a tested, accessible, CI-backed codebase.
