# Multi-Agent Newsroom: Project Plan

## 1. Product objective

Build a portfolio-grade newsroom platform that turns a developing event into a
source-backed, editor-approved story. The product must make agent activity,
evidence, uncertainty, contradictions, and revisions visible instead of hiding
them behind a single chat response.

## 2. Showcase scenario

The primary demonstration begins with several conflicting reports about the same
event. The system clusters them into one story, extracts and compares claims,
builds a timeline, launches an appropriate agent team, drafts an article, runs
adversarial review, and presents a human editor with publication controls and a
complete audit trail.

## 3. Product surfaces

### Newsroom dashboard

- Live story clusters ranked by urgency, impact, and confidence
- Ingestion health and source coverage
- Active agent runs, alerts, and editorial queues

### Investigation workspace

- Source reader with provenance and credibility signals
- Claims-and-evidence graph
- Event timeline and contradiction view
- Agent activity stream and assignment controls

### Editorial desk

- Draft editor with sentence-level citations
- Fact-check, bias, legal, and safety findings
- Side-by-side revisions and agent recommendations
- Approve, reject, request revision, and publish controls

### Operations and evaluation

- Prompt/model configuration and routing
- Run traces, latency, token usage, and cost
- Evaluation suites and failure analysis
- Source and agent performance metrics

## 4. System design

### Core services

1. **Web application** — newsroom UI, editorial workflows, and live updates.
2. **Application API** — authentication, projects, stories, drafts, and approvals.
3. **Ingestion service** — RSS, URL, document, and manual lead processing.
4. **Story intelligence service** — deduplication, clustering, entities, and timelines.
5. **Agent orchestrator** — typed workflows, parallel tasks, retries, and checkpoints.
6. **Evidence service** — claims, citations, contradictions, and confidence scoring.
7. **Worker system** — durable long-running research and generation jobs.
8. **Evaluation service** — factuality, citation integrity, quality, and regression tests.

### Initial domain model

- Workspace, User, Role
- Source, SourceDocument, SourceSnapshot
- StoryCluster, Story, Event, Entity
- Claim, Evidence, Citation, Contradiction
- Assignment, AgentRun, AgentMessage, ToolCall
- Draft, DraftRevision, ReviewFinding
- Approval, Publication, Correction
- EvaluationCase, EvaluationRun, Metric

### Non-negotiable engineering rules

- Every material factual claim must link to evidence.
- Generated content must distinguish facts, inference, and uncertainty.
- External content is untrusted input and must not control agent behavior.
- Long-running workflows must be resumable and idempotent.
- Publication always requires an explicit human action.
- Every model and editorial decision must be auditable.

## 5. Delivery roadmap

### Phase 0 — Foundation

**Goal:** establish a reliable monorepo and local development environment.

- Architecture decision records and threat model
- Next.js web app and FastAPI service
- Shared schemas and API contract
- PostgreSQL, Redis, migrations, and seed data
- Containerized local environment
- Formatting, linting, tests, and CI
- Structured logging and configuration management

**Exit condition:** one command starts the stack and CI validates a sample change.

### Phase 1 — Vertical-slice newsroom

**Goal:** complete one story from submitted sources to editor approval.

- URL/text source submission
- Immutable source snapshots and metadata extraction
- Story creation and source attachment
- Researcher, Reporter, Fact-Checker, and Editor agents
- Durable workflow state and live agent activity
- Citation-aware draft format
- Editorial review and approval screen
- Mock-model mode for deterministic tests

**Exit condition:** a user can submit conflicting sources and approve a cited draft.

### Phase 2 — Evidence intelligence

**Goal:** make trust and disagreement visible.

- Atomic claim extraction
- Claim-to-evidence relationships
- Corroboration and contradiction detection
- Source independence and credibility signals
- Event timeline construction
- Interactive evidence graph
- Confidence model with explainable component scores
- Unsupported-claim publication blockers

**Exit condition:** editors can inspect why every important sentence is trusted.

### Phase 3 — Adaptive multi-agent newsroom

**Goal:** demonstrate genuinely dynamic orchestration.

- Editor-in-Chief planner and assignment policies
- Beat-specific agent teams
- Parallel research with bounded budgets
- Skeptical, bias, data, and legal/safety reviewers
- Agent debate with structured objections and resolutions
- Checkpoints, retries, cancellation, and human intervention
- Model routing by task, risk, latency, and cost

**Exit condition:** different stories produce different, observable workflows.

### Phase 4 — Live news operations

**Goal:** handle evolving stories continuously.

- RSS and approved feed ingestion
- Near-duplicate detection and semantic clustering
- Story urgency and impact ranking
- Breaking-news alerts
- Timeline updates and change detection
- Draft invalidation when supporting evidence changes
- Corrections and post-publication provenance

**Exit condition:** a developing story updates without losing its prior audit history.

### Phase 5 — Evaluation, security, and reliability

**Goal:** make quality measurable and the system defensible.

- Curated truth-set and misinformation test cases
- Citation entailment and citation-completeness checks
- Factuality, bias, style, latency, and cost evaluations
- Prompt-injection and poisoned-source defenses
- Authorization, rate limits, secrets handling, and audit logs
- Load, failure-recovery, and workflow replay tests
- Quality dashboards and release gates

**Exit condition:** regressions are detected automatically before deployment.

### Phase 6 — Publication and presentation

**Goal:** turn the system into a polished public demonstration.

- Publication destinations and export formats
- Newsletter, social, briefing, and audio-script derivatives
- Public article provenance page
- Guided demo data and cinematic newsroom mode
- Accessibility, responsive design, and performance work
- Deployment, monitoring, documentation, and demo video

**Exit condition:** a reviewer can understand the value in five minutes and inspect
the technical depth afterward.

## 6. Recommended build sequence

Build vertical slices rather than completing entire infrastructure layers. The
first slice should contain a minimal UI, API, database path, agent run, evidence
record, draft, and human approval. Each later iteration deepens that same path.

1. Monorepo and local stack
2. Story/source data model
3. Deterministic four-agent workflow
4. Live activity and editorial approval UI
5. Claims, citations, and contradictions
6. Dynamic orchestration and specialist agents
7. Continuous ingestion and evolving stories
8. Evaluations, security, deployment, and polish

## 7. Quality strategy

- Unit tests for scoring, state transitions, and parsers
- Contract tests for API and structured model outputs
- Integration tests for databases, queues, and workflow recovery
- End-to-end tests for the editor journey
- Golden evaluation cases for article and citation quality
- Adversarial tests for false consensus, source poisoning, and prompt injection
- Performance budgets for time-to-first-update and completed investigation cost

## 8. Initial success metrics

- Citation precision and material-claim citation coverage
- Contradiction detection recall on the evaluation set
- Percentage of drafts blocked for intentionally unsupported claims
- Human acceptance and revision rates
- Workflow completion and recovery rates
- Median investigation latency and cost
- Time required for an editor to validate a story

## 9. Near-term backlog

1. Record architecture decisions for monorepo, orchestration, and data storage.
2. Scaffold the web app, API, shared contracts, and local infrastructure.
3. Define story, source, claim, evidence, draft, and run schemas.
4. Implement a deterministic workflow simulator before connecting live models.
5. Build the investigation workspace around a seeded conflicting-source story.
6. Add model integrations behind provider-neutral interfaces.
7. Establish evaluation fixtures and CI release gates early.

