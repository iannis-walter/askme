# Design System: Ask Me

The visual language for the candidate-briefing app. Treat this as the source of
truth: new screens and components should read as if they always belonged here.

## 1. Visual theme & atmosphere

A **briefing console**: a calm, dark, instrument-panel surface where every answer
arrives with its telemetry (the sources it drew from). Clinical but warm, like a
dim studio at dusk with one shaft of low sun. Density is balanced (4/10) — roomy
reading column, never a dashboard cockpit. Motion is restrained but precise
(5/10): nothing decorative loops; entrances and presses are crisp and fast.

Register: **product** (the design serves the conversation, it is not the show).

## 2. Color palette & roles

Tinted-neutral base with a single warm accent. Restrained strategy: the accent
covers well under 10% of any view. Never pure black or pure white.

- **Ink** (`#0f1116`) — app background, deepest surface
- **Surface** (`#161922`) — sidebar, cards, composer, drawer
- **Surface 2** (`#1d212c`) — raised / hover fills, user bubble
- **Border** (`#2a2f3c`) — structural 1px lines
- **Border soft** (`#21252f`) — quieter dividers
- **Text** (`#e8eaf0`) — primary text
- **Muted** (`#9097a6`) — secondary text, metadata
- **Faint** (`#6a7080`) — eyebrows, placeholders, captions
- **Ember** (`#e26d3a`) — THE accent: CTAs, active nav, focus, source caret, streaming caret. The "mistral wind / southern sun." One accent only.
- **Ember soft** (`rgba(226,109,58,0.12)`) — accent tint fills (active nav, hovered source tag, pills)
- **Ember line** (`rgba(226,109,58,0.32)`) — accent borders / focus rings
- **Grounded** (`#5bbf9b`) — reserved exclusively for the grounding indicator (the "N sources" dot). Never use it decoratively.

Ambient: a single faint ember radial glow, top-left, fixed. No other gradients.

## 3. Typography

- **Display** — `Instrument Serif`, 400 weight, tight tracking (`-0.01em`). Hero titles, drawer/source titles. Distinctive editorial serif; hierarchy comes from it, not from screaming size.
- **Body** — `Inter`. 15px, line-height 1.6. Reading column capped ~760px.
- **Mono** — `IBM Plex Mono`. The telemetry voice: eyebrows, role tags, source tags, nav glyphs, code/source bodies. Uppercase + wide letter-spacing (`0.14–0.18em`) for eyebrows.

Eyebrows are the signature label: 11px mono, uppercase, `--faint`.

## 4. Components

- **Buttons** — flat, no glow. Press feedback is mandatory: `transform: scale()` on `:active` (send 0.92, primary/chip ~0.97) over `120ms var(--ease-out)`. Primary = ember fill on dark ink text.
- **Source tags** — the signature element: mono "readout" chips with a leading ember caret (`›`), full 1px border, ember-soft tint + ember-line border on hover. (No colored side-stripe borders, ever.)
- **Grounded indicator** — small glowing `--grounded` dot + "Grounded · N sources" in mono.
- **Cards** (job-fit report) — `--surface` fill, 1px border, 14px radius, mono uppercase section headers. Used only where elevation earns it; never nested.
- **Composer / inputs** — `--surface` fill, border lifts to `--ember-line` on focus. No floating labels.
- **Drawer** — slides in from the right over a dimmed backdrop; `var(--ease-drawer)` curve, ~300ms. Closes on backdrop click or Escape.
- **Loaders** — skeletal shimmer matching layout dimensions. No spinners.
- **Streaming caret** — blinking ember `▍` while the answer streams.

## 5. Layout

- Two-column app shell: 248px sidebar + fluid stage. Collapses to a single column with a top bar under 820px.
- Reading column capped at 760px, centered. Vary vertical spacing for rhythm; avoid uniform padding.
- Don't wrap everything in a card. Most content is just type on the surface.

## 6. Motion

- Curves: `--ease-out: cubic-bezier(0.23,1,0.32,1)` for UI; `--ease-drawer: cubic-bezier(0.32,0.72,0,1)` for the drawer. Never `ease-in`, never `transition: all`.
- Durations: presses 100–160ms, entrances 360–480ms, drawer ~300ms. Keep UI motion under ~300ms except deliberate entrances.
- Animate only `transform` and `opacity`. Entrances are `fadeUp` (translateY 8px + opacity), staggered 50–80ms (intro, chips, report cards).
- Nothing animates from `scale(0)`. No bounce, no elastic, no perpetual loops (except the streaming caret).
- Always honor `prefers-reduced-motion: reduce` (near-zero durations).

## 7. Anti-patterns (banned)

- No colored side-stripe borders (`border-left`/`right` > 1px as an accent).
- No gradient text, no glassmorphism-by-default, no neon/outer-glow shadows.
- No `transition: all`, no `ease-in` on UI, no animating layout properties.
- No second accent color; `--grounded` is not decorative.
- No pure `#000` / `#fff`. No identical 3-card grids. No em dashes in copy.
- No spinners where a skeleton fits. No `scale(0)` entrances.
