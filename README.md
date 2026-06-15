# Ask Me — Conversational candidate profile

A source-grounded conversational interface for exploring a candidate's profile.
Ask questions in natural language and get answers that are **grounded only in a
curated knowledge base** — every answer shows the exact files it drew from, so
nothing is invented. A **Job fit** mode takes a pasted job description and returns
a structured match: strengths, honest gaps, the projects worth showing, and a
tailored pitch.

Built as an applied-AI work product, not a portfolio gadget: a clean
conversational UX, a transparent retrieval layer, and a **provider-agnostic LLM
layer** (OpenAI-compatible) that runs on a free local model in dev and a free
hosted open-source model in production.

## Why it's built this way

The product rests on the **quality and structure of the knowledge base**, not on
model sophistication. Retrieval is **semantic** (`mistral-embed`): chunk vectors
are precomputed into a committed, content-hash-keyed cache
(`backend/embeddings.json`), so a Render cold start loads instantly with no
embedding calls at boot. A keyword + IDF scorer remains as the fallback for local
dev (Ollama, no key) and if a query embedding ever fails. Pick with `RETRIEVER`
(`auto` | `embeddings` | `keyword`). After editing `content/`, regenerate the
cache with `python backend/build_embeddings.py` and commit `embeddings.json`.

The split is deliberate:

- **`backend/` — Python / FastAPI** owns the applied-AI work: loading the
  knowledge base, retrieving and ranking the most relevant chunks, building
  grounded prompts, and orchestrating the LLM (streaming + JSON) through a
  provider-agnostic client (Ollama, Groq, Mistral, OpenRouter — switched by env).
- **`web/` — Next.js 15 / TypeScript** is the product layer: the conversational
  UI and thin route handlers that proxy to the backend. The browser never holds
  the API key or talks to Mistral directly.

```
ask-me/
├── content/            # the knowledge base (JSON + Markdown) — the single source of truth
│   ├── bio.json
│   ├── experience.json
│   ├── skills.json
│   ├── faq.json
│   ├── projects/*.md
│   └── roles/*.md
├── backend/            # FastAPI: retrieval, ranking, prompts, Mistral orchestration
│   ├── main.py
│   ├── content_loader.py
│   ├── retrieve.py
│   ├── prompts.py
│   ├── mistral_client.py
│   └── schemas.py
└── web/                # Next.js: chat UI, job-fit page, proxy routes
    ├── app/
    ├── components/
    └── lib/
```

## Security

User-supplied text (chat questions, conversation, and the pasted job description)
is untrusted. The backend treats it as **data, never instructions**: system
prompts state this explicitly, untrusted input is wrapped in fenced delimiters
with a trailing reminder, and Pydantic caps input length and turn count
(oversized requests get a 422). A lightweight heuristic logs likely injection
attempts (`backend/guards.py`) for visibility — it does not block, to avoid false
positives on legitimate job descriptions.

## The LLM layer (provider-agnostic)

The backend speaks the **OpenAI-compatible Chat Completions API**, so the model
provider is just configuration — no code changes to switch. See
[`backend/llm_client.py`](backend/llm_client.py).

| `LLM_PROVIDER` | Use for | Cost | Key |
| -------------- | ------- | ---- | --- |
| `ollama` (default) | Local dev — runs an open-source model on your machine | Free | None |
| `mistral` | **Production** — Mistral's "Free mode" (~1 req/s, ~1B tok/mo) | Free tier | `LLM_API_KEY` |
| `groq` | Alt: open-source models (Llama 3.3) hosted for you | Free tier | `LLM_API_KEY` |
| `openrouter` | Alt: wide model choice, incl. free models | Free tier+ | `LLM_API_KEY` |

Each provider has preset URL + model; override with `LLM_MODEL` / `LLM_API_URL`.
`LLM_MIN_INTERVAL_S` paces upstream calls (set to `1.1` for the Mistral free tier
so concurrent visitors queue instead of hitting its ~1 req/s cap).

> **Why not run the model inside the deployment?** A serverless host (Vercel)
> has no GPU, tight memory/time limits, and ephemeral functions — it cannot host
> an LLM. The model always runs elsewhere; in production that's the Mistral API
> (free tier), reached over HTTP exactly like any other provider.

## Running it locally

You need Python 3.11+ and Node 18+. For the default local setup, install
[Ollama](https://ollama.com) and pull a model: `ollama pull llama3.1`
(no API key needed). Prefer the hosted Mistral free tier instead? Get a free key
at [console.mistral.ai](https://console.mistral.ai) and set `LLM_PROVIDER=mistral`.

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # defaults to Ollama; edit to use Groq if you like
uvicorn main:app --reload --port 8000
```

Check it's up: `curl localhost:8000/health`.

### 2. Front-end (Next.js)

```bash
cd web
npm install
cp .env.local.example .env.local   # BACKEND_URL defaults to http://localhost:8000
npm run dev
```

Open http://localhost:3000.

### Or both at once

```bash
# from the repo root, after installing deps for each
./run-dev.sh
```

### Or with Docker

The container can't reach an Ollama on your host, so compose defaults to Mistral:

```bash
LLM_API_KEY=<mistral_key> docker compose up --build
```

## Editing the content

Everything the assistant can say lives in `content/`. Edit those files, then —
if using embeddings — regenerate the cache with `python backend/build_embeddings.py`
and commit `backend/embeddings.json`. Restart the backend. (In `keyword` mode,
just restart — no cache step.)

## API

| Method | Route        | Purpose                                              |
| ------ | ------------ | ---------------------------------------------------- |
| POST   | `/chat`      | Streamed answer (NDJSON: `sources` → `delta`s → `done`) |
| POST   | `/job-fit`   | Structured fit report for a pasted job description   |
| GET    | `/sources`   | Raw content of one source, for the UI drawer         |
| GET    | `/health`    | Liveness + document count                            |

## Deployment (free, end-to-end)

Three pieces, each where it belongs — the model is **never** inside the Vercel
deployment. Total cost: **$0**.

```
Browser → Vercel Hobby (web/, Next.js UI + proxy routes)     ← free
            → Render free (backend/, FastAPI: retrieval + prompts)   ← free
              → Mistral API, Free mode (the model runs here, over HTTP)   ← free
```

**Backend → Render** (Blueprint in [`render.yaml`](render.yaml)): New → Blueprint →
this repo. The Dockerfile builds from the repo root so `content/` is baked in.
Set two secrets in the dashboard: `LLM_API_KEY` (your Mistral free-tier key) and
`FRONTEND_ORIGIN` (`https://<your-app>.vercel.app`, for CORS). The rest
(`LLM_PROVIDER=mistral`, model, `LLM_MIN_INTERVAL_S=1.1`) is preset in the
blueprint. Note: the free plan sleeps after ~15 min idle, so the first request
after a pause has a ~30-50s cold start.

**Front-end → Vercel** (config in [`web/vercel.json`](web/vercel.json)): set the
project **Root Directory** to `web/`, and add one env var `BACKEND_URL` pointing
at the Render URL. Vercel hosts only the UI — no API key ever lives here.

**Rate limiting** is built in: per-IP sliding-window limits on `/chat` and
`/job-fit` (abuse protection, [`backend/ratelimit.py`](backend/ratelimit.py)),
plus upstream pacing (`LLM_MIN_INTERVAL_S`) so concurrent visitors queue rather
than tripping the Mistral free-tier cap.

## Possible next steps

- Per-project detail pages (`/projects/[slug]`).
- Conversation history persistence.
