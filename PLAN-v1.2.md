# DClaw Agent — v1.2 Feature Roadmap (YC-Ready Edition)

> 📘 **REVISED PRD v2.3** is the source of truth for product identity and architecture: see `REVISED-PRD.md`.
> 📐 **AGENTS.md** is the source of truth for tech stack, ports, and anti-patterns.

## 1. Positioning — The Wedge

**One-line pitch:** *"Shopify for AI agents — build, run, and monetize agents without writing infrastructure."*

**Hair-on-fire problem we solve:**
Today an indie builder who has a working agent idea spends 80% of their time on auth, billing, multi-tenancy, hosting, retries, observability, and a publish-able UI — none of which is the agent. We collapse that to a Git push.

**Why us, why now:**
- LangChain / CrewAI / LangGraph are libraries — we are the platform.
- OpenAI GPT Store is walled; Hugging Face Spaces has no monetization; Dify and Relevance are SaaS-only.
- We ship a **self-hostable, open-marketplace, Stripe-built-in** agent platform with a local-first dev loop.
- The flywheel: builders publish → users install & pay → builders earn → more builders join.

**Defensible moat:**
1. **Marketplace network effect** — every install grows the catalog and the publisher class.
2. **Runtime portability** — the same agent graph runs in dev (SQLite + Ollama) and prod (Postgres + cloud LLM).
3. **Tool sandbox** — safe code-exec/file-IO/browser primitives that don't exist as a unit anywhere else.
4. **Self-host + cloud** — privacy-sensitive customers stay on-prem; everyone else pays our managed tier.

---

## 2. Pre-Flight Checklist (Gate before every PR)

- [ ] `frontend/package-lock.json` committed after any `npm install`
- [ ] `frontend/next-env.d.ts` present and committed
- [ ] `docker-compose.yml` healthchecks resolve (use `python urllib.request`, not curl)
- [ ] `frontend/Dockerfile` declares `ARG NEXT_PUBLIC_API_URL` **before** `RUN npm run build`
- [ ] No `default_factory=` in `mapped_column()` (use `default=` with callable)
- [ ] No timezone-aware datetimes in models (use `utc_now()`)
- [ ] No `eval()` in runtime nodes (use safe expression evaluator)
- [ ] Every new router endpoint has a test in `backend/tests/`
- [ ] Every new model has an Alembic migration

---

## 3. Complexity-Based Roadmap

Numbering convention:
- **0 — Low complexity / foundational quick wins.** Wire up infrastructure that everything else depends on. Days, not weeks.
- **1 — Medium complexity / core differentiators.** What makes the YC pitch real. Weeks of focused work.
- **2 — High complexity / advanced moat features.** What we demo to investors after Demo Day.

Every item below has: **Why**, **Acceptance**, **Files**, **Tests**.

---

### Complexity 0 — Foundation Quick Wins

#### 0.1 — Local SQLite dev fallback
**Why:** Devs without Docker should run `uvicorn` and have a working DB in <30s. AGENTS.md mandates Postgres for prod, but `aiosqlite` is already in `requirements.txt`. We just need a clean fallback.
**Acceptance:** `DATABASE_URL` unset → backend boots against `./dclaw_agent.db` (SQLite). All migrations run. Tests still pass.
**Files:** `backend/app/core/config.py`, `backend/app/core/database.py`, `.env.example`
**Tests:** Smoke test that imports `app.main:app` with no env vars set.

#### 0.2 — User & Auth scaffolding (JWT, owner_id enforcement)
**Why:** Every endpoint today is public. Multi-tenancy is impossible until we have a `User` model and JWT.
**Acceptance:** `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`. JWT bearer required on every write endpoint. `owner_id` populated from token. Existing endpoints reject anonymous writes.
**Files:** `backend/app/models/user.py`, `backend/app/api/v1/endpoints/auth.py`, `backend/app/core/security.py`, `backend/app/api/deps.py`
**Tests:** Register, login, me, ownership-rejected case.

#### 0.3 — Replace unsafe `eval()` in condition nodes
**Why:** `app/services/execution.py:120` runs arbitrary Python from user-supplied JSON. RCE risk; blocks any "publish your agent" story.
**Acceptance:** Conditions use `asteval` or `simpleeval`. Disallowed call/attr-access raises a typed `UnsafeConditionError` logged as a step failure.
**Files:** `backend/app/services/execution.py`, `backend/app/services/safe_expr.py` (new)
**Tests:** Allowed comparisons pass; `__import__('os')` rejected.

