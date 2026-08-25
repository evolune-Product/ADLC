# Agentic SDLC — Claude Code Context

> Read this file at the start of every session. All phases 1–10 are complete. Jump straight into the task.

---

## What This Project Is

An AI-powered Software Development Lifecycle orchestration platform. A user connects GitHub + Jira, defines skill markdown files, builds AI agents from skills, groups agents into pods, onboards a project, then runs tickets through the pod. The platform autonomously: plans sprints → writes code → opens PRs → runs QA → waits for human approval → deploys. Every production deploy requires explicit human approval.

---

## Monorepo Layout

```
E:\Evolune_Products\SDLC\
├── CLAUDE.md                        ← you are here
├── AGENTIC_SDLC_BLUEPRINT.md        ← full original spec (phases, DB schema, API list)
├── docker-compose.yml
├── backend/
│   ├── .env                         ← secrets (DATABASE_URL, ANTHROPIC_API_KEY, etc.)
│   ├── requirements.txt
│   ├── celery_app.py                ← Celery instance
│   ├── socket_app.py                ← python-socketio AsyncServer (sio)
│   ├── app/
│   │   ├── main.py                  ← FastAPI app + socket.io ASGI wrap
│   │   ├── config.py                ← pydantic-settings Settings class
│   │   ├── database.py              ← SQLAlchemy engine, SessionLocal, Base
│   │   ├── models/                  ← SQLAlchemy ORM (one file per table)
│   │   ├── schemas/                 ← Pydantic v2 request/response schemas
│   │   ├── routers/                 ← FastAPI route handlers
│   │   ├── agents/                  ← LangGraph agent nodes
│   │   ├── services/                ← GitHub, Jira, MinIO, encryption, notifications
│   │   ├── tasks/                   ← Celery tasks (run_tasks.py)
│   │   └── middleware/              ← AuditMiddleware, auth_middleware
│   └── migrations/                  ← Alembic (single migration: b48d141e700e)
└── frontend/
    ├── index.html                   ← title: "Agentic SDLC — AI-Powered Development"
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── src/
    │   ├── App.tsx                  ← all routes defined here
    │   ├── index.css                ← CSS vars (onto.dev palette) + animation utilities
    │   ├── main.tsx
    │   ├── layouts/
    │   │   ├── DashboardLayout.tsx  ← sidebar + topbar shell for all /dashboard routes
    │   │   └── AuthLayout.tsx       ← minimal header/footer for /login, /register
    │   ├── pages/
    │   │   ├── landing/LandingPage.tsx
    │   │   ├── auth/{Login,Register}Page.tsx
    │   │   ├── dashboard/DashboardPage.tsx
    │   │   ├── connections/ConnectionsPage.tsx
    │   │   ├── skills/{Skills,NewSkill,SkillDetail}Page.tsx
    │   │   ├── agents/{Agents,NewAgent,AgentDetail}Page.tsx
    │   │   ├── pods/{Pods,NewPod,PodDetail}Page.tsx
    │   │   ├── projects/{Projects,NewProject,ProjectDetail,TicketDetail}Page.tsx
    │   │   ├── runs/{Runs,RunDetail}Page.tsx
    │   │   ├── audit/AuditPage.tsx
    │   │   └── settings/SettingsPage.tsx
    │   ├── components/
    │   │   ├── ui/                  ← shadcn/ui (button, card, input, label, badge, dialog, skeleton)
    │   │   ├── ErrorBoundary.tsx    ← React class error boundary
    │   │   ├── agents/AgentWizard.tsx
    │   │   ├── connections/{AddConnectionModal,ConnectionCard,ConnectionStatusBadge}.tsx
    │   │   ├── pods/PodWizard.tsx
    │   │   ├── projects/ProjectWizard.tsx
    │   │   ├── runs/PrDiffViewer.tsx
    │   │   └── skills/SkillForm.tsx
    │   ├── hooks/
    │   │   ├── useAgents.ts / useAudit.ts / useConnections.ts / useDashboard.ts
    │   │   ├── usePods.ts / useProjects.ts / useRuns.ts / useSettings.ts
    │   │   ├── useSkills.ts / useTickets.ts
    │   ├── lib/
    │   │   ├── api.ts               ← axios instance (baseURL=VITE_API_URL), interceptors, getApiError()
    │   │   ├── auth.ts              ← isAuthenticated(), token helpers
    │   │   ├── socket.ts            ← socket.io-client setup, connectSocket(), joinRunRoom()
    │   │   ├── skillTemplates.ts    ← MD starter templates per skill category
    │   │   └── utils.ts             ← cn() and other helpers
    │   ├── stores/
    │   │   ├── authStore.ts         ← Zustand: user, login(), logout(), setUser()
    │   │   └── runStore.ts          ← Zustand: liveSteps, setActiveRun(), appendStep()
    │   └── types/index.ts           ← all shared TypeScript interfaces
```

---

## Tech Stack (exact versions in use)

### Frontend
| Thing | What |
|---|---|
| Framework | Vite + React 19 + TypeScript |
| Routing | React Router v7 |
| Styling | Tailwind CSS + shadcn/ui |
| State | Zustand |
| Data fetching | TanStack Query v5 |
| Real-time | socket.io-client |
| Forms | react-hook-form + zod |
| Icons | lucide-react |
| Toasts | sonner |

### Backend
| Thing | What |
|---|---|
| Framework | FastAPI (Python 3.11+) |
| LLM | Anthropic Claude API — `claude-sonnet-4-6` |
| Agent engine | LangGraph |
| DB | PostgreSQL 15 via SQLAlchemy 2.0 + Alembic |
| Queue | Celery + Redis |
| Real-time | python-socketio (`AsyncServer`, `AsyncRedisManager`) |
| Auth | JWT (python-jose) |
| GitHub | PyGithub |
| Token encryption | cryptography (Fernet) |
| Storage | MinIO (minio Python client) |
| Validation | Pydantic v2 |

---

## Design System (onto.dev-inspired — applied everywhere)

The entire app uses a **warm cream + near-black** enterprise palette inspired by buildonto.dev.

### CSS Variables (`frontend/src/index.css`)
```
--background:  36 33% 93%   →  #F5EFE6  warm cream page bg
--foreground:  0 0% 5%      →  #0C0C0C  near-black text
--card:        0 0% 100%    →  #FFFFFF  white cards
--border:      36 22% 84%   →  #E5DDD0  warm border
--muted:       36 20% 89%   →  slightly darker cream
--muted-foreground: 0 0% 42% → #6B6B6B  secondary text
--primary:     0 0% 6%      →  #0F0F0F  black buttons
--radius:      0.375rem     →  6px subtle rounding
--onto-accent: #E8632A      →  orange (used for highlights, active states)
```

### Key UI Patterns
- **Page header**: `<p className="onto-label mb-1">Section Name</p>` + `<h1>` — always use `onto-label` for the eyebrow
- **onto-label class**: `text-[0.65rem] font-semibold tracking-[0.12em] uppercase text-[#8a8378]`
- **Section dividers on landing**: `01 — SECTION NAME` style labels
- **Primary button**: `bg-foreground text-background hover:opacity-85` — never use `bg-indigo-*`
- **Cards**: `bg-card rounded-lg border border-border` — white card on cream background
- **Status dots**: Small colored `w-1.5 h-1.5 rounded-full` dot + text, not pill badges in main app
- **Orange accent**: `text-[#E8632A]` or `bg-[#E8632A]` for pending approvals, highlights, CTA
- **Tables**: `bg-card border border-border rounded-lg overflow-hidden`, `onto-label` for `<th>`
- **Sidebar active state**: `bg-foreground text-background` (black bg, white text)
- **No indigo/blue/purple anywhere** — the design uses black + orange only

