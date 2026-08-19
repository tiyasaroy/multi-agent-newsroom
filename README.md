# Multi-Agent Newsroom

An evidence-first AI newsroom where specialized agents discover, investigate,
challenge, edit, and prepare news stories while humans retain publication control.

## Product vision

Multi-Agent Newsroom is not just an article generator. It is a transparent
editorial workspace that shows how a story was produced: which sources support
each claim, where reports conflict, how confidence changes over time, and which
human approved publication.

## Core workflow

1. Ingest feeds, URLs, documents, and user-submitted leads.
2. Cluster related material into evolving stories.
3. Assign a specialist agent team based on the story and beat.
4. Extract claims, evidence, quotations, entities, and event timelines.
5. Draft an article and subject it to fact-checking and adversarial review.
6. Show editors the evidence graph, unresolved risks, and revision history.
7. Publish only after explicit human approval.

## Planned agents

- Assignment Editor
- Source Scout
- Investigative Researcher
- Data Journalist
- Beat Reporter
- Fact-Checker
- Skeptical Reviewer
- Bias and Framing Analyst
- Legal and Safety Reviewer
- Copy Editor
- Visual Story Producer
- Audience Editor
- Editor-in-Chief

## Proposed architecture

- **Web:** Next.js, TypeScript, Tailwind CSS
- **API and orchestration:** Python, FastAPI, typed agent state machine
- **Data:** PostgreSQL with pgvector
- **Jobs and streaming:** Redis-backed workers and WebSockets/SSE
- **Storage:** S3-compatible object storage
- **Observability:** structured traces, token/cost accounting, evaluation results
- **Deployment:** containerized services with CI/CD

## Status

Foundation development: monorepo, web application, API, and local data services.

## Repository layout

```text
apps/web/          Next.js newsroom interface
services/api/      FastAPI application and future agent orchestrator
packages/contracts Shared API schemas
infra/             Local infrastructure configuration
```

## Local development

Prerequisites: Node.js 24+, pnpm 11+, Python 3.11+, and Docker with Compose.

```bash
cp .env.example .env
make install
make infra-up
make db-migrate
make dev
```

The web application runs at `http://localhost:3000`, the API at
`http://localhost:8000`, and interactive API documentation at
`http://localhost:8000/docs`.

Run all currently configured checks with:

```bash
make check
```

## Current API

- `POST /api/v1/stories` creates a developing story.
- `GET /api/v1/stories` lists and filters stories.
- `GET /api/v1/stories/{story_id}` returns a story with its source snapshots.
- `POST /api/v1/stories/{story_id}/sources` attaches immutable source material.
- `POST /api/v1/stories/{story_id}/investigations` runs the deterministic agent team.
- `GET /api/v1/investigations/{run_id}` returns events, claims, citations, and the draft.
- `GET /api/v1/investigations/{run_id}/events` streams agent activity with SSE.
- `POST /api/v1/investigations/{run_id}/retry` retries a blocked or failed run.
- `POST /api/v1/investigations/{run_id}/cancel` cancels queued or running work.

Database schema changes are managed with Alembic migrations. Source snapshots are
stored independently from their original URLs so future fact-checking agents can
always audit the exact evidence used during an investigation.

The initial workflow uses deterministic implementations of the Assignment
Editor, Researcher, Reporter, and Fact-Checker. It exercises durable agent state,
parallel source research, citations, idempotency, and editorial blocking without
requiring model credentials. Live model providers will plug into this boundary in
a later milestone.

### Model-backed investigations

Set `NEWSROOM_PROVIDER=openai` and `OPENAI_API_KEY` in the local `.env` file to
use the OpenAI Responses API. `OPENAI_MODEL` controls the model and defaults to
`gpt-5.4-mini`. If credentials are absent, the system automatically falls back
to the deterministic workflow. The `mock` provider exercises the full
model-shaped path without network calls.

Add `?background=true` when starting an investigation to receive a queued run
immediately, then subscribe to its `/events` endpoint. Each model-backed agent
stage records its provider, model, prompt version, token usage, latency, and an
optional cost estimate.