#### 0.4 — Run registry (replace fire-and-forget `asyncio.create_task`)
**Why:** Background runs today are orphaned on shutdown; cancel endpoint races. Production-fragile.
**Acceptance:** A `RunSupervisor` singleton tracks live tasks by run_id; cancel hits the task; shutdown awaits all in-flight runs.
**Files:** `backend/app/services/run_supervisor.py` (new), `backend/app/api/v1/endpoints/runs.py`, `backend/app/main.py`
**Tests:** Cancel mid-run → status `cancelled`; lifespan shutdown awaits.

#### 0.5 — Real "Runs" list endpoint + page
**Why:** `frontend/app/runs/page.tsx` is a stub. No way to see history across agents.
**Acceptance:** `GET /api/v1/agent/runs?status=&agent_id=&limit=` with pagination. Frontend page renders the table with status badges, duration, and a link to the SSE stream.
**Files:** `backend/app/api/v1/endpoints/runs.py`, `backend/app/repositories/run.py` (new), `frontend/app/runs/page.tsx`
**Tests:** Filter, paginate, ownership filter when auth is on.

#### 0.6 — Marketplace real counts + owner display
**Why:** `install_count = 0` and `owner_name = "Anonymous"` are hardcoded stubs. Kills credibility.
**Acceptance:** `install_count` derived from a `MarketplaceInstall` table; `owner_name` joined from `User`. Sort by install_count works.
**Files:** `backend/app/models/marketplace_install.py` (new), `backend/app/api/v1/endpoints/marketplace.py`, Alembic migration
**Tests:** Install increments count; uninstall decrements; owner_name is the user's display name.

#### 0.7 — Structured logging (structlog) + request_id middleware
**Why:** PRD bans `print()`. We use `print()`-free silence today; can't debug a failed run in prod.
**Acceptance:** `structlog` JSON output; every log line carries `request_id`, `run_id`, `agent_id` when in scope. Middleware emits `request_started`/`request_completed`.
**Files:** `backend/app/core/logging.py` (new), `backend/app/main.py`
**Tests:** Logger fixture asserts JSON structure on a sample log.

#### 0.8 — Deep healthcheck (`/health`)
**Why:** Today returns static OK. K8s + Docker can't distinguish DB-down from app-down.
**Acceptance:** `GET /health/` → `{status, db, llm}` with per-dependency status; returns 503 if any required dep is down. `/health/live` always 200 for liveness probes.
**Files:** `backend/app/api/routes/health.py`
**Tests:** DB up, DB down, Ollama down.

#### 0.9 — Global nav + auth-aware header
**Why:** Frontend has no consistent nav; user can't see they're logged in. Required for every later feature.
**Acceptance:** `<AppShell>` wraps every page; left nav lists Agents/Builder/Marketplace/Tools/Teams/Memory/Runs; right shows user avatar + logout.
**Files:** `frontend/app/layout.tsx`, `frontend/components/AppShell.tsx` (new), `frontend/lib/auth.ts` (new)
**Tests:** Snapshot test; clicking logout clears token.

#### 0.10 — Seed script + demo dataset
**Why:** New devs / YC demo need data on first boot. `seed.py` exists but only creates one Echo agent.
**Acceptance:** `python seed.py --demo` creates: 1 demo user, 3 sample agents (research-bot, summarizer, calculator), 2 teams, 5 memory entries.
**Files:** `backend/seed.py`
**Tests:** Idempotent re-run; row counts match.

---

### Complexity 1 — Core Differentiators (YC Demo Day Must-Haves)

#### 1.1 — AI Copilot (YC mandate, PRD §9)
**Why:** The PRD explicitly requires every app to ship a context-aware AI copilot. We have none. Non-negotiable for any YC submission citing this PRD.
**Acceptance:** Floating right-rail chat on every page. Sees current page context (agent ID, run ID). Suggests next actions ("Add a retry step", "Publish this to the marketplace"). Streams via SSE. Falls back to Ollama when cloud is unavailable.
**Files:** `backend/app/services/copilot.py` (new), `backend/app/api/v1/endpoints/copilot.py` (new), `frontend/components/Copilot.tsx` (new)
**Tests:** Suggestions endpoint returns expected actions for an agent-builder context.

#### 1.2 — pgvector / RAG for memory + copilot
**Why:** BM25 gets us 70% recall. Copilot needs semantic recall across agents, tools, and past runs. pgvector ships with Postgres; minimal infra add.
**Acceptance:** `Memory` gets an `embedding VECTOR(1536)` column (pgvector) or `embedding JSON` (sqlite fallback). New retrieval endpoint supports `mode=semantic|bm25|hybrid`. Copilot uses hybrid by default.
**Files:** `backend/app/services/memory.py`, `backend/app/services/embeddings.py` (new), Alembic migration, `backend/requirements.txt` (`pgvector`)
**Tests:** Semantic-only retrieval returns relevant doc when keyword doesn't match.