### Dashboard Sidebar Groups
```
(ungrouped)  Dashboard
Build        Connections · Skills · Agents · Pods
Work         Projects · Runs
Observe      Audit Log · Settings
```

---

## Route Map (`frontend/src/App.tsx`)

```
/                    → LandingPage (public, always — no auth redirect)
/pricing             → PricingPage (public — plans, comparison, FAQ)
/security            → SecurityPage (public — posture, including what is NOT built)
*                    → NotFoundPage (public 404; was a redirect to /dashboard)
/login               → LoginPage   (redirects to /dashboard if already authed)
/register            → RegisterPage
/dashboard           → DashboardPage         ┐
/connections         → ConnectionsPage       │
/skills              → SkillsPage            │
/skills/new          → NewSkillPage          │
/skills/:id          → SkillDetailPage       │ all require auth
/agents              → AgentsPage            │ via RequireAuth
/agents/new          → NewAgentPage          │ wrapper in App.tsx
/agents/:id          → AgentDetailPage       │
/pods                → PodsPage              │
/pods/new            → NewPodPage            │
/pods/:id            → PodDetailPage         │
/projects            → ProjectsPage          │
/projects/new        → NewProjectPage        │
/projects/:id        → ProjectDetailPage     │
/projects/:id/tickets/:ticketId → TicketDetailPage
/runs                → RunsPage              │
/runs/:runId         → RunDetailPage         │
/audit               → AuditPage             │
/settings            → SettingsPage          ┘
```

---

## Backend API Routes

All routes are served from `VITE_API_URL` (default `http://localhost:8000`). No `/api` prefix — Nginx strips it in production.

```
POST   /auth/register              POST   /auth/login
GET    /auth/me

GET    /connections                POST   /connections
GET    /connections/:id            PUT    /connections/:id       DELETE /connections/:id
POST   /connections/:id/test       GET    /connections/:id/repos
GET    /connections/:id/projects

GET    /skills                     POST   /skills
GET    /skills/:id                 PUT    /skills/:id            DELETE /skills/:id

GET    /agents                     POST   /agents
GET    /agents/:id                 PUT    /agents/:id            DELETE /agents/:id
GET    /agents/:id/skills          POST   /agents/:id/skills
DELETE /agents/:id/skills/:skillId

GET    /pods                       POST   /pods
GET    /pods/:id                   PUT    /pods/:id              DELETE /pods/:id
GET    /pods/:id/agents            POST   /pods/:id/agents
PUT    /pods/:id/agents/:agentId   DELETE /pods/:id/agents/:agentId

GET    /projects                   POST   /projects
GET    /projects/:id               PUT    /projects/:id          DELETE /projects/:id
GET    /projects/:id/tickets       POST   /projects/:id/tickets/sync
GET    /projects/:id/tickets/:tid
GET    /projects/:id/runs

GET    /runs                       POST   /runs
GET    /runs/:id                   GET    /runs/:id/steps
POST   /runs/:id/approve           POST   /runs/:id/retry        DELETE /runs/:id/cancel
GET    /runs/:id/diff              ← PR diff via PyGithub

GET    /audit                      GET    /audit/export           ← CSV stream
GET    /dashboard/stats
GET    /settings                   PUT    /settings

── Phase 11 ────────────────────────────────────────────────────────────────
GET    /billing                    GET    /billing/plans
POST   /billing/checkout           POST   /billing/portal          PUT /billing/plan
PUT    /billing/llm-key            DELETE /billing/llm-key          POST /billing/webhook

GET    /notifications              POST   /notifications/read-all
POST   /notifications/:id/read     GET/PUT /notifications/settings
POST   /notifications/test-slack

GET    /analytics/summary          GET    /analytics/timeseries
GET    /analytics/agents           GET    /analytics/export.csv
GET    /deployments                POST   /deployments/:id/rollback
GET    /runs/:id/findings          GET/POST /runs/:id/feedback
GET    /runs/:id/sources           ← external URLs the agents read, and how well

GET/POST   /policies               PUT/DELETE /policies/:id
GET/POST   /apikeys                DELETE /apikeys/:id
GET/POST   /webhooks               DELETE /webhooks/:id
POST   /webhooks/:id/test          GET    /webhooks/:id/deliveries
GET    /compliance/posture         GET    /compliance/evidence.csv

GET    /templates                  GET    /templates/:slug
POST   /templates/:slug/install    DELETE /templates/:id
GET    /marketplace                POST   /marketplace/publish
POST   /marketplace/:id/rate

GET    /projects/:id/memory        POST   /projects/:id/memory/index
POST   /projects/:id/memory/search GET    /projects/:id/memory/chunks
POST   /projects/:id/memory/notes  DELETE /projects/:id/memory

GET    /projects/:id/sprint-plan            ← latest plan, or null
GET    /projects/:id/sprint-plan/backlog    ← unstarted tickets
POST   /projects/:id/sprint-plan            ← generate (capacity_points, write_back)
POST   /projects/:id/sprint-plan/:planId/write-back

── SSO (OIDC, per organisation) ────────────────────────────────────────────
GET    /auth/sso/lookup            GET    /auth/sso/start
GET    /auth/sso/callback
GET/PUT/DELETE /orgs/:id/sso       ← owner only

── MCP (Bearer adlc_live_… , JSON-RPC 2.0) ─────────────────────────────────
POST   /mcp                        ← initialize · tools/list · tools/call · ping

── Public API (Bearer adlc_live_… , scoped) ────────────────────────────────
GET    /v1/whoami                  GET    /v1/projects
GET    /v1/projects/:id/tickets    GET    /v1/runs/:id/diff
GET/POST /v1/runs                  GET    /v1/runs/:id
POST   /v1/runs/:id/approve        GET    /v1/analytics/summary
```

---

## Key Implementation Patterns

### Frontend data fetching
Every resource has a hook in `src/hooks/`. Pattern:
```ts
// useRuns.ts
const KEY = ['runs']
export function useRuns() {
  return useQuery({ queryKey: KEY, queryFn: () => api.get('/runs').then(r => r.data) })
}
export function useApproveRun() {
  return useMutation({
    mutationFn: ({ id, decision, comment }) => api.post(`/runs/${id}/approve`, { decision, comment }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  })
}
```

### API client (`src/lib/api.ts`)
```ts
import api, { getApiError } from '@/lib/api'
// api is an axios instance; baseURL = VITE_API_URL
// Interceptor adds Bearer token from localStorage automatically
// 401 → clears token, redirects to /login
// getApiError(err) → extracts FastAPI detail string or human message
```

### Auth store (`src/stores/authStore.ts`)
```ts
const { user, login, logout, setUser, isAuthenticated } = useAuthStore()
// login(token, user) — stores token in localStorage, sets user in store
// isAuthenticated() in lib/auth.ts checks localStorage token existence
```

### Real-time runs (`src/lib/socket.ts` + `src/stores/runStore.ts`)
```ts
connectSocket()               // call once (AppInit in App.tsx)
joinRunRoom(runId)            // call in RunDetailPage useEffect
// Listen: getSocket().on('run:step:started', handler)
// Events: run:step:started | run:step:log | run:step:completed | run:awaiting_approval | run:completed | run:failed
```

### Backend router pattern
```python
# Every router uses the same dependency injection pattern:
@router.get("/resource")
def list_resource(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Resource).filter(Resource.user_id == current_user.id).all()
```

### Celery run tasks (two-task approval gate)
```python
# run_tasks.py — NEVER block a Celery worker waiting for human input
task_run_until_approval(run_id)    # runs graph → pauses at approval node → task ends
task_resume_after_approval(run_id) # called by /approve endpoint → resumes graph → deploys
```

### OAuth token encryption
All `access_token` / `refresh_token` in the `connections` table are **Fernet-encrypted** using `ENCRYPTION_KEY` env var. Encrypt in `services/encryption.py` before insert; decrypt only in service layer when making API calls. Never store or return raw tokens.

