# Agentic SDLC

An AI-powered Software Development Lifecycle orchestration platform. Connect GitHub and Jira, define skill files, build agents, group them into pods, and run tickets autonomously — from sprint planning through code, PR, QA, and deployment. Every production deploy requires explicit human approval.

---

## How It Works

```
Ticket  →  Pod  →  Planner  →  Coder  →  QA  →  Reviewer  →  ⏸ Human approval + policy gate
                                                              →  DevOps  →  dev → qa → prod
```

Each step streams live over WebSocket. The platform stops at every production gate and waits
for a human decision — and an approval policy decides whether that decision is even sufficient
(how many approvers, what reviewer score, which paths the agent was allowed to touch).

---

## Tech Stack

### Backend
| | |
|---|---|
| Framework | FastAPI (Python 3.11+) |
| LLM | Anthropic Claude (`claude-sonnet-4-6`) |
| Agent Engine | LangGraph |
| Database | PostgreSQL 15 + SQLAlchemy 2.0 + Alembic |
| Queue | Celery + Redis |
| Real-time | python-socketio |
| Auth | JWT (python-jose) |
| GitHub | PyGithub |
| Token Security | Fernet encryption (cryptography) |
| Storage | MinIO |
| Validation | Pydantic v2 |

### Frontend
| | |
|---|---|
| Framework | Vite + React 19 + TypeScript |
| Routing | React Router v7 |
| Styling | Tailwind CSS + shadcn/ui |
| State | Zustand |
| Data Fetching | TanStack Query v5 |
| Real-time | socket.io-client |
| Forms | react-hook-form + zod |

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── routers/          # API route handlers
│   │   ├── agents/           # LangGraph agent nodes
│   │   ├── services/         # GitHub, Jira, MinIO, encryption
│   │   ├── tasks/            # Celery background tasks
│   │   └── middleware/       # Audit logging, auth
│   ├── celery_app.py
│   ├── socket_app.py
│   └── migrations/           # Alembic migrations
└── frontend/
    └── src/
        ├── pages/            # One folder per route
        ├── components/       # Shared UI components
        ├── hooks/            # TanStack Query hooks
        ├── stores/           # Zustand state
        └── lib/              # API client, socket, auth helpers
```

---

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15
- Redis
- MinIO (or use Docker Compose)

---

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/agentic-sdlc.git
cd agentic-sdlc
```

---

### 2. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create your .env file (copy from example)
cp .env.example .env
# Fill in your values (see Environment Variables section below)

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --port 8000

# In a separate terminal — start Celery worker
celery -A celery_app worker --loglevel=info --pool=solo   # Windows
celery -A celery_app worker --loglevel=info               # Mac/Linux
```

---

### 3. Frontend

```bash
cd frontend

npm install

# Create your .env file
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000

npm run dev
# Runs at http://localhost:5173
```

---

### Docker

```bash
docker compose up -d                        # Postgres, Redis, MinIO only
docker compose --profile app up -d --build  # + backend, worker, beat, frontend
```

The `app` profile runs migrations on boot and serves the frontend through nginx on port 3000.

---

## Environment Variables

### `backend/.env`

```env
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
ENCRYPTION_KEY=          # 32-byte Fernet key
```

### `frontend/.env`

```env
VITE_API_URL=http://localhost:8000
VITE_SOCKET_URL=http://localhost:8000
VITE_GITHUB_CLIENT_ID=
```

---

## Core Concepts

### Skills
Markdown files that define what an agent knows how to do — coding standards, review checklists, deployment steps. Written in plain text, versioned in the platform.

### Agents
An agent has a role (Planner, Coder, Reviewer, DevOps), an LLM model, and a set of skills. Skills are injected into the agent's system prompt at runtime.

### Pods
A pod is an ordered group of agents. When a ticket is run through a pod, each agent executes in sequence. Failure handling and retry policy are configurable per agent slot.

### Runs
A run is one ticket being processed through a pod. It progresses through statuses: `queued → running → awaiting_approval → approved → completed`. The approval gate is mandatory before any deploy step.

### Policies
An approval policy decides whether a run may deploy to a given environment: how many approvers
are required, which roles count, what reviewer score is needed, which severities block, which
paths and branches agents may never touch, and how much a run may cost. Policies scope
org-wide or per project, per environment.

### Memory
Each project can be indexed into embedded chunks so agents stop starting cold. Retrieval feeds
the agent prompt on every run, merged PRs write outcomes back, and humans can add notes the
repo doesn't say out loud.

### Runs are metered
A run is the billing unit. Quota is checked before work starts, every model call is costed and
attributed, and a per-run budget cap stops a runaway ticket rather than letting it invert the
month's margin.

---

## WebSocket Events

The frontend subscribes to a run room and receives live updates:

| Event | Payload |
|---|---|
| `run:started` | `{ runId, ticketId, podName }` |
| `run:step:started` | `{ runId, stepName, agentRole }` |
| `run:step:log` | `{ runId, stepName, log }` |
| `run:step:completed` | `{ runId, stepName, status, output }` |
| `run:awaiting_approval` | `{ runId, prUrl, prNumber }` |
| `run:approved` | `{ runId, reviewer, decision }` |
| `run:completed` | `{ runId, status }` |
| `run:failed` | `{ runId, error, retryCount }` |

---

## Feature Map

| Area | What you get |
|---|---|
| **Orchestration** | Skills → Agents → Pods → Runs, live WebSocket traces, multi-env deploy chain |
| **Governance** | Approval policies, protected paths/branches, N-approver rules, immutable audit log, compliance posture + evidence CSV |
| **Review** | Reviewer agent scores each PR against your own rubric skills and posts structured findings |
| **Commercial** | Plans, metered runs, quota enforcement, Stripe checkout/portal, per-run budget caps |
| **Model agility** | Anthropic / OpenAI / Azure / OpenAI-compatible / Ollama, per-workspace bring-your-own key |
| **Insight** | Cycle time, approval latency, cost per merged run, hours saved, agent scorecards, CSV export |
| **Memory** | Repo indexing, embedding retrieval into agent prompts, human notes, merged-PR write-back |
| **Library** | 14 built-in skills, 6 agent templates, 3 pod templates, publishable marketplace |
| **Integrations** | GitHub, GitLab, Jira, Linear · Slack, email, signed outbound webhooks |
| **Automation** | Public API v1 with scoped API keys — trigger runs from CI, approve from ChatOps |

---

## API Overview

```
POST  /auth/register        POST  /auth/login         GET   /auth/me