#### 1.3 — OpenRouter / Kimi cloud LLM fallback (PRD §4)
**Why:** PRD mandates `Ollama (local) → OpenRouter/Kimi (cloud)` fallback chain. We hard-code Ollama and silently return `[echo]` on failure.
**Acceptance:** `LLMClient` abstraction with providers `ollama`, `openrouter`. If `OPENROUTER_API_KEY` is set and Ollama fails or returns >timeout, fall back. Cost per call recorded.
**Files:** `backend/app/services/llm.py` (new), `backend/app/services/execution.py`
**Tests:** Mock Ollama failure → OpenRouter chosen; both fail → typed error.

#### 1.4 — Real-time streaming run UI
**Why:** SSE endpoint exists; frontend polls runs page. The "watch your agent think" moment is the entire UX.
**Acceptance:** Run detail page subscribes to `GET /runs/{id}/stream`, renders steps live, auto-scrolls, supports reconnect. LLM token-stream visible.
**Files:** `frontend/app/runs/[id]/page.tsx` (new), `frontend/lib/sse.ts` (new), `backend/app/api/v1/endpoints/runs.py` (token-stream events)
**Tests:** Playwright test verifies steps appear without page reload.

#### 1.5 — HITL approval gates
**Why:** PRD P0.3 names it. Enterprises won't deploy agents without human review on critical actions.
**Acceptance:** New `approval` node type pauses the run, posts to `/runs/{id}/approvals`. Approver hits `POST /approvals/{id}/decide` with approve/reject. Email/webhook stub on creation.
**Files:** `backend/app/models/approval.py` (new), `backend/app/services/execution.py`, `backend/app/api/v1/endpoints/approvals.py` (new), `frontend/app/approvals/page.tsx` (new)
**Tests:** Run pauses, approve resumes with new payload, reject marks run as `rejected`.

#### 1.6 — Retry + exponential backoff in runtime
**Why:** A flaky API call kills the entire run today. Production-unusable.
**Acceptance:** Tool + LLM nodes accept `retry: {max_attempts, backoff_seconds, jitter}`. Default 3 attempts, exponential. Configurable per-node in builder.
**Files:** `backend/app/services/retry.py` (new), `backend/app/services/execution.py`, `frontend/components/builder/PropertyPanel.tsx`
**Tests:** First-call-failure → succeeds on retry; permanent-failure → typed error after N.

#### 1.7 — Marketplace ratings, reviews, install tracking
**Why:** Network-effect kickstart. Without ratings the marketplace is just a JSON list.
**Acceptance:** `Rating` (1–5, comment), `Install` (with version), aggregate `average_rating`. List endpoint sorts by rating/installs/recent.
**Files:** `backend/app/models/rating.py` (new), `backend/app/models/marketplace_install.py` (extended), `backend/app/api/v1/endpoints/marketplace.py`, `frontend/app/marketplace/[id]/page.tsx`
**Tests:** Average is computed; one rating per user per agent.

#### 1.8 — Stripe metered billing skeleton
**Why:** YC asks: "How do you make money on day one?" — we have to demonstrate the path. Stripe Customer + Subscription + usage record is enough to demo.
**Acceptance:** Webhook handler creates `BillingCustomer` on user signup; `meter_run()` posts usage records (tokens, runs). Settings page shows current plan.
**Files:** `backend/app/services/billing.py` (new), `backend/app/api/v1/endpoints/billing.py` (new), `frontend/app/settings/billing/page.tsx` (new)
**Tests:** Webhook signature check; meter records emit; mock Stripe client.

#### 1.9 — Per-run cost attribution
**Why:** Builders need to know "how much did that run cost?" — and we need it for metered billing.
**Acceptance:** `AgentRun.cost_usd`, `AgentRun.tokens_input/output`. LLM provider returns token usage; stored per step and aggregated on run.
**Files:** `backend/app/services/llm.py`, `backend/app/models/agent.py`, `backend/app/services/execution.py`
**Tests:** Mock provider returns counts; run aggregates correctly.

