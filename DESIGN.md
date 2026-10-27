# Design System: Ask Iannis!

The visual language for the candidate-briefing app. Source of truth: new screens
should read as if they were the next page of the same comic.

## 1. Idea, constraint, gesture

- **Idea**: the profile is a pop comic book, *Ask Iannis!*. The recruiter asks in
  speech balloons, Iannis (drawn as a masked hero) answers, and every citation is
  an **editor's note** ("*See Issue #04: Hyperion! —Ed.") pointing to where it
  happened. Projects are **issues** of the series; knowledge files are "the Files".
- **Constraint**: only comic-book conventions. Panels with gutters, speech
  balloons, captions, sound effects, Ben-Day dots, issue covers. No generic UI
  cards, no icons, no gradients other than the halftone dots.
- **Signature gesture**: when an answer cites a source, its editor's note pops in
  and the cited issue cover slides into the "Back issues cited" panel, stamped
  **SOURCED!**.

Register: **brand-leaning product** (the profile IS the pitch). Density 6/10,
variance 8/10, motion 5/10.

## 2. Color (four plates + ink, printed on newsprint)

- **Newsprint** (`#f4ebd8`) — page background, the paper
- **Balloon** (`#fffdf6`) — speech balloons, cards, inputs
- **Ink** (`#111111`) — every border, outline, hard shadow and most text
- **Electric blue** (`#2d2df5`) — cover, question panels, "honest gaps"
- **Dot blue** (`#7c82ff`) — Ben-Day dots on blue only
- **Yellow** (`#ffd23f`) — captions, answer panels, logo, active tabs
- **Orange** (`#ff7a1a`) — ribbons, sound effects
- **Red** (`#e8322b`) — bursts, price box, citation markers, the streaming caret
- **Muted** (`#6a5f4e`) — small print (file paths, hints)

A paper-grain texture (`/art/paper-grain.jpg`) sits over everything in
`multiply`. Dots fade from the top-right corner of blue surfaces.

## 3. Typography

- **Logo** — `Luckiest Guy`: the cover title and the "Crossover!" title only.
  Yellow fill, thick ink outline (`-webkit-text-stroke` + `paint-order`), hard
  ink shadow, rotated −3°.
- **Lettering** — `Bangers`: captions, sound effects, tabs, buttons, issue
  titles. Always uppercase.
- **Balloons / body** — `Bricolage Grotesque`: questions at 800, answers at 500,
  emphasis at 800.
- **Mono** — `Space Mono`: file paths, tool calls, folio, small print.

## 4. Components

- **Masthead** — publisher bar: small lettered logo, folio, section tabs
  (`Ask` / `Job fit`, active one yellow with hard shadow), links.
- **Panel** — 3px ink border, gutter 14px, a **caption** box hung on the
  top-left corner ("A recruiter asks…", "Iannis answers:"). Tones: blue (with
  dots), yellow, cream, newsprint.
- **Speech balloon** — cream, 3px ink border, 40px radius, hard 5px shadow,
  SVG tail left or right.
- **Burst** — 24-point star in red with yellow lettering ("Ask!", "Sourced!",
  "11 sources inside!").
- **Issue cover** — a project as an issue: yellow masthead strip, red price box
  (`#04`), pop-art art, lettered title, mono tagline. Scales with `--w`.
- **Editor's note** — the citation: cream box, 2px border, rotated ±1°, red
  marker (`*`, `**`, `***`, `†`…), file path in mono. Opens the source.
- **Tool calls** ("Meanwhile, in the archives…") — mono cards, one per agent
  step, with a "Riffle! Riffle!" sound effect.
- **Composer** — the question is a speech balloon; mode tabs (`One-shot` /
  `Agent loop`); the send button is an **Ask!** burst.
- **Source drawer** — a back issue pulled from the archives: caption, cover,
  lettered title, mono source text.

## 5. Layout

- **Cover** (empty state): giant logo, ribbon tagline, hero balloon, teasers
  ("In this issue:") that send the suggested questions, the masked hero, a
  burst and a blurb, back issues that ask about each project.
- **Page** (conversation): one **tier** per turn. Row 1: question panel
  (+ archive panel in agent mode). Row 2: answer panel (+ back issues cited).
- **Job fit**: a "Special crossover issue!": title panel, the role panel, then
  findings as panels (overall fit, strongest matches, honest gaps, projects to
  show as issue covers, suggested pitch).
- Max width 1240px. Under 860px every tier stacks to one column, the mic art
  hides, the hero shrinks and sits under the balloon.

## 6. Art

All art is processed in-house into pop-art halftone (posterised plates, Ben-Day
dots, ink outlines) from:

- the masked hero: the owner's GitHub avatar (used with permission);
- "Elegant steel microphone" (Unsplash via Wikimedia Commons, CC0);
- "Container ship in Koper 2013" (Wikimedia Commons, CC0) — Vigie;
- "Apollo 9 Mission Control, S69-26107" (NASA, public domain) — Hyperion;
- "Petit Champlain at night, Quebec city" (Wikimedia Commons, CC0) — Aria;
- "Cessna 172 3-view line drawing" (Wikimedia Commons, public domain) — Flight Dynamics;
- "Prince Christian Sound Iceberg Glacier" (Wikimedia Commons, CC0) — Sillage;
- "Old Paper texture" (Wikimedia Commons, public domain) — paper grain.

Files live in `web/public/art/`. Replace an issue's art by dropping a 340×412
PNG with the same name.

## 7. Motion

- Curves: `--ease-out: cubic-bezier(0.23,1,0.32,1)`, `--ease-pop:
  cubic-bezier(0.34,1.56,0.64,1)` (stickers, notes, bursts only),
  `--ease-drawer: cubic-bezier(0.32,0.72,0,1)`.
- Panels rise in (`translate` + opacity). Notes, tool calls and teasers pop in,
  staggered ~100ms. Bursts land as a **stamp** (scale 1.8 → 1). Cited covers
  slide in from the right. Drawer slides ~320ms.
- Keyframes use the individual `translate` / `scale` / `rotate` properties so
  they compose with the static tilt of stickers.
- Perpetual loops: only the streaming caret and the "Crunch!" loading sound
  effect. Everything honors `prefers-reduced-motion`.

## 8. Anti-patterns (banned)

- No soft blurred shadows: shadows are hard and ink-coloured.
- No rounded generic cards or icon sets: use balloons, captions, notes, covers.
- No gradients except the halftone dot mask. No second hero illustration style.
- No `transition: all`, no animating layout properties.
