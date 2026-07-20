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
| UI redesign | ✅ Done | Full onto.dev design system applied across entire app (all pages, layout, auth) |

---

## What Hasn't Been Built Yet (potential Phase 11+)

- Docker production build (Dockerfiles exist in blueprint but not created yet)
- GitHub Actions CI/CD workflow
- Nginx config files
- Email notifications on approval needed / run failed
- GitHub OAuth login button on auth pages (only email/password exists)
- Multi-env deploy loop in DevOps agent (dev → QA → prod progression)
- Tests (Pytest for backend, Vitest for frontend)
- MinIO skill file storage (skills save `md_content` direct to DB, not MinIO currently)

---

## Common Gotchas

1. **Windows Celery**: Use `--pool=solo` on Windows — gevent pool crashes on Windows
2. **File not read error**: Always `Read` a file before `Edit` or `Write` — the tool enforces this
3. **shadcn colors**: All shadcn components use CSS vars (`bg-background`, `text-foreground`, etc.) — never use hardcoded Tailwind colors like `bg-white` or `text-gray-500` in new code
4. **Auth in App.tsx**: `RequireAuth` wraps all dashboard routes; `RedirectIfAuthed` wraps `/login` and `/register`
5. **Landing page is public**: `/` route renders `LandingPage` with no auth check — no "Open Dashboard" button
6. **API base URL**: Frontend uses `VITE_API_URL` — no `/api` prefix in route definitions (Nginx strips it in prod)
7. **Encryption**: All OAuth tokens must be Fernet-encrypted before DB insert — use `services/encryption.py`
8. **Two Celery tasks**: Never block a worker at the approval gate — `task_run_until_approval` stops, `task_resume_after_approval` continues
9. **onto-label class**: Use for ALL section eyebrow labels — defined in `index.css`, it's `text-[0.65rem] font-semibold tracking-[0.12em] uppercase`
10. **Orange accent `#E8632A`**: Only accent color in the design — use for pending states, CTA highlights, brand moments