#### 1.10 — Parallel multi-agent orchestration
**Why:** `workflow_type` is sequential-only. CrewAI ships parallel, conditional, hierarchical. We must match.
**Acceptance:** `TeamTemplate` supports `parallel` and `hierarchical` modes. `parallel` runs all members in `asyncio.gather`. `hierarchical` lets a manager-agent delegate to sub-agents.
**Files:** `backend/app/services/multi_agent.py`, `backend/app/models/agent.py` (workflow_type enum)
**Tests:** Parallel completes when all done; hierarchical delegates and aggregates.

#### 1.11 — RBAC + audit log
**Why:** Enterprises won't talk to us without these. PRD P1.4 lists them.
**Acceptance:** Roles `owner`, `editor`, `viewer` per agent and per team. Every mutating action writes an `AuditLogEntry` (actor, action, target, before/after).
**Files:** `backend/app/models/audit.py` (new), `backend/app/models/membership.py` (new), `backend/app/api/deps.py` (role checks)
**Tests:** Viewer can't edit; audit log captures the rejected attempt.

#### 1.12 — Webhooks (run-completed, run-failed, approval-needed)
**Why:** Integrations are how agents become useful. Slack, Zapier, custom systems.
**Acceptance:** Users register webhooks; runtime fires on lifecycle events with HMAC signature. Retry on 5xx with backoff.
**Files:** `backend/app/models/webhook.py` (new), `backend/app/services/webhooks.py` (new), `backend/app/api/v1/endpoints/webhooks.py` (new)
**Tests:** Signature validated; failed delivery retried.

---

### Complexity 2 — Advanced Moat Features

#### 2.1 — LangGraph integration (planner-executor, cycles, branching)
**Why:** Our custom DAG is acyclic. Real agentic reasoning needs planner-executor loops and re-planning. LangGraph is the standard.
**Acceptance:** New node type `langgraph_subgraph` lets a builder drop in a compiled LangGraph state machine. Step logs preserve LangGraph node names.
**Files:** `backend/app/services/langgraph_runtime.py` (new), `backend/requirements.txt`
**Tests:** A re-planning agent that retries with a different tool succeeds.

#### 2.2 — Browser-use agent (Playwright sandbox)
**Why:** MultiOn / Adept / Browserbase are YC-funded specifically for this. The "watch the agent click around" demo is irresistible.
**Acceptance:** `browser` tool: launches headless Chromium in a Docker-isolated container; supports `goto`, `click`, `type`, `screenshot`. Screenshots stream back to the UI.
**Files:** `backend/app/services/tools/browser.py` (new), `docker/browser-sandbox/Dockerfile` (new)
**Tests:** Open example.com, screenshot, assert non-empty PNG.

#### 2.3 — Code-interpreter agent (Docker-isolated)
**Why:** "Run untrusted Python" is a hard problem we can productize. Today `code_executor` uses subprocess — easy to escape.
**Acceptance:** `python` tool runs in ephemeral container with no network, CPU/memory caps, 30s timeout. Returns stdout, stderr, plots (matplotlib → PNG).
**Files:** `backend/app/services/tools/python_sandbox.py` (new), `docker/code-sandbox/Dockerfile` (new)
**Tests:** Compute factorial(10); attempt network call → blocked.

#### 2.4 — Scheduled + event-driven triggers
**Why:** Today agents only run on manual invocation. PRD P1.5 names this.
**Acceptance:** `Trigger` model: `cron` (5 1 * * *), `webhook` (inbound URL), `manual`. Scheduler runs in a separate worker process.
**Files:** `backend/app/services/scheduler.py` (new), `backend/app/models/trigger.py` (new), `backend/app/workers/scheduler_worker.py` (new)
**Tests:** Cron fires within tolerance; webhook URL creates a run.

#### 2.5 — Agent versioning + canary deploy
**Why:** PRD P2.3. Rollback story for production users.
**Acceptance:** Semantic version on every publish. `GET /marketplace/{id}/versions`. Install pins a version. Canary: route X% of traffic to v2.
**Files:** `backend/app/models/agent_version.py` (new), `backend/app/api/v1/endpoints/marketplace.py`
**Tests:** Pin v1.0.0, publish v1.1.0, both available; canary routes correctly.

#### 2.6 — Publisher payouts & revenue share
**Why:** Marketplace flywheel requires builders to actually earn.
**Acceptance:** Stripe Connect Express onboarding. Per-install / per-run revenue split (70/30 default). Payout dashboard.
**Files:** `backend/app/services/payouts.py` (new), `frontend/app/settings/payouts/page.tsx` (new)
**Tests:** Mock Stripe transfer; balance reconciles.

