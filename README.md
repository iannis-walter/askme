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
├── backend/            # FastAPI: retrieval, ranking, prompts, LLM orchestration
│   ├── main.py
│   ├── content_loader.py
│   ├── retrieve.py
│   ├── prompts.py
│   ├── llm_client.py
│   ├── schemas.py
│   ├── agent.py        # agentic tool-use loop + guardrails (native / ReAct)
│   ├── tools.py        # the tools the model can call (search_kb, list_topics, evaluate_job_fit)
│   ├── tracing.py      # per-request structured trace (steps, latency, tokens)
│   └── eval/           # offline eval suite (deterministic + optional LLM-as-judge)
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

## Agent (tool-use loop)

`/chat` is single-shot: retrieve once, inject context, one LLM call. `/chat/agent`
is the **agentic** counterpart — the model decides *which* tools to call, with
*what* arguments, *how many* times, until it can answer. Same retriever, same
prompts, same provider-agnostic client; **no orchestration framework** (no
LangChain/LlamaIndex) — a single file you can read end to end in
[`backend/agent.py`](backend/agent.py) (the core loop is ~120 lines; the rest is
the native/ReAct backends and the graceful-degradation paths).

```
messages = [system, user]
loop (≤ MAX_STEPS):
    resp = llm(messages, tools=TOOLS)
    ├─ tool_calls?  → validate args → run tool (isolated, timed) → append result → continue
    └─ no tool_calls → final answer
else (limit / loop detected) → graceful partial answer (flagged truncated)
```

**Tools** ([`tools.py`](backend/tools.py)) — each has a Pydantic argument schema,
a model-facing description, and isolated execution:

- `search_kb(query, top_k)` — wraps the retriever; callable **many times** with
  different queries to gather everything before answering.
- `list_topics()` — the KB's sections/themes, to orient a broad question.
- `evaluate_job_fit(job_description)` — wraps the job-fit logic.

**Multi-provider, one interface.** Function calling is **native** on Mistral /
Groq / OpenRouter (the `tools` parameter). For models without reliable tool
support (e.g. local Ollama) a hand-parsed **ReAct** fallback
(`Thought/Action/Observation`) implements the same loop. Pick with `AGENT_MODE`
(`auto` | `native` | `react`); `auto` chooses by provider.

**Guardrails** (treated as features, not afterthoughts):

- `AGENT_MAX_STEPS` bounds the loop (default 4); hitting it returns a graceful
  partial answer, never an error.
- per-tool and per-LLM-call timeouts (`AGENT_TOOL_TIMEOUT_S`, `AGENT_LLM_TIMEOUT_S`).
- arguments are **validated before execution**; invalid input is reported back to
  the model to retry, not crashed.
- **loop detection**: the same tool with the same arguments twice cuts the loop.
- every failure mode degrades to a clean answer — no raw exception reaches the client.
- tool results re-enter the prompt **fenced as untrusted data**, preserving the
  existing anti-injection hardening.

**Streaming** is preserved: the front-end gets the same `sources` / `delta` /
`done` NDJSON it already understood, plus a `step` event per tool call. The
optional **Agent** toggle in the chat UI renders those steps inline.

**Tracing / observability** ([`tracing.py`](backend/tracing.py)) — every request
gets a `request_id` and a structured trace: each step (LLM turn or tool call),
its latency, tokens in/out, provider/model, arguments, a truncated result, and a
`stop_reason` (`completed` | `max_steps` | `loop_detected` | `error`). Read it at
`GET /trace/{request_id}`, or attach it to the final event with `?debug=1`.

**Eval suite** ([`backend/eval/`](backend/eval/)) — `cases.json` holds ~14 cases
(`question`, `expected_facts`, `must_cite`, plus injection/honesty traps). The
runner executes the agent per case and scores it two ways:

- **deterministic** — expected facts present, forbidden strings absent, sources
  cited, step count and token cost. Reproducible.
- **LLM-as-judge** (optional, `--judge`) — a second model rates faithfulness and
  completeness 0–5 with a strict rubric. Kept **out of CI** (cost/flakiness).

```bash
cd backend
python eval/run_eval.py                      # deterministic, console report
python eval/run_eval.py --judge --json out.json   # + LLM judge + JSON report
python eval/run_eval.py --case backend-vs-ai       # one case (shows multi-search)
```

The deterministic unit tests (`backend/tests/`) mock the LLM, so they exercise
the loop, guardrails and tools **offline** — that's what runs in CI
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

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
| POST   | `/chat`      | Single-shot streamed answer (NDJSON: `sources` → `delta`s → `done`) |
| POST   | `/chat/agent`| Agentic answer: tool-use loop, streams `sources` / `step` / `delta` / `done` (`?debug=1` attaches the trace) |
| POST   | `/job-fit`   | Structured fit report for a pasted job description   |
| GET    | `/trace/{request_id}` | Structured trace of an agent request (steps, latency, tokens) |
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
