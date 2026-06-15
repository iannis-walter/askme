# Design System: Ask Me

The visual language for the candidate-briefing app. Source of truth: new screens
should read as if they always belonged to this dossier.

## 1. Visual theme & atmosphere

An **editorial press dossier**, not a chat tool. Warm paper, near-black ink, a
single terracotta accent, and large characterful serif headlines. The chat reads
as a printed **interview transcript** (Question / Response), and sources appear as
footnote citations. Calm and confident: generous whitespace, an asymmetric reading
column hung left of center, light restrained motion. Deliberately the opposite of
the generic dark-mode AI chatbot.

Density 3/10 (airy). Variance 6/10 (asymmetric). Motion 4/10 (restrained).
Register: **brand-leaning product** (the profile IS the pitch).

## 2. Color palette & roles

Warm-paper light theme. One accent, well under 10% coverage. Never pure black or
white; every neutral is warmed toward the paper.

- **Paper** (`#f1ece1`) — canvas / page background
- **Surface** (`#f8f4ea`) — raised surface (drawer, textarea)
- **Surface 2** (`#ece5d6`) — sunken / hover fill
- **Ink** (`#221d17`) — primary text and display
- **Ink soft** (`#463f35`) — answer / body copy
- **Muted** (`#6c6357`) — secondary text
- **Faint** (`#a39a89`) — captions, placeholders, labels
- **Rule** (`#d9d1c0`) / **Rule soft** (`#e7e0d1`) — hairline borders and dividers
- **Terracotta** (`#b34a2c`) — THE accent: eyebrows, links, CTA fill, active nav, italic emphasis, citation hover. One accent only.
- **Terracotta soft / line** (`rgba(179,74,44,0.10 / 0.30)`) — accent tints and borders
- **Grounded** (`#3f7a55`) — reserved only for the "Sourced · N" marker. Never decorative.

Ambient: one faint terracotta radial wash, top-right, fixed. No other gradients.

## 3. Typography

- **Display** — `Fraunces` (400–600), normal + italic. Big editorial headlines; tight tracking (`-0.015em`); italic in terracotta for emphasis (`A profile you can <em>interrogate</em>`). Hierarchy from face and size, not weight alone.
- **Body / reading** — `Newsreader` serif, 17px, line-height 1.62. Answers, questions, paragraphs, inputs. The "article" voice.
- **Mono** — `IBM Plex Mono` (400–500). Captions, eyebrows, role tags, nav, source citations, the source-text body. Uppercase + wide tracking (`0.16–0.2em`) for labels.
- **Banned:** Inter and generic system sans. Generic serifs (Times, Georgia, Garamond).

## 4. Components

- **Q & A transcript** — each turn is a labelled block separated by a hairline rule: a mono `QUESTION` / `RESPONSE` eyebrow, the question in large Fraunces, the answer in Newsreader.
- **Source citations** — mono, underline-on-hover footnote links (no chips, no boxes, no side-stripe). Preceded by a green "Sourced · N" marker.
- **Prompt list** — a bordered editorial list (mono label + serif prompt), not a card grid; rows nudge right and turn terracotta on hover.
- **Buttons** — terracotta pill with uppercase mono label; `scale()` press feedback. No glow.
- **Composer** — a single underline that lifts to terracotta on focus. Italic placeholder.
- **Report (job-fit)** — sections divided by top rules, not cards: mono uppercase header + serif body.
- **Drawer** — paper panel sliding from the right (`--ease-drawer`, ~320ms); backdrop click or Escape to close.
- **Loaders** — skeleton shimmer. No spinners. **Streaming caret** — blinking terracotta `▍`.

## 5. Layout

- Two-column shell: a quiet 268px **masthead** (name in Fraunces, mono nav with an active terracotta underline, mono links) + the reading stage. Collapses to a single column with a top bar under 860px.
- Reading column ~720px, hung **left of center** with a wide right margin for air (asymmetric, not dead-centered).
- Rules and whitespace do the structuring; avoid boxes and nested cards.

## 6. Motion

- Curves: `--ease-out: cubic-bezier(0.23,1,0.32,1)`; `--ease-drawer: cubic-bezier(0.32,0.72,0,1)`. Never `ease-in`, never `transition: all`.
- `fadeUp` entrances (translateY + opacity), staggered 60–80ms (intro, prompts, turns, report sections). Press feedback `scale(0.94–0.97)`. Drawer slide ~320ms.
- Animate only `transform` / `opacity`. No `scale(0)`, no bounce, no perpetual loops except the streaming caret. Honor `prefers-reduced-motion`.

## 7. Anti-patterns (banned)

- No dark "AI chatbot" shell, no second accent, no neon/glow, no gradient text.
- No colored side-stripe borders, no chip-grids of identical cards, no spinners.
- No Inter, no generic serif. No pure `#000`/`#fff`. No em dashes in copy.
- No `transition: all`, no `ease-in`, no animating layout properties.
