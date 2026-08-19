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

Prerequisites: Node.js 20+, pnpm 9+, Python 3.11+, and Docker with Compose.

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

Database schema changes are managed with Alembic migrations. Source snapshots are
stored independently from their original URLs so future fact-checking agents can
always audit the exact evidence used during an investigation.