GET   /connections          POST  /connections
GET   /skills               POST  /skills
GET   /agents               POST  /agents
GET   /pods                 POST  /pods
GET   /projects             POST  /projects
GET   /projects/:id/tickets POST  /projects/:id/tickets/sync

GET   /runs                 POST  /runs
GET   /runs/:id/steps
POST  /runs/:id/approve
POST  /runs/:id/retry
GET   /runs/:id/diff

GET   /audit                GET   /audit/export
GET   /dashboard/stats
GET   /settings             PUT   /settings

GET   /billing              POST  /billing/checkout   PUT /billing/llm-key
GET   /notifications        GET/PUT /notifications/settings
GET   /analytics/summary    GET   /analytics/agents   GET /analytics/export.csv
GET   /policies             POST  /policies
GET   /apikeys              GET   /webhooks
GET   /compliance/posture   GET   /compliance/evidence.csv
GET   /templates            POST  /templates/:slug/install
GET   /marketplace          POST  /marketplace/publish
GET   /projects/:id/memory  POST  /projects/:id/memory/index
```

### Public API (API-key authenticated)

```bash
curl -X POST https://your-host/v1/runs \
  -H "Authorization: Bearer adlc_live_…" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"<uuid>","ticket_id":"<uuid>"}'
```

Scopes: `runs:read`, `runs:write`, `runs:approve`, `projects:read`, `analytics:read`.
`runs:approve` is separate from `runs:write` on purpose — a CI token that starts work should
not be able to wave its own work through the gate.

---

## Testing

```bash
cd backend && pytest tests/ -q     # 53 unit tests — pricing, policy, signatures, retrieval
cd frontend && npm run build       # tsc + vite
```

---

## Build Status

| Phase | Status |
|---|---|
| Foundation (auth, layout, routing) | Done |
| Connections (GitHub + Jira OAuth) | Done |
| Skills (CRUD, MD editor) | Done |
| Agents (CRUD, skill bindings, wizard) | Done |
| Pods (CRUD, agent ordering) | Done |
| Projects (onboarding wizard, Jira sync) | Done |
| Orchestration (LangGraph, Celery, sockets) | Done |
| Runs UI (live trace, diff viewer, approval) | Done |
| Dashboard + Audit log | Done |
| Polish (error boundaries, skeletons, validation) | Done |
| Organizations, roles, invitations | Done |
| **Billing, quota + metering** | Done |
| **Approval policies + Reviewer agent** | Done |
| **Notifications (in-app, email, Slack, webhooks)** | Done |
| **ROI analytics + agent scorecards** | Done |
| **Codebase memory** | Done |
| **Template library + marketplace** | Done |
| **GitLab + Linear connectors** | Done |
| **Public API + compliance export** | Done |
| **Docker, nginx, CI** | Done |

See `documents/IMPLEMENTATION_REPORT.md` for what is *not* built and why.

---

## License

Private. All rights reserved.
