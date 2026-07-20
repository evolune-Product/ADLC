# Agentic SDLC

An AI-powered Software Development Lifecycle orchestration platform. Connect GitHub and Jira, define skill files, build agents, group them into pods, and run tickets autonomously — from sprint planning through code, PR, QA, and deployment. Every production deploy requires explicit human approval.

---

## How It Works

```
Jira Ticket  →  Pod Triggered  →  Planner Agent  →  Coder Agent  →  Reviewer Agent
     →  PR Opened  →  QA Agent  →  Awaiting Human Approval  →  DevOps Agent  →  Deployed
```

Each step is visible in real-time via WebSocket. The platform pauses at every production gate and waits for a human decision before continuing.

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

### Docker (full stack)

```bash
docker compose up -d
```

Starts PostgreSQL, Redis, MinIO, backend, and frontend together.

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

---

## License

Private. All rights reserved.