### Audit middleware (`app/middleware/audit_middleware.py`)
`AuditMiddleware(BaseHTTPMiddleware)` automatically logs all POST/PUT/PATCH/DELETE with 2xx response. Extracts `user_id` from JWT Bearer header. Maps URL path → action string (e.g. `run.approved`). Uses `SessionLocal()` directly (no DI). Swallows all exceptions silently.

---

## Database Models (SQLAlchemy)

```
users           id, email, name, org_name, avatar_url, created_at
connections     id, user_id, name, type, status, access_token(enc), metadata(JSONB), ...
skills          id, user_id, name, category, md_content, version, is_active, ...
agents          id, user_id, name, role, repo_connection_id, llm_model, config(JSONB), ...
agent_skills    agent_id, skill_id, priority  (join table)
pods            id, user_id, name, description, is_active, ...
pod_agents      pod_id, agent_id, execution_order, on_failure, max_retries  (join table)
projects        id, user_id, name, type, repo_connection_id, repo_name, jira_connection_id,
                jira_project_key, pod_id, context_md, deploy_targets(JSONB), ...
tickets         id, project_id, jira_id, title, description, type, priority, status, raw_payload(JSONB)
runs            id, project_id, ticket_id, pod_id, status, branch_name, pr_url, pr_number,
                current_step, retry_count, started_at, completed_at, ...
run_steps       id, run_id, agent_id, agent_role, step_name, status, input, output, log, duration_ms
approvals       id, run_id, reviewer_id, decision, comment, created_at
audit_logs      id, user_id, action, entity_type, entity_id, metadata(JSONB), created_at
```

Run statuses: `queued | running | awaiting_approval | approved | completed | failed`

---

## WebSocket Events

Backend emits from inside agent nodes to room `run:{run_id}`:
```
run:started              { runId, ticketId, podName }
run:step:started         { runId, stepName, agentRole }
run:step:log             { runId, stepName, log }       ← streamed line by line
run:step:completed       { runId, stepName, status, output }
run:step:failed          { runId, stepName, error }
run:awaiting_approval    { runId, prUrl, prNumber }
run:approved             { runId, reviewer, decision }
run:completed            { runId, status }
run:failed               { runId, error, retryCount }
run:awaiting_env_approval{ runId, envIndex, env, branch, totalEnvs }
run:policy:blocked       { runId, policyName, reasons[], approvalsHave, approvalsNeed }
```

---

## Environment Variables

### `backend/.env`
```
DATABASE_URL=postgresql://user:pass@localhost:5432/agentic_sdlc
REDIS_URL=redis://localhost:6379
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=http://localhost:8000/auth/github/callback
JIRA_CLIENT_ID=
JIRA_CLIENT_SECRET=
JIRA_REDIRECT_URI=
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=agentic-sdlc-skills
JWT_SECRET=your-secret-key
JWT_EXPIRY_HOURS=24
FRONTEND_URL=http://localhost:3000
ENCRYPTION_KEY=32-char-fernet-key
```

### `frontend/.env`
```
VITE_API_URL=http://localhost:8000
VITE_SOCKET_URL=http://localhost:8000
VITE_GITHUB_CLIENT_ID=
```

---

## Dev Commands

### Backend
```bash
cd backend

# activate venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac/Linux

# run FastAPI (also serves socket.io)
uvicorn app.main:app --reload --port 8000

# run Celery worker
celery -A celery_app worker --loglevel=info --pool=solo   # Windows (solo pool)
celery -A celery_app worker --loglevel=info               # Mac/Linux

# run migrations
alembic upgrade head

# create new migration after model change
alembic revision --autogenerate -m "description"
```

### Frontend
```bash
cd frontend
npm install        # first time
npm run dev        # starts Vite dev server on http://localhost:5173
npm run build      # production build → dist/
```

### Before you push — run what CI runs

`.github/workflows/ci.yml` does five things the ordinary dev loop does not, and
a green local `pytest` is **not** enough. Ruff caught a broken forward
annotation that every other check ran straight past.

```bash
# Backend (needs a real Postgres — CI uses a service container)
cd backend
ruff check app tests --select E9,F63,F7,F82        # syntax + undefined names
python -c "import app.main"                        # wiring and model errors
alembic upgrade head                               # against a real Postgres
alembic downgrade -1 && alembic upgrade head       # migrations must reverse
pytest tests/ -q

# Frontend
cd frontend && npm run lint && npm run build
```

Two traps worth knowing:

- **A string annotation is not an excuse to import inside the function.** Ruff's
  F821 resolves `-> "Thing | None"` and fails if `Thing` is not importable at
  module scope. Models never import routers, so a top-level import is almost
  always fine — reach for `TYPE_CHECKING` only where there is a genuine cycle.
- **Every migration must downgrade.** CI runs `downgrade -1 && upgrade head`, so
  a `downgrade()` that is a stub fails the build.

### Docker (full stack)
```bash
docker compose up -d           # start all services
docker compose logs -f backend # tail logs
docker compose down            # stop
```

---

## Phases Completed

| Phase | Status | What was built |
|---|---|---|
| 1 — Foundation | ✅ Done | Vite/React setup, FastAPI, PostgreSQL, JWT auth, DashboardLayout, AuthLayout, auth pages |
| 2 — Connections | ✅ Done | GitHub/Jira OAuth, connections CRUD, connection test, repo/project fetch |
| 3 — Skills | ✅ Done | Skills CRUD, MD editor, category templates, split preview |
| 4 — Agents | ✅ Done | Agents CRUD, skill bindings, 3-step wizard |
| 5 — Pods | ✅ Done | Pods CRUD, agent builder, execution order, topology config |
| 6 — Projects | ✅ Done | Projects CRUD, 4-step onboarding wizard, Jira ticket sync, ticket detail |
| 7 — Orchestration | ✅ Done | LangGraph graph, all 4 agent nodes, Celery tasks, socket.io, approval gate |
| 8 — Runs UI | ✅ Done | RunsPage, RunDetailPage (step trace + live socket), PrDiffViewer, approval UI |
| 9 — Dashboard + Audit | ✅ Done | Dashboard stats API, AuditMiddleware, AuditPage (filter + CSV export), SettingsPage |
| 10 — Polish | ✅ Done | ErrorBoundary, Skeleton, getApiError, responsive sidebar, form validation |
| Landing page | ✅ Done | onto.dev-style landing: animated terminal, section dividers, before/after, features, CTA |
| Marketing surface | ✅ Done | Rebuilt as a WebGL landing page + `/pricing`. See "Marketing surface" below. |
| UI redesign | ✅ Done | Full onto.dev design system applied across entire app (all pages, layout, auth) |

---

## Phase 11 — Commercial, Governance & Intelligence Layer (✅ Done)

Built to close the gaps in `documents/MARKET_AND_COMPETITIVE_RESEARCH_2026.md`.
Full write-up: `documents/IMPLEMENTATION_REPORT.md`.

### New backend modules
```
models/     billing.py (Subscription, UsageRecord) · notification.py · governance.py
            (ApprovalPolicy, ApiKey, Webhook, WebhookDelivery) · catalog.py (Template,
            MarketplaceListing, MarketplaceInstall) · memory.py (MemoryChunk, MemoryIndex)
            insight.py (ReviewFinding, RunFeedback, Deployment)
services/   llm_service (multi-provider + costing) · metering_service (plans, quota)
            policy_service (deploy gate) · notifier · email_service · slack_service
            webhook_service (HMAC) · embedding_service · memory_service
            stripe_service · analytics_service · gitlab_service · linear_service
routers/    billing · notifications · insights · governance · catalog · memory · public_api
agents/     review_agent.py  ← the 5th agent; scores the PR, posts findings
tasks/      memory_tasks.py  (repo indexing + nightly retention prune)
data/       builtin_templates.py (14 skills, 6 agents, 3 pods)
migrations/ d7e8f9a0b1c2_phase11_commercial_layer.py (16 tables)
```

