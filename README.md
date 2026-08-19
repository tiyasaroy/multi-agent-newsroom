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

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for the delivery roadmap.

## Status

Project initialization and architecture planning.

