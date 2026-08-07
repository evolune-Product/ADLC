# Phase 11 — Implementation Report

**Date:** August 2026 · **Scope:** the commercial, governance and intelligence layer
**Companions:** [`MARKET_AND_COMPETITIVE_RESEARCH_2026.md`](./MARKET_AND_COMPETITIVE_RESEARCH_2026.md) · [`BUSINESS_PLAN_2026.md`](./BUSINESS_PLAN_2026.md)

---

## What was built and why

Every item traces to a gap the research identified — either an investor question the product could not answer, or a competitive position it could not defend.

| Gap (from research) | Built | Where |
|---|---|---|
| "Who pays and how?" — no billing at all | Plans, subscriptions, metered runs, quota enforcement, per-run budget caps, Stripe checkout/portal/webhooks, BYO-LLM keys | `models/billing.py`, `services/metering_service.py`, `services/stripe_service.py`, `routers/billing.py`, `BillingPage` |
| Approval gate had no teeth — one approver, no conditions | Policy engine: N-approver rules, reviewer-score thresholds, blocking severities, protected paths/branches, file-count and cost caps, per-environment scoping | `models/governance.py`, `services/policy_service.py`, `routers/governance.py`, `PoliciesPage` |
| Reviewer agent existed only on the roadmap — the stated differentiator was unbuilt | Reviewer agent producing structured findings, scoring, and PR comments; gates the deploy | `agents/review_agent.py`, `models/insight.py`, `ReviewFindings` |
| Gate is worthless if the reviewer never hears about it | In-app bell, email, Slack, signed outbound webhooks; per-user channel preferences | `models/notification.py`, `services/notifier.py`, `services/webhook_service.py`, `NotificationBell` |
| No ROI story — the retention and upsell narrative | Cycle time, approval latency, cost per merged run, hours/money saved with tunable assumptions, agent scorecards, CSV export | `services/analytics_service.py`, `routers/insights.py`, `AnalyticsPage` |
| No improvement loop; runs were binary pass/fail | Run feedback (thumbs + category + comment) feeding agent scorecards | `models/insight.py`, `FeedbackWidget` |
| Model lock-in — Anthropic was hardcoded | Provider abstraction (Anthropic / OpenAI / Azure / OpenAI-compatible / Ollama), per-org BYO key, token accounting and costing on every call | `services/llm_service.py` |
| Agents started cold on every run | Codebase memory: repo indexing, embeddings, retrieval into agent prompts, human-authored notes, merged-PR write-back | `models/memory.py`, `services/embedding_service.py`, `services/memory_service.py`, `MemoryPanel` |
| Hours to first run — no starting point | 14 first-party skills, 6 agent templates, 3 pod templates; one-click install that materialises a runnable pipeline | `data/builtin_templates.py`, `routers/catalog.py` |
| No network effect | Marketplace: publish, install counts, ratings (installers only), verified first-party listings, revenue-share field | `models/catalog.py`, `MarketplacePage` |
| GitHub + Jira only — TAM limited | GitLab and Linear connectors behind the same interfaces; GitLab merge/promote paths in the DevOps agent | `services/gitlab_service.py`, `services/linear_service.py`, `agents/devops_agent.py` |
| Not scriptable — no CI or ChatOps path | Public API v1 with scoped, hashed API keys (`runs:approve` deliberately separate from `runs:write`) | `routers/public_api.py`, `DeveloperPage` |
| Enterprise procurement questions unanswerable | Compliance posture self-assessment, evidence CSV export, retention enforcement job, self-hosted mode flag | `routers/governance.py`, `tasks/memory_tasks.py`, `CompliancePage` |
| No production deployment path | Backend + frontend Dockerfiles, nginx config, full compose profile, GitHub Actions CI | `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`, `.github/workflows/ci.yml` |

---

## Verification performed

| Check | Result |
|---|---|
| `python -m compileall` across the backend | Clean |
| FastAPI app imports with all routers wired | **97 API paths / 128 operations** registered |
| `pytest tests/ -q` | **53 passed** |
| `npm run build` (tsc + vite) | Clean — 2,874 modules, ~584 kB gzipped |
| `.env.example` ↔ `config.py` field parity | Exact match, verified by diff |
| Template library integrity | Every agent→skill and pod→agent reference resolves (asserted in tests) |