### New frontend
```
pages/      billing/BillingPage · analytics/AnalyticsPage · marketplace/MarketplacePage
            governance/{Policies,Developer,Compliance}Page · notifications/NotificationsPage
components/ notifications/NotificationBell · runs/{ReviewFindings,FeedbackWidget}
            projects/MemoryPanel
hooks/      usePlatform.ts   ← all Phase 11 hooks live here (shared invalidation graph)
types/      platform.ts
```

### Sidebar (updated)
```
(ungrouped)  Dashboard
Build        Connections · Skills · Agents · Pods · Marketplace
Work         Projects · Runs
Observe      Insights · Audit Log · Compliance
Govern       Policies · Developer · Billing · Settings
```
Plus a notification bell in the topbar. **Phase 12** adds `Workspace` directly
under `Dashboard`, above every group — the conversation is where a team starts
its day, and burying it under "Build" is how a chat surface goes unused and the
WhatsApp group survives.

### Run pipeline (updated)
`sprint → dev → qa → review → [human approval + policy gate] → merge → multi-env deploy`

Quota is checked **before** work starts; a per-run budget cap aborts runaway runs;
a policy violation returns the run to `awaiting_approval` rather than failing it.

---

## Theming (`light` / `dark` / `system`)

One preference for the whole product, honoured on both surfaces. Default is
`system` and it follows the OS live.

```
index.html                            ← inline boot script: reads localStorage
                                        'adlc-theme', stamps <html> before first
                                        paint. MUST stay inline and in <head>.
src/lib/theme.ts                      ← types, storage key, applyTheme,
                                        ThemeContext, useTheme
src/components/ThemeProvider.tsx      ← the provider (mounted in main.tsx,
                                        OUTSIDE the router)
src/components/ThemeToggle.tsx        ← ThemeToggle (cycling icon button) and
                                        ThemeChoices (segmented, for Settings)
```

`applyTheme` writes three things to `<html>`, and all three are load-bearing:
`data-theme` (what `mk-*` tokens key off), the `.dark` class (what Tailwind's
`darkMode: ['class']` keys off), and `style.colorScheme` (what the browser keys
off, for form controls and scrollbars).

Where the toggle lives: marketing nav (desktop + mobile), auth footer, dashboard
topbar, and Settings → Appearance.

## Source Reading (the AgentRead engine, ported)

Tickets link out — a Notion spec, an RFC, a vendor's API docs. The Planner used
to see a bare URL string. It now reads them.

```
backend/app/services/reader_service.py     ← fetch → extract → Markdown → score
backend/app/agents/_common.py::read_sources← per-agent helper; writes SourceRead rows
backend/app/models/insight.py::SourceRead  ← one row per URL, success or failure
migrations/versions/e3f4a5b6c7d8_source_reads.py
frontend/src/components/runs/SourceReads.tsx
```

- **`reader_service` is a port of `~/Desktop/agentread-main/src/lib/engine/read.ts`.**
  Same extraction pipeline (Readability → Markdown), same six ReadScore
  deductions with the same weights (15/10/20/15/8/7/25), same risk thresholds
  (≥75 low, ≥55 medium). That file is the source of truth; `TestSourceReaderScoring`
  in `tests/test_platform_units.py` pins the constants so a drift fails a test
  rather than a customer's run. Measured ~91% token reduction on real docs pages.
- **The SSRF guard is not optional and has no equivalent upstream.** AgentRead is
  a public tool where the user fetching a URL is the user who typed it. This is
  an authenticated backend inside a perimeter that can reach Postgres, Redis and
  MinIO. `_assert_public_url` rejects private/loopback/link-local/reserved
  addresses **by resolved IP**, and redirects are followed one hop at a time so
  the guard runs on every destination. Never swap that for
  `follow_redirects=True`.
- **A bad read is never fatal.** A dead link costs the plan one source and
  leaves a `SourceRead` row saying why. The score is advisory in exactly the way
  `ReviewFinding` is — only an `ApprovalPolicy` can block a deploy.
- **The score travels into the prompt.** A page that read badly is handed to the
  model with a caveat telling it to flag the gap rather than invent the detail.

## Marketing Surface (`/`, `/pricing`, `/security`)

A public, WebGL-driven marketing site, deliberately separate from the product UI.

```
src/styles/marketing.css              ← "foundry" theme, all tokens under
                                        [data-surface="marketing"], classes `mk-*`;
                                        light variant under [data-theme="light"]
src/components/Seo.tsx                ← per-route title/description/canonical/OG
                                        + page-level JSON-LD, restores on unmount
public/robots.txt · public/sitemap.xml · public/og.png
scripts/og.mjs · scripts/og-card.html ← regenerate the social card
src/components/marketing/
  content.ts                          ← ALL copy, pricing and cited figures
  hooks.ts                            ← useMarketingSurface, useReducedMotion,
                                        usePointer, useScrollProgress, useInView
  Reveal.tsx                          ← Reveal / SplitHeading / DrawRule
  Chrome.tsx                          ← Atmosphere, AdlcMark, nav, footer
  ui.tsx                              ← Eyebrow, Readout, MkButton, SectionHead
  scene/
    pipelineTimeline.ts               ← the model: phases, layout, extent. NO three
    HeroStage.tsx                     ← band + projected DOM labels + compact view
    PipelineCanvas.tsx                ← capability gate + lazy boot + fallback
    PipelineScene.tsx                 ← Canvas, fog, bloom/vignette (lazy chunk)
    DeliveryLine.tsx                  ← the run drawn as a git graph
    GridField.tsx · Rig.tsx · shaders.ts · palette.ts
    StaticPipeline.tsx                ← SVG fallback (reduced motion / no WebGL)
  sections/                           ← Hero, Problem, HowItWorks, TheGate,
                                        Platform, Positioning, Pricing, Trust,
                                        Faq, Interstitial, ClosingCta
```

Rules that matter:

1. **`content.ts` is the only place copy and numbers live.** A figure must be counted
   from this repo, taken from `documents/BUSINESS_PLAN_2026.md`, or attributed to a
   named source rendered next to it. No invented metrics, no customer counts.
2. **The scene is the state machine, not decoration.** `DeliveryLine` draws the run as
   a **git graph**: `main` runs left to right, a feature branch is cut from it and
   gathers four agent commits, the approval gate stands at the merge point and HEAD
   *stops* there, and only after release does the change promote through dev → qa →
   prod. The hero's status readout is driven by the same phase events, so the words and
   the picture can never disagree. An earlier version used an orbital ring; it read as a
   solar system whatever the labels said, and could not show a merge or a promotion.
3. **`TheGate` section is a faithful port of `policy_service`** — same severity ranks,
   same `100 − weighted penalty` review score, same reason strings. If the server's
   logic changes, change it there too or the page starts lying.
4. **three.js is a lazy chunk** (~256 kB gz) that only loads after `requestIdleCallback`,
   only on a capable device with WebGL and no reduced-motion preference, and **never
   below 860px** — phones get `CompactStage`, a DOM timeline driven by the same
   schedule. It stops rendering the moment the stage scrolls out of view.
6. **`pipelineTimeline.ts` must never import three.** It is the shared model: the WebGL
   scene and the compact mobile stage are two views of it, and `hooks.ts` imports it. One
   three import there would put the whole renderer in the main bundle for every visitor.
7. **Every node on the stage is named.** Labels are DOM chips whose positions are
   projected from world space each frame and written straight to `transform` — never
   through React state. Anonymous dots are pretty; a pipeline whose stages you cannot
   name is not doing its job.
5. **Fonts are bundled** (`@fontsource-variable/*`), not fetched from a CDN — this
   platform is meant to run air-gapped.