#### 2.7 — Multi-tenant org workspaces
**Why:** Teams of >1 person need shared workspaces, shared agents, shared billing.
**Acceptance:** `Organization` model with members + roles. Org-scoped agents/teams/memory. Org-level billing.
**Files:** `backend/app/models/organization.py` (new), every scoped model gets `organization_id`
**Tests:** Cross-org access rejected.

#### 2.8 — Real-time multiplayer agent builder
**Why:** Figma-for-agents. Differentiation against single-player builders.
**Acceptance:** Yjs CRDT backend for the canvas; presence cursors; conflict-free merges. Powered by `y-websocket` server.
**Files:** `backend/app/workers/yjs_server.py` (new), `frontend/components/builder/MultiplayerCanvas.tsx`
**Tests:** Two browser sessions edit same agent; both see changes.

#### 2.9 — Observability stack (Prometheus, OpenTelemetry, Grafana)
**Why:** PRD §4 mandates Prometheus + Grafana. Enterprise customers ask "Where are my dashboards?" on call 1.
**Acceptance:** `/metrics` Prometheus endpoint. OTel spans for every run / node. Ships a Grafana dashboard JSON.
**Files:** `backend/app/core/metrics.py` (new), `backend/app/core/tracing.py` (new), `observability/grafana/dashboards/*.json`
**Tests:** Metric counter increments on run; span context propagates.

#### 2.10 — Agent insurance / output guarantees (research)
**Why:** PRD P2.4. Differentiates us; nobody else has it.
**Acceptance:** `Guarantee` model: SLA on output quality, escrow on subscription. Dispute filing endpoint + manual resolver UI. Pure-MVP — no actuarial science yet.
**Files:** `backend/app/models/guarantee.py` (new), `backend/app/api/v1/endpoints/guarantees.py` (new)
**Tests:** Create guarantee, file dispute, resolve.

#### 2.11 — Embed SDK / white-label widget
**Why:** PRD P2.4. Distribution: every embed is free marketing.
**Acceptance:** `<script src="https://cdn.dclawstack.io/embed.js" data-agent="...">` renders a chat widget. Themable.
**Files:** `embed/src/index.ts` (new package), `embed/Dockerfile` (CDN build)
**Tests:** Embed loads, sends message, receives streamed reply.

---

## 4. Implementation Sequence

**Sprint A (Complexity-0, weeks 1–2): Foundation hardening.** 0.1 → 0.10 in order. Goal: every later feature can assume auth, logging, supervised runs, and a real runs page.

**Sprint B (Complexity-1 core, weeks 3–5): Copilot + LLM + Streaming.** 1.1, 1.2, 1.3, 1.4 — the "wow" of the demo.

**Sprint C (Complexity-1 platform, weeks 6–8): HITL + Retry + Marketplace + Billing.** 1.5, 1.6, 1.7, 1.8, 1.9 — the YC pitch.

**Sprint D (Complexity-1 enterprise, weeks 9–10): RBAC + Audit + Webhooks + Parallel teams.** 1.10, 1.11, 1.12 — close enterprise pilots.

**Sprint E+ (Complexity-2, post-Demo-Day): Moat.** 2.1 → 2.11 prioritized by customer pull.

---

## 5. Definition of Done (per feature)

A feature is "done" when **all** of the following are true:
1. Backend tests pass (`cd backend && pytest -v`).
2. Frontend builds (`cd frontend && npm run build`).
3. `docker compose up` boots without errors.
4. AGENTS.md anti-patterns are not introduced.
5. New routes covered by at least one test.
6. New models have an Alembic migration.
7. README or `docs/` updated where user-facing.
8. PR description names the roadmap item (e.g., `Closes 0.3`).

---

## 6. Out of Scope (deliberately)

- Mobile apps (PWA only for now)
- On-device fine-tuning
- Marketplace for non-agent assets (datasets, prompts)
- Voice agents (post-2.x)

---

## 7. Open Decisions

- **Vector store:** pgvector (in-Postgres, simpler ops) vs Qdrant (faster, separate service). **Tentative: pgvector** for v1.2 — revisit if recall@10 drops below 0.7.
- **LLM defaults:** Ollama default model is `llama3.1`. Cloud default via OpenRouter is `meta-llama/llama-3.1-8b-instruct`. Both cheap; revisit when quality is the bottleneck.
- **Browser sandbox:** Playwright in Docker (proven) vs Browserbase API (faster ramp, vendor lock). **Tentative: Playwright** — self-hostable per our positioning.

---

*Plan version: 2.0*
*Updated: 2026-05-20*
*Next review: end of Sprint A.*