Pre-existing TypeScript errors in 13 untouched files (React 19's removed global `JSX` namespace, form-payload union mismatches, unused imports) blocked the build; they were fixed, since a repo that does not compile is not a deliverable.

**Not verified, and cannot be from here:** no live Postgres run of the new migration, no real Stripe/Slack/SMTP round trip, no agent run against a real repository. Those need credentials and a deployed environment.

---

## Architectural decisions worth knowing

**Embeddings degrade rather than fail.** With no embedding key, `embedding_service` falls back to a deterministic hashed embedder. Retrieval is weaker but the feature works offline, in CI, and in air-gapped installs — memory is never a hard dependency on an external vendor.

**Vectors are JSONB, not pgvector.** Stock Postgres 15 and every managed provider can run this. Cosine similarity is computed in Python inside `memory_service.retrieve()`, which is the single place to swap in pgvector when a customer's corpus outgrows it.

**Money is integers everywhere.** `cost_millicents` and `price_cents` — no floats in the billing path, so no drift across millions of usage rows.

**Stripe is optional.** Unset `STRIPE_SECRET_KEY` and plan changes apply directly. Self-hosted enterprise installs bill by invoice and should never be blocked by a payment processor.

**Policies fail *open* by default and *closed* by configuration.** The default policy is one approver and no reviewer gate: governance a team didn't ask for that blocks their first run is how a pilot dies. Tightening is an explicit act.

**A blocked deploy returns to the gate, it does not fail the run.** A policy violation leaves the run in `awaiting_approval` so the missing approval can still be obtained — failing it would destroy the work and teach people to route around the gate.

**Review never fails a run on its own.** The Reviewer agent produces findings and a score; only a *policy* can turn those into a block. Advisory and enforcement stay separate.

---

## Known limitations (stated rather than hidden)

1. **No live deployment or users.** Everything above is engineering; the design-partner program is the remaining gate on the business case.
2. **Marketplace payments are modelled, not processed.** `price_cents` and `revenue_share_pct` exist and paid listings can be published, but no creator payout flow is implemented — free listings work end to end.
3. **Memory indexing caps at 400 files by default.** Fine for a service, thin for a monorepo; the cap is a parameter, but incremental re-indexing on diff is not built.
4. **The reviewer reads the PR diff, not the whole repository.** Cross-file architectural review is out of reach without the memory layer feeding it more context.
5. **Sprint-planner estimation and bi-directional Jira/Linear writeback** (Horizon 4 in the strategy doc) are not built — tickets sync in, status does not sync back.
6. **The MCP server** for exposing runs/approvals as tools to other orchestrators is designed in the research doc but not implemented.
7. **SSO (SAML/OIDC) and SCIM** are listed as enterprise plan features; role-based access exists, but the identity-provider integration does not.

---

## Running it

```bash
# Infrastructure
docker compose up -d

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set ANTHROPIC_API_KEY at minimum
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Worker (agent runs) + beat (nightly retention prune)
celery -A celery_app worker --loglevel=info
celery -A celery_app beat  --loglevel=info

# Frontend
cd frontend && npm install && cp .env.example .env && npm run dev

# Everything in containers instead
docker compose --profile app up -d --build
```

First login → **Marketplace** → install *Standard SDLC Pod*. That creates the five agents and their skills, and gives you a runnable pipeline without writing a line of markdown.

---

## Suggested next moves

1. **Deploy it.** Every remaining risk in the business plan is a go-to-market risk, not an engineering one.
2. **Onboard three design partners** on the free tier with BYO keys — zero COGS, real usage data.
3. **Instrument the three numbers** the plan commits to (weekly active orgs, runs/org/week, ticket→merged) from real runs, not synthetic ones.
4. **Ship the MCP server** next. It is small, and it positions ADLC as the execution engine *behind* Atlassian's and GitHub's agent surfaces rather than a competitor to them.