8. **The light theme is a redesign, not an inversion.** Every colour role is
   re-solved against the cream ground for AA contrast (`--mk-ember` stays the
   brand value for *fills*; `--mk-ember-lit` is the legible value type uses, and
   it is *darker* in light and *lighter* in dark). Three things are switched off
   in light because they are all "add light to a dark thing" and only produce
   grey on cream: **bloom**, **additive blending**, and **the ground grid** —
   the grid's horizon accumulates alpha on a transparent canvas and paints
   brighter than the page. Tone mapping is off in light too, so the fog colour
   composites exactly against the CSS ground.
9. **`SECURITY_POSTURE` lists what is *not* built alongside what is.** No SOC 2,
   no SAML, no SCIM, no pen test. When one of those ships, **move** the row into
   a built group — as OIDC SSO was — do not quietly delete it.
10. **`POSITIONING` compares design intent, never quality.** It names Copilot,
   Cursor, Claude Code, Devin and Factory. No benchmark is implied and the
   disclaimer under the table says so. Do not add a row that claims ADLC is
   faster or better at anything measurable.

## Enterprise Identity (OIDC SSO)

Per-organisation OpenID Connect. Authorization code + PKCE, ID token verified
against the IdP's JWKS, nonce checked, domain re-checked on the way back.

```
backend/app/services/sso_service.py      ← discovery, PKCE, JWKS verification
backend/app/models/organization.py       ← SsoConnection (one per org)
backend/app/routers/auth.py              ← /auth/sso/{lookup,start,callback}
backend/app/routers/organizations.py     ← owner-only CRUD
frontend/src/components/org/SsoPanel.tsx
frontend/src/pages/auth/SsoCallbackPage.tsx
migrations/versions/f4a5b6c7d8e9_sso_connections.py
```

- **OIDC only, on purpose.** Every usable SAML library links against
  `libxmlsec1`, a native build dependency, and this platform is meant to install
  from a compose file inside an air-gapped perimeter. OIDC reaches Okta, Entra
  ID, Google Workspace, Auth0, Keycloak and PingFederate over plain HTTPS.
  SAML-only IdPs are a real gap and are **named as one** on `/security`.
- **`state` is a signed JWT, not a session row** — carries the connection id,
  nonce and PKCE verifier, expires in 10 minutes. No Redis, and a callback that
  lands on a different worker still validates.
- **The redirect URI is on the API** (`settings.api_base_url`), never the SPA:
  the code exchange uses the client secret. One URI serves every tenant.
- **A domain can only be claimed by one organisation.** Two orgs claiming
  `acme.com` would make routing a coin toss and land users in the wrong tenant.
- **Enforcement is checked in `login()` before the password**, otherwise it is a
  suggestion rather than a control.
- Owner-only, not admin: an admin who could point the org at an IdP they control
  could sign in as anyone in it.

## MCP Server (`POST /mcp`)

ADLC as tools any agent can call — JSON-RPC 2.0 over Streamable HTTP,
authenticated with the same scoped `adlc_live_…` API keys as the REST API.

Tools: `list_projects` · `list_runs` · `get_run` · `start_run` ·
`list_pending_approvals` · `approve_run` · `read_url`

- **The scope split is the whole design.** `start_run` needs `runs:write`;
  `approve_run` needs `runs:approve`. A key that can start work deliberately
  cannot wave it through — "let the agent do it end to end" has to be a
  decision someone makes when minting the key, not an accident. There is a test
  asserting those two never collapse into one scope.
- **`approve_run`'s description is a guardrail**, and there is a test asserting
  it still says "production" and "audit log". It is the only thing between an
  eager agent and a deploy.
- Tool failures come back as MCP tool errors (`isError: true`) rather than
  JSON-RPC protocol errors, so a model can read the reason and stop instead of
  retrying blindly.
- Lives at the root, not under `/v1`: MCP clients take a bare URL and the
  protocol is versioned by `protocolVersion` in the handshake.

## Ticket Write-back

Tickets synced *in* and nothing ever went back — a ticket could go through
plan, code, QA, review, human approval and a production deploy while sitting in
"To Do" for everyone not watching this dashboard.

```
backend/app/services/writeback_service.py   ← the milestones, provider-agnostic
backend/app/services/jira_service.py        ← add_comment / transition_issue (ADF)
backend/app/services/linear_service.py      ← comment / move_issue (already existed)
backend/app/models/project.py               ← Project.writeback JSONB
frontend/src/components/projects/WritebackPanel.tsx
migrations/versions/a5b6c7d8e9f0_project_writeback.py
```

Two rules, and they are the whole design:

1. **A write-back failure can never affect a run.** It is called from inside the
   Celery task that owns a deploy. Jira being down, a token being revoked, a
   workflow with no matching transition — none of those are reasons to fail a
   deploy that has already been approved. `_emit` is wrapped whole and there is
   a test that feeds it an exploding tracker.
2. **A comment is always attempted; a status move is opt-in.** Moving someone's
   ticket between columns is opinionated and every workflow differs; narrating
   what happened is safe everywhere. `DEFAULT_STATUS_MAP["failed"]` is
   deliberately blank — a failed run is not a ticket state.

Other things worth not breaking:

- **Only the *last* environment closes the ticket.** A ticket that flips to Done
  when dev deploys, then sits there while prod waits at a gate, is worse than no
  write-back at all. `_is_last_environment` guards it.
- **Jira comments are ADF, not strings** — Jira Cloud rejects a plain string
  body. `_adf()` builds paragraphs and marks bare URLs as links so they are
  clickable rather than text someone has to copy.
- **Jira has no "set status"** — you find the transition that leads to the
  status you want, and which transitions exist depends on where the issue is
  right now. That is why it is looked up per issue rather than cached.
- Off by default. `Project.writeback` defaults to `{}`, which reads as disabled.

## AI Sprint Planner

One metered LLM call turns a project's untouched backlog into story-point
estimates, a dependency graph, and a capacity-bound sprint selection —
per `documents/PRODUCT_STRATEGY.md` Horizon 4 §5.14. None of the
execution-layer competitors (Devin, Factory, GitHub Agent HQ, OpenHands) plan
a sprint; they only execute a ticket once it's already scheduled.
**Correction, 2026-08-16:** Atlassian's Rovo *does* ship a Sprint Planning
Agent (capacity-based allocation + backlog dependency-conflict detection) —
see `documents/RESEARCH_TRIAGE_2026-08.md`. The surviving differentiation is
narrower than first claimed: Rovo is Jira-only and stops at the backlog; this
feeds the same estimate into the governed pipeline (policy gate, cost
attribution, audit trail) across Jira *and* Linear.

```
backend/app/models/sprint.py                  ← SprintPlan, TicketEstimate
backend/app/services/sprint_planner_service.py← the tool-call, the scoring
backend/app/routers/sprint.py                 ← /projects/:id/sprint-plan
migrations/versions/b2c3d4e5f6a7_sprint_plans.py
frontend/src/components/projects/SprintPlanPanel.tsx  ← "Sprint" tab on ProjectDetailPage
```

- **"Backlog" means tickets with zero runs ever started.** A ticket already in
  flight has an opinion (a run, maybe a PR) that estimation shouldn't
  second-guess; re-planning one that failed is a human call, not an automatic
  one. Capped at 60 tickets per planning call — a bigger backlog needs triage
  before it needs a bigger prompt.
- **Dependencies can only point at tickets the model was actually shown** —
  the tool schema returns `depends_on` as *other backlog tickets' jira_ids*,
  which keeps the graph inside the plan instead of inventing cross-project
  references. `resolve_estimate` drops any `jira_id` the model wasn't handed
  rather than guessing what it meant.
- **`blocked` beats `at_risk`.** A sprint at 40% capacity whose first ticket
  can't start because its dependency didn't make the cut is not "under
  budget," it cannot proceed as planned — `plan_health` checks `any_blocked`
  before the capacity math. Pinned in `tests/test_platform_units.py::TestSprintPlanHealth`
  and `TestSprintPlannerResolution` the same way `TestReviewScore` pins policy
  scoring — a drift here should fail a test, not a customer's sprint.
- **Same metering path as every agent call** — `llm_service.complete()` +
  `metering_service.record_llm_call(..., run_id=None, ...)`, BYO-key aware,
  quota-checked before the call via `metering_service.check_quota()`. It is
  billed like a run's LLM spend, not a side channel that dodges cost
  attribution.
- **Write-back reuses the Jira/Linear write-back convention, not the
  run-scoped `writeback_service`** (that module's `_target()` requires a
  `Run`; sprint planning has none). `sprint_planner_service.write_back_estimates()`
  is the project-level sibling: same opt-in gate (`project.writeback.enabled`),
  same "a tracker failure can never raise" rule, posts one comment per
  estimated ticket. Off by default — the endpoint takes `write_back: bool` on
  the plan request, or a plan can be written back separately after review.
- **A plan is a snapshot, not a live document.** Re-planning creates a new
  `SprintPlan` row rather than mutating the last one, so a team can see how
  the plan changed and still show a stakeholder last week's version.

## VS Code Extension (`vscode-extension/`)

Chosen over marketplace creator payouts as the next Phase-12 item, per
`documents/RESEARCH_TRIAGE_2026-08.md`: a paid marketplace needs both buyers
and sellers, and with zero live users there is no buyer side yet for a
creator to sell into. An IDE extension is distribution into where developers
already are and can generate real usage before either side of a marketplace
exists.

```
vscode-extension/
  src/api.ts            ← thin client for the public API (/v1/*) — nine
                           endpoints, hand-written on purpose, not generated
  src/extension.ts       ← activation, commands, status bar, polling
  src/runsProvider.ts     ← one TreeDataProvider class backs both sidebar
                            views (Awaiting Approval / Recent Runs)
  src/diffPanel.ts        ← webview rendering PR patches
```

- **Talks to the same `/v1` public API as CI and ChatOps** — no
  extension-only backend path. Two endpoints were added to
  `routers/public_api.py` to support it: `GET /v1/projects/:id/tickets`
  (backs "Assign Ticket to AI") and `GET /v1/runs/:id/diff` (backs the diff
  webview). The diff logic itself was extracted from `routers/runs.py` into
  `services/pr_diff_service.py` so the internal web-app route and the public
  API route call the same function instead of maintaining two copies of a
  PyGithub call.
- **Scopes are enforced exactly as they are everywhere else** — a
  `runs:write`-only key can start work through the extension but its Approve
  button will 403, the same separation that exists for CI tokens. The
  extension does not attempt to hide or route around this client-side.
- **The API key lives in VS Code's `SecretStorage`**, never in `settings.json`.
- No test suite yet (see "Still isn't built" below) — `tsc`'s strict-mode
  type-check is the safety net for now; the client is a thin enough wrapper
  that most real bugs would be in the backend routes it calls, which *are*
  covered by `tests/test_platform_units.py`.

## Reviewer Suggestion

A named Rovo Dev capability ("suggest the right peer reviewer based on past
commit history") this platform didn't have: every PR the Dev agent opened
went out with zero reviewers requested. `services/reviewer_suggestion_service.py`
closes that gap for GitHub — after `_apply_github` opens the PR, it walks the
commit history of each changed file (`repo.get_commits(path=...)`, last 15
commits/file), tallies author logins (once per file, so a big diff to one file
doesn't drown out someone who touches many small files), excludes the PR's
own author, and calls `pr.create_review_request()` with the top 2. The ranking
(`rank()`) is pure and unit-tested (`TestReviewerSuggestion`,
`tests/test_platform_units.py`) with zero GitHub calls; the GitHub-specific
fetch wrapping it is best-effort and swallowed on any exception — a rate
limit or a brand-new repo with no history must never block PR creation, the
same rule the Reviewer agent's PR comment already follows. GitLab MRs use
numeric `reviewer_ids` rather than usernames and aren't wired up yet — MR
creation still succeeds, it just requests no reviewer.

## Phase 12 — Workspace (the collaboration layer)

Every team running this platform already coordinates somewhere else: a WhatsApp
group in India, Slack elsewhere, Teams in the enterprise. That split is where
the audit trail dies — a deploy approved in a WhatsApp thread at 11pm and typed
into the platform an hour later by someone else makes the compliance export a
work of fiction. The whole pitch of this codebase is that the governed path is
the only path; a chat tool the platform cannot see is a parallel ungoverned one.

```
backend/app/models/workspace.py            ← Channel, ChannelMember, Message,
                                              MessageReaction, UserPresence
backend/app/services/workspace_service.py  ← the write path: post_message, mentions,
                                              unread, presence, catch-up summary
backend/app/services/workspace_bridge.py   ← chat ↔ pipeline: run narration,
                                              @agent dispatch, slash commands
backend/app/routers/workspace.py           ← 28 routes under /workspace
migrations/versions/c3d4e5f6a7b8_workspace.py
frontend/src/pages/workspace/WorkspacePage.tsx
frontend/src/components/workspace/{ChannelSidebar,MessageItem,Composer,ThreadPanel}.tsx
frontend/src/hooks/useWorkspace.ts · frontend/src/types/workspace.ts
```

What it does that a Slack integration structurally cannot:

1. **Agents are members, not webhooks.** `ChannelMember` carries either a
   `user_id` or an `agent_id` (a CHECK enforces exactly one), so the member
   list, the mention autocomplete and `@`-resolution treat humans and agents
   identically. `@qa PROJ-214` in a project channel starts a real run —
   attributed to the person who typed it, counted against their quota, subject
   to the same policy gate as the Runs page.
2. **Runs narrate themselves** into the channel that owns the work.
   `narrate_run_event` is called from `run_tasks.py` next to each
   `emit_run_event` so the two cannot drift. The step firehose is deliberately
   *not* narrated — `run:step:log` belongs on the trace page.
3. **Approving from chat is the same gate.** `runs.py::apply_run_decision` was
   extracted so the chat button and the Runs page share one code path. Two
   places that can release a deploy is one too many.

Rules that matter:

- **`post_message` is the only way a message is created.** Counters, unread
  bookkeeping, socket fan-out, notification fan-out and the mention parse have
  to happen together or the sidebar lies about unread counts. Order inside it is
  `persist → counters → socket → notifications`, so an online reader clears the
  unread before the notifier decides whether to email them.
- **One socket publish per message, to `channel:{id}`.** There is deliberately
  no per-recipient badge event: that would be one broker publish per member per
  message (200 publishes for one line in a 200-person channel). The client joins
  every channel it belongs to — `useWorkspaceLive` — and decides locally whether
  an inbound message is a badge or a rendered line. `useChannelSocket` takes an
  `isMember` flag so it does not leave a room the sidebar still needs.
- **Only a mention or a DM may page someone.** Ordinary channel traffic stays
  in-app. `notify_level` (`all`/`mentions`/`none`) and `is_muted` are honoured
  in `_recipients`, not in the notifier, because they are per-channel. Mute
  means "do not interrupt me", not "hide this from me" — a muted channel still
  increments unread, and a direct mention still pierces it.
- **Broadcast channels are the WhatsApp-Channel shape** — admins publish,
  everyone reads. Enforced in `can_post`, never only in the UI.
- **A private channel 404s rather than 403s** for non-members. A 403 confirms
  the channel exists and lets someone enumerate the channel list by probing.
  Search applies the same rule; there is an e2e assertion for it.
- **Messages are soft-deleted.** A hard delete would let someone remove the
  message an approval was granted in, after the fact, from a system whose whole
  value is that the record is trustworthy.
- **Read state is a high-water mark**, not a receipt table — members × messages
  rows to answer one question a single timestamp answers.
- **Search is ILIKE, not tsvector**, for the same reason memory embeddings are
  JSONB: stock Postgres 15 from a compose file, no extensions. Swap point is
  documented in `search()`.
- **`nullslast()` goes after `desc()`**, not before. `desc(col.nullslast())`
  emits `NULLS LAST DESC`, which Postgres rejects outright.
- **The catch-up summary goes through `llm_service.complete()`** like every
  other model call, so it is metered and attributable. It would otherwise be the
  one uncapped cost path in the product.

New WebSocket events (rooms `channel:{id}` and `user:{id}`):
```
message:new · message:updated · message:deleted · typing · workspace:read
```

## Run Concurrency (Devin's "automations queueing")

A cap on concurrent runs per project, plus a bounded queue behind it. Blast
radius is not only *what one run may touch* — it is also *how many runs are
touching at once*. Six agents opening PRs against one repo in parallel is a
merge-conflict generator and a way to burn a month's quota in an afternoon, and
neither is visible in a per-run cost cap.

```
app/models/governance.py        ← ApprovalPolicy.max_concurrent_runs, .max_queue_depth
app/services/policy_service.py  ← check_concurrency(), promote_next(), ConcurrencyDecision
app/routers/runs.py             ← create_and_dispatch_run() — the single creation path
app/tasks/run_tasks.py          ← _drain_queue() on both terminal paths
migrations/versions/d4e5f6a7b8c9_run_concurrency.py
```

- **It is a policy, not a queue setting**, and lives beside the blast-radius
  controls an org already configures. It therefore applies identically whether a
  run was started from the Runs page, from chat, from CI via `/v1/runs`, or by an
  agent over MCP — which is why `create_and_dispatch_run` exists at all. A cap
  only one of four entry points respects is not a cap.
- **`awaiting_approval` does not occupy a slot.** If it did, three un-reviewed
  PRs would deadlock a project's whole pipeline until a human woke up — the exact
  failure a concurrency cap exists to prevent. Pinned by
  `TestConcurrencySlotAccounting`.
- **Three outcomes, not two.** Admitted (dispatch now), queued (held at `queued`,
  started by `promote_next` when a slot frees), or refused with **429** when the
  queue itself is full. An unbounded queue is not backpressure, it is a memory
  leak with a nicer name.
- **Both limits default to 0 = unlimited**, so every pre-existing policy row
  behaves exactly as before. `check_concurrency` tests `policy is None`, not
  truthiness — an explicitly-passed empty policy means "no limits" and must not
  fall through to a DB lookup.
- **`_drain_queue` is swallowed whole.** It runs right after a run reaches a
  terminal state; an exception escaping there would turn a run that just
  *succeeded* into a failure, and the next completion drains the queue anyway.

## Engineering Pulse (Rovo's "AI Pulse")

The cross-run view an engineering manager needs, built on rows the platform
already writes. `analytics_service.pulse()` → `GET /analytics/pulse` →
`frontend/src/pages/analytics/PulsePage.tsx` at `/pulse`.

Deliberately **separate from `/analytics`**. Insights answers "was this worth the
money", a quarterly finance conversation. Pulse answers "where is my pipeline
stuck this week and does the team trust the output", a Monday-morning one. One
page trying to do both serves neither.

Four blocks, in the order a manager reads them:

| Block | What it shows |
|---|---|
| **Flow** | DORA-shaped: deploy frequency, median lead time, change failure rate, throughput trend vs the preceding window |
| **Bottleneck** | Median duration per agent role, **approval wait per reviewer**, and how long the oldest waiting run has sat |
| **Quality** | Reviewer-agent findings by severity and category, per-run rate, trend |
| **Trust** | First-pass approval rate, median human rewrite in LOC, thumbs up/down, top rejection reasons |

- **The bottleneck block is the point.** On most real teams the agents finish in
  minutes and the change then waits hours for a person; no other screen in this
  product makes that visible, and it reframes "the AI is slow" into a number the
  manager can act on.
- **Change failure rate counts deploys, not runs.** A run that failed before it
  ever deployed is a flaky agent; a deploy that broke or was rolled back is a
  production incident. Conflating them makes the metric useless.
- **Empty stays empty.** With no `RunFeedback` rows the trust block renders blank
  and says so. An assumed satisfaction score is worse than an honest gap.

## Model Providers and Plugins (bring your own everything)

Two registries and the credentials that go with them. Both are declarative:
adding a vendor is a dict literal, not code.

```
app/services/llm_providers.py   ← 20 model vendors, all BYO-key
app/services/plugins.py         ← 41 connectors across 9 categories
app/services/plugin_verify.py   ← one real authenticated call per plugin
app/models/integration.py       ← ModelCredential — many keys per workspace
app/routers/integrations.py     ← /providers · /plugins
migrations/versions/e5f6a7b8c9d0_model_credentials.py
frontend/src/pages/settings/ProvidersPage.tsx     → /providers
frontend/src/pages/connections/PluginsPage.tsx    → /plugins
frontend/src/hooks/useIntegrations.ts · types/integrations.ts
```

### The position: this platform does not resell inference

There is no bundled model quota and no markup on tokens. A workspace connects a
vendor it already pays; the tokens are billed by that vendor on the customer's
own contract under their own data-processing terms. That is the answer to the
first question every security review asks, and it keeps inference off this
company's COGS entirely. `/providers` says so on the page, in those words.

A platform-key fallback still exists for single-tenant and self-hosted installs
(`settings.anthropic_api_key`), but it is not the product path and no
customer-facing copy implies otherwise.

### One workspace, many keys

`Subscription.byo_llm_provider` / `byo_llm_key` held exactly **one** key for a
whole workspace, which forces a choice the product should not force — teams run
Claude for the Dev agent and a local Ollama for QA. `ModelCredential` is one row
per provider; `_common.workspace_credential(db, user, org, model)` resolves per
model and falls back to the old single key so no existing workspace breaks.

### Wire formats, not vendors

Twenty providers, four clients. `llm_providers` records a `wire` per provider
and `llm_service` dispatches on that:

| wire | serves |
|---|---|
| `anthropic` | Claude, native SDK |
| `openai` | most of the catalogue — Azure, Groq, DeepSeek, xAI, Together, Fireworks, OpenRouter, Mistral, Perplexity, Cerebras, DeepInfra, Nebius, Cohere, vLLM, LM Studio |
| `google` | Gemini's `:generateContent` |
| `ollama` | local models |

Things that will bite whoever touches this next:

- **`suggested_models` is not a closed set.** Model ids churn faster than any
  hardcoded list survives, so the API accepts any string. An allow-list would
  reject a model the vendor shipped last week — a worse failure than an unknown
  id reaching the provider and coming back with a clear error.
- **The base URL is what makes one client serve fifteen vendors.** It comes from
  the stored credential first (Azure, vLLM, an internal gateway), then the
  catalogue default. `settings.openai_base_url` is now only a last resort.
- **Gemini rejects JSON Schema keys the others ignore** — `additionalProperties`,
  `title`, `default`, `const` and friends produce a 400, not a shrug. The agent
  tool schemas are written once and shared, so `_gemini_schema` filters them on
  the way out rather than maintaining a second copy per vendor.
- **`resolve_credentials` returns a 4-tuple now** (provider, key, is_byo,
  base_url). `is_byo` keys off the provider being chosen, **not** off a secret
  being present — a keyless local Ollama is still the customer's own hardware
  and must not be billed as platform spend.
- **Cost overrides beat the published table.** This repo has published prices
  for a minority of the catalogue. Rather than invent the rest,
  `ModelCredential.price_overrides` lets a workspace enter its own rate, which
  is the truer number for anyone on committed spend anyway.
  `has_published_price()` is what the UI uses to prompt for one instead of
  quietly showing an invented figure as if it were measured.
- **`/providers/credentials/{p}/test` makes a real two-token completion**, not a
  ping to a `/models` list. Several vendors happily list models for a key with
  no inference quota, no billing attached, or the wrong project scope — and the
  failure then surfaces mid-run instead of in the settings page.

### Plugins: depth is declared, not implied

A catalogue of forty logos is worth nothing if thirty-five only store a token.
Every entry declares a `depth`, the API returns it, and the card shows it:

| depth | meaning | count |
|---|---|---|
| `native` | the pipeline drives it — reads issues, opens PRs, comments back | 4 |
| `notify` | receives approvals, failures and deploys | 7 |
| `verified` | credential genuinely checked against the vendor and available to agents; no bespoke pipeline behaviour yet | 30 |

`verified` is not a euphemism for "we did nothing" — `plugin_verify` makes a
real authenticated request to the vendor's own auth endpoint, so a wrong token
fails in the connect form rather than at 3am inside a deploy. There is a test
asserting the `native` set is exactly `{github, gitlab, jira, linear}`, so
growing that list forces a real service module to grow with it.

Rules worth keeping:

- **SSRF is keyed off deployment mode, not blanket-blocked.** Several plugins
  are self-hostable (GitLab, Gitea, Mattermost, SonarQube, Grafana, YouTrack),
  so the customer supplies a host and the server then calls it. In `cloud` mode
  `reader_service._assert_public_url` refuses private, loopback, link-local and
  reserved addresses **by resolved IP** — a tenant admin must not be able to
  make shared infrastructure fetch `169.254.169.254`. In `self_hosted` mode the
  guard is off, because the internal host is the entire point. Redirects are
  never followed on a verification call.
- **`requires_url` is driven by the presence of a URL field, not by the auth
  constant.** Jira and Confluence authenticate with `basic` *and* need a site
  URL; keying off the auth constant let a Jira connect pass validation with no
  URL and then fail deep in the verifier on an un-substituted `{base}`.
- **A failed verification still saves the connection**, with the vendor's reason
  attached and `status="error"`. Someone who pasted a token missing one scope
  should fix the scope and re-verify, not retype the whole form.
- **Webhook URLs are encrypted like tokens.** Anyone holding a Slack incoming
  webhook can post into the channel, so it does not sit in the plaintext
  `workspace_url` column.
- **An omitted key or base URL on an update means "keep the stored one."** The
  UI cannot show a secret back, so it cannot resend one; treating a blank field
  as a deletion would wipe a working key on an unrelated edit. Both were
  genuine bugs caught by the end-to-end script, not hypotheticals.
- **`catalog()` never returns the `verify` recipes.** They are internal, and
  publishing them invites probing vendors through us.

## What Still Isn't Built (Phase 12+)

- SAML SSO and SCIM directory provisioning (OIDC SSO **is** built — see above)
- Marketplace creator payouts (listings support pricing; no payout flow)
- Vitest/a test runner for the VS Code extension, and for the frontend (backend has 186 pytest unit tests)
- Incremental memory re-indexing on diff (currently full re-index, 400-file cap)
- MinIO skill file storage (skills still save `md_content` direct to DB)
- Reviewer suggestion for GitLab merge requests (GitHub only today)
- INR pricing, GST and Razorpay — the billing path is Stripe-only, which blocks
  the India motion entirely. See `documents/MARKET_RESEARCH_2026-08-25.md` §4.2.
- Mobile/PWA push for Workspace. The layout is responsive, but a WhatsApp
  replacement with no push notification on a phone is not one.
- Voice notes in Workspace — the most-used WhatsApp feature not yet replicated.
- Attachment *upload*. `Message.attachments` stores and renders a list, but there
  is no upload endpoint behind it yet; MinIO (`storage_service`) is the obvious home.

---

## Common Gotchas

1. **Windows Celery**: Use `--pool=solo` on Windows — gevent pool crashes on Windows
2. **File not read error**: Always `Read` a file before `Edit` or `Write` — the tool enforces this
3. **shadcn colors**: All shadcn components use CSS vars (`bg-background`, `text-foreground`, etc.) — never use hardcoded Tailwind colors like `bg-white` or `text-gray-500` in new code
4. **Auth in App.tsx**: `RequireAuth` wraps all dashboard routes; `RedirectIfAuthed` wraps `/login` and `/register`
5. **Landing page is public**: `/` and `/pricing` render with no auth check — no "Open Dashboard" button
5b. **Two surfaces, one app**: the product UI is the light cream shadcn theme on `:root`; the marketing pages are a dark theme scoped to `[data-surface="marketing"]` (`src/styles/marketing.css`, all classes prefixed `mk-`), applied by `useMarketingSurface()` on mount and removed on unmount. Never define a `mk-` token on `:root`, and never use a shadcn token inside a marketing component — the two palettes must not meet.
5c. **Auth belongs to marketing**: `AuthLayout` is on the marketing surface and carries `.mk-auth`, which **redefines the shadcn tokens** (`--background`, `--card`, `--border`, …) for that subtree. The login/register markup is unchanged and simply resolves dark; new auth pages inherit it for free.
5d. **The app has a real dark mode now, and it is still not the marketing surface.** `.dark` in `index.css` is the product's dark token set — warm-biased blacks, lifted a step from the hero page's #08070a because tables need more separation between ground, card and border. Do not port the marketing grain/bloom/atmosphere into it. Brand continuity comes from *type*, not atmosphere: `AdlcMark` + the name "ADLC" everywhere, `.app-display` (Archivo) on headings, `.app-metric` (JetBrains Mono, tabular) on every measured number.
5e. **Status tints are remapped, not rewritten.** ~50 uses of Tailwind's `bg-red-50 text-red-700`-style pills across 12 files would be neon on a dark ground. `index.css` remaps exactly the utilities in use under `.dark` to low-alpha washes of the same hue. If you add a new tint class, add it to that list — `grep -ro "bg-[a-z]*-[0-9]*"` finds strays.
6. **API base URL**: Frontend uses `VITE_API_URL` — no `/api` prefix in route definitions (Nginx strips it in prod)
7. **Encryption**: All OAuth tokens must be Fernet-encrypted before DB insert — use `services/encryption.py`
8. **Two Celery tasks**: Never block a worker at the approval gate — `task_run_until_approval` stops, `task_resume_after_approval` continues
9. **onto-label class**: Use for ALL section eyebrow labels — defined in `index.css`, it's `text-[0.65rem] font-semibold tracking-[0.12em] uppercase`
10. **Orange accent `#E8632A`**: Only accent color in the design — use for pending states, CTA highlights, brand moments
11. **Never pass `temperature`/`top_p`/`top_k` to Anthropic** — current Claude models reject them with a 400. `llm_service` only forwards sampling params to OpenAI-shaped providers.
12. **Money is integers**: `cost_millicents` (1 cent = 1000) and `price_cents`. No floats anywhere in the billing path.
13. **Every agent LLM call goes through `llm_service.complete()`** — that is what makes BYO-keys, cost attribution and budget caps work. A direct `anthropic.Anthropic()` call bypasses metering. (`sprint_agent` was doing exactly this until Aug 2026, so the first call of *every* run was unmetered and un-cappable. Use `_common.call_llm`.)
14. **Memory embeddings are JSONB, not pgvector** — stock Postgres 15 works. Swap point is `memory_service.retrieve()`.
15. **Stripe is optional**: with no `STRIPE_SECRET_KEY`, `/billing/checkout` applies the plan directly and returns `simulated: true`.
16. **Review is advisory; policy is enforcement** — `review_agent` never fails a run, only an `ApprovalPolicy` can block a deploy.
