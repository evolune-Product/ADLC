# Agentic SDLC Platform — Full Development Blueprint

> Hand this file to Claude Code as the complete specification for building the platform.
> Build in the exact order listed in Section 9.

---

## 1. Product Summary

A standalone AI-powered SDLC orchestration platform. A human connects their tools, defines skills (MD files), builds agents from skills, groups agents into pods, onboards a project, then assigns tickets to pods. The platform runs the full loop: Sprint Agent plans → Dev Agent codes → QA Agent tests → human approves → DevOps Agent deploys. Every step is logged. Every production deploy requires human approval.

---

## 2. Tech Stack

### Frontend
```
Framework        Vite + React 18
Language         TypeScript
Routing          React Router v6
Styling          Tailwind CSS + shadcn/ui
State            Zustand
Data fetching    TanStack Query (React Query)
Realtime         Socket.io client
MD Editor        @uiw/react-md-editor
Code Diff        react-diff-viewer-continued
Icons            lucide-react
Forms            react-hook-form + zod
```

### Backend
```
Framework        FastAPI (Python 3.11+)
Agent Engine     LangGraph
LLM              Anthropic Claude API (claude-sonnet-4-6)
Database         PostgreSQL 15
ORM              SQLAlchemy 2.0 + Alembic (migrations)
Cache / Queue    Redis + Celery
Realtime         Socket.io (python-socketio)
Auth             JWT + OAuth2 (GitHub, Jira)
Storage          MinIO (self-hosted S3-compatible)
HTTP Client      httpx
Validation       Pydantic v2
GitHub API       PyGithub
Token Encryption cryptography (Fernet)
File Storage SDK minio (Python client)
```

### Infrastructure (Contabo VPS — fully self-hosted)
```
Server           Contabo VPS (Ubuntu 22.04)
Containerization Docker + Docker Compose
Reverse proxy    Nginx (routes /api → FastAPI, / → Vite/React static)
SSL              Let's Encrypt via Certbot
Frontend serve   Vite build → static files served by Nginx (Docker container)
Backend serve    Gunicorn + Uvicorn workers (FastAPI)
Database         PostgreSQL 15 (Docker container)
Cache / Queue    Redis (Docker container)
File storage     MinIO (self-hosted S3-compatible, Docker container)
Process manager  Docker Compose (all services in one compose file)
CI/CD            GitHub Actions → SSH deploy to Contabo on push to main
```

### Dev Tools
```
Package manager  npm (frontend), pip + requirements.txt (backend)
Linting          ESLint, Prettier (FE), Ruff (BE)
Testing          Vitest + React Testing Library (FE), Pytest (BE)
API docs         FastAPI auto Swagger at /docs
Env management   python-dotenv (.env), Vite env files (.env, .env.production)
```

---

## 3. Repository Structure

```
agentic-sdlc/
├── frontend/                        # Vite + React app
│   ├── index.html
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx                 # app entry point
│   │   ├── App.tsx                  # React Router route definitions
│   │   ├── pages/
│   │   │   ├── auth/
│   │   │   │   ├── LoginPage.tsx
│   │   │   │   └── RegisterPage.tsx
│   │   │   ├── dashboard/
│   │   │   │   └── DashboardPage.tsx
│   │   │   ├── connections/
│   │   │   │   ├── ConnectionsPage.tsx
│   │   │   │   └── ConnectionDetailPage.tsx
│   │   │   ├── skills/
│   │   │   │   ├── SkillsPage.tsx
│   │   │   │   ├── NewSkillPage.tsx
│   │   │   │   └── SkillDetailPage.tsx
│   │   │   ├── agents/
│   │   │   │   ├── AgentsPage.tsx
│   │   │   │   ├── NewAgentPage.tsx
│   │   │   │   └── AgentDetailPage.tsx
│   │   │   ├── pods/
│   │   │   │   ├── PodsPage.tsx
│   │   │   │   ├── NewPodPage.tsx
│   │   │   │   └── PodDetailPage.tsx
│   │   │   ├── projects/
│   │   │   │   ├── ProjectsPage.tsx
│   │   │   │   ├── NewProjectPage.tsx   # onboarding wizard
│   │   │   │   ├── ProjectOverviewPage.tsx
│   │   │   │   ├── ProjectTicketsPage.tsx
│   │   │   │   ├── TicketDetailPage.tsx
│   │   │   │   ├── ProjectRunsPage.tsx
│   │   │   │   └── ProjectSettingsPage.tsx
│   │   │   ├── runs/
│   │   │   │   ├── RunsPage.tsx         # all runs across projects
│   │   │   │   └── RunDetailPage.tsx    # run detail + approval gate
│   │   │   ├── audit/
│   │   │   │   └── AuditPage.tsx
│   │   │   └── settings/
│   │   │       └── SettingsPage.tsx
│   │   ├── layouts/
│   │   │   ├── DashboardLayout.tsx      # sidebar + topbar shell
│   │   │   └── AuthLayout.tsx
│   │   ├── components/
│   │   │   ├── ui/                      # shadcn components
│   │   │   ├── connections/
│   │   │   │   ├── ConnectionCard.tsx
│   │   │   │   ├── AddConnectionModal.tsx
│   │   │   │   └── ConnectionStatusBadge.tsx
│   │   │   ├── skills/
│   │   │   │   ├── SkillCard.tsx
│   │   │   │   └── SkillMDEditor.tsx
│   │   │   ├── agents/
│   │   │   │   ├── AgentCard.tsx
│   │   │   │   ├── SkillBindingSelector.tsx
│   │   │   │   └── AgentConfigForm.tsx
│   │   │   ├── pods/
│   │   │   │   ├── PodCard.tsx
│   │   │   │   ├── AgentGroupBuilder.tsx
│   │   │   │   └── WorkflowTopologyConfig.tsx
│   │   │   ├── projects/
│   │   │   │   ├── ProjectCard.tsx
│   │   │   │   ├── OnboardingWizard.tsx
│   │   │   │   └── TicketList.tsx
│   │   │   ├── runs/
│   │   │   │   ├── RunCard.tsx
│   │   │   │   ├── RunStepTrace.tsx
│   │   │   │   ├── ApprovalGate.tsx
│   │   │   │   └── PRDiffViewer.tsx
│   │   │   └── shared/
│   │   │       ├── StatusBadge.tsx
│   │   │       ├── EmptyState.tsx
│   │   │       ├── LoadingSpinner.tsx
│   │   │       └── ConfirmModal.tsx
│   │   ├── lib/
│   │   │   ├── api.ts                   # axios instance pointing to FastAPI
│   │   │   ├── socket.ts                # socket.io client setup
│   │   │   ├── auth.ts                  # JWT helpers
│   │   │   └── utils.ts
│   │   ├── stores/
│   │   │   ├── authStore.ts
│   │   │   └── runStore.ts              # live run state via socket
│   │   ├── types/
│   │   │   └── index.ts                 # all shared TypeScript types
│   │   └── hooks/
│   │       ├── useConnections.ts
│   │       ├── useSkills.ts
│   │       ├── useAgents.ts
│   │       ├── usePods.ts
│   │       ├── useProjects.ts
│   │       └── useRuns.ts
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── config.py                # settings via pydantic-settings
│   │   ├── database.py              # SQLAlchemy engine + session
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── connection.py
│   │   │   ├── skill.py
│   │   │   ├── agent.py
│   │   │   ├── pod.py
│   │   │   ├── project.py
│   │   │   ├── ticket.py
│   │   │   ├── run.py
│   │   │   └── audit.py
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   │   ├── connection.py
│   │   │   ├── skill.py
│   │   │   ├── agent.py
│   │   │   ├── pod.py
│   │   │   ├── project.py
│   │   │   ├── ticket.py
│   │   │   └── run.py
│   │   ├── routers/                 # FastAPI route handlers
│   │   │   ├── auth.py
│   │   │   ├── connections.py
│   │   │   ├── skills.py
│   │   │   ├── agents.py
│   │   │   ├── pods.py
│   │   │   ├── projects.py
│   │   │   ├── tickets.py
│   │   │   ├── runs.py
│   │   │   └── audit.py
│   │   ├── services/                # business logic layer
│   │   │   ├── github_service.py    # GitHub API operations
│   │   │   ├── gitlab_service.py    # GitLab API operations
│   │   │   ├── jira_service.py      # Jira REST API operations
│   │   │   ├── storage_service.py   # MinIO file storage (MD files)
│   │   │   └── notification_service.py  # socket.io emit helpers
│   │   ├── agents/                  # LangGraph agent definitions
│   │   │   ├── orchestrator.py      # main graph + state machine
│   │   │   ├── sprint_agent.py      # reads ticket, generates plan
│   │   │   ├── dev_agent.py         # branch, code, commit, PR
│   │   │   ├── qa_agent.py          # trigger tests, parse results
│   │   │   └── devops_agent.py      # merge PR, deploy to env
│   │   ├── tasks/                   # Celery async tasks
│   │   │   └── run_tasks.py         # trigger_run, execute_step
│   │   └── middleware/
│   │       ├── auth_middleware.py
│   │       └── audit_middleware.py
│   ├── migrations/                  # Alembic migration files
│   ├── tests/
│   ├── celery_app.py
│   ├── socket_app.py
│   ├── pyproject.toml
│   └── .env
│
└── README.md
```

---

## 4. Database Schema

```sql
-- USERS
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         VARCHAR(255) UNIQUE NOT NULL,
  name          VARCHAR(255),
  avatar_url    TEXT,
  org_name      VARCHAR(255),
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- CONNECTIONS
CREATE TABLE connections (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID REFERENCES users(id) ON DELETE CASCADE,
  name          VARCHAR(255) NOT NULL,          -- display name
  type          VARCHAR(50) NOT NULL,           -- github | gitlab | jira | github_actions
  status        VARCHAR(50) DEFAULT 'pending',  -- pending | connected | error
  access_token  TEXT,                           -- encrypted
  refresh_token TEXT,                           -- encrypted
  workspace_url TEXT,                           -- jira base URL
  metadata      JSONB DEFAULT '{}',             -- org, username, etc.
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- SKILLS
CREATE TABLE skills (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID REFERENCES users(id) ON DELETE CASCADE,
  name          VARCHAR(255) NOT NULL,
  description   TEXT,
  category      VARCHAR(100),                   -- dev | qa | devops | planning | custom
  md_content    TEXT NOT NULL,                  -- the actual markdown skill definition
  s3_key        TEXT,                           -- if stored in S3
  version       VARCHAR(20) DEFAULT '1.0.0',
  is_active     BOOLEAN DEFAULT TRUE,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- AGENTS
CREATE TABLE agents (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
  name             VARCHAR(255) NOT NULL,
  role             VARCHAR(50) NOT NULL,         -- sprint | dev | qa | devops | custom
  description      TEXT,
  repo_connection_id UUID REFERENCES connections(id),
  default_branch   VARCHAR(255) DEFAULT 'main',
  branch_prefix    VARCHAR(100) DEFAULT 'agent/',
  llm_model        VARCHAR(100) DEFAULT 'claude-sonnet-4-6',
  max_iterations   INT DEFAULT 10,
  config           JSONB DEFAULT '{}',           -- extra agent-level config
  is_active        BOOLEAN DEFAULT TRUE,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- AGENT <-> SKILL bindings
CREATE TABLE agent_skills (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id   UUID REFERENCES agents(id) ON DELETE CASCADE,
  skill_id   UUID REFERENCES skills(id) ON DELETE CASCADE,
  priority   INT DEFAULT 0,                      -- order skills are injected as context
  UNIQUE(agent_id, skill_id)
);

-- PODS
CREATE TABLE pods (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
  name        VARCHAR(255) NOT NULL,
  description TEXT,
  is_active   BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- POD <-> AGENT membership + workflow topology
CREATE TABLE pod_agents (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pod_id          UUID REFERENCES pods(id) ON DELETE CASCADE,
  agent_id        UUID REFERENCES agents(id) ON DELETE CASCADE,
  execution_order INT NOT NULL,                  -- 1=sprint, 2=dev, 3=qa, 4=devops
  count           INT DEFAULT 1,                 -- how many of this agent type in pod
  on_failure      VARCHAR(50) DEFAULT 'retry',   -- retry | escalate | stop
  max_retries     INT DEFAULT 3,
  UNIQUE(pod_id, agent_id)
);

-- PROJECTS
CREATE TABLE projects (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
  name                VARCHAR(255) NOT NULL,
  description         TEXT,
  type                VARCHAR(100),              -- backend | frontend | fullstack | mobile | data
  repo_connection_id  UUID REFERENCES connections(id),
  repo_name           VARCHAR(255),              -- owner/repo-name
  jira_connection_id  UUID REFERENCES connections(id),
  jira_project_key    VARCHAR(50),               -- e.g. PROJ
  pod_id              UUID REFERENCES pods(id),
  context_md          TEXT,                      -- project-level context MD
  deploy_targets      JSONB DEFAULT '[]',        -- [{env: "dev", branch: "develop"}, ...]
  status              VARCHAR(50) DEFAULT 'active',
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- TICKETS (cached from Jira, synced on demand)
CREATE TABLE tickets (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
  jira_id         VARCHAR(100) NOT NULL,         -- e.g. PROJ-42
  title           TEXT NOT NULL,
  description     TEXT,
  type            VARCHAR(50),                   -- bug | feature | task | story
  priority        VARCHAR(50),                   -- highest | high | medium | low
  status          VARCHAR(100),                  -- from Jira
  assignee        VARCHAR(255),
  jira_url        TEXT,
  raw_payload     JSONB DEFAULT '{}',            -- full Jira response cached
  synced_at       TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(project_id, jira_id)
);

-- AGENT RUNS
CREATE TABLE runs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
  ticket_id       UUID REFERENCES tickets(id),
  pod_id          UUID REFERENCES pods(id),
  status          VARCHAR(50) DEFAULT 'queued',  -- queued | running | awaiting_approval | approved | failed | completed
  triggered_by    UUID REFERENCES users(id),
  branch_name     TEXT,                          -- branch created for this run
  pr_url          TEXT,                          -- GitHub/GitLab PR URL
  pr_number       INT,
  current_step    VARCHAR(100),                  -- which agent is currently running
  error_message   TEXT,
  retry_count     INT DEFAULT 0,
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- RUN STEPS (step-by-step trace per run)
CREATE TABLE run_steps (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id      UUID REFERENCES runs(id) ON DELETE CASCADE,
  agent_id    UUID REFERENCES agents(id),
  agent_role  VARCHAR(50),
  step_name   VARCHAR(255),                      -- e.g. "read_ticket", "create_branch", "write_code"
  status      VARCHAR(50),                       -- running | success | failed | skipped
  input       JSONB DEFAULT '{}',
  output      JSONB DEFAULT '{}',                -- what the agent produced
  log         TEXT,                              -- raw LLM output / tool call log
  duration_ms INT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- APPROVALS (human decisions on runs)
CREATE TABLE approvals (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id      UUID REFERENCES runs(id) ON DELETE CASCADE,
  reviewer_id UUID REFERENCES users(id),
  decision    VARCHAR(50),                       -- approved | changes_requested
  comment     TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- AUDIT LOG
CREATE TABLE audit_logs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id),
  action      VARCHAR(255) NOT NULL,             -- e.g. "run.approved", "agent.created"
  entity_type VARCHAR(100),
  entity_id   UUID,
  metadata    JSONB DEFAULT '{}',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. All Pages — What Each Page Does

### AUTH

**`/login`**
- Email + password form
- "Continue with GitHub" OAuth button
- Redirects to `/dashboard` on success

**`/register`**
- Name, email, password, org name
- Same GitHub OAuth option

---

### DASHBOARD `(main layout wraps all below with sidebar)`

**Sidebar nav items:**
```
Dashboard
─────────────
Connections
Skills
Agents
Pods
─────────────
Projects
─────────────
Runs
Audit Log
─────────────
Settings
```

---

**`/dashboard`**
- Stats cards: Total Projects, Active Runs, Pending Approvals, Skills Configured
- Recent runs table (last 10, with status badges)
- Quick action: "New Project" button

---

### CONNECTIONS

**`/connections`**
- Page header: "Connections" + "Add Connection" button
- Stats row: Total / Connected / Error count
- Filter tabs: All | Source Control | Issue Tracker | CI/CD
- Connections list (card or table):
  - Name, Type (badge), Status (connected/error/pending), Last tested, Actions (Test / Edit / Delete)
- Empty state if no connections

**`/connections/new` (modal or page)**
- Provider selector grid: GitHub | GitLab | Jira | GitHub Actions
- On select → show OAuth connect button or API token form depending on provider
- GitHub/GitLab: OAuth flow
- Jira: Base URL + API token + email
- Name field (display name for this connection)
- Test Connection button before saving

**`/connections/[id]`**
- Connection detail: name, type, status, connected account info
- Test Connection button
- Edit name
- Delete connection (with warning if used by agents/projects)
- Usage: "Used by N agents, N projects"

---

### SKILLS REGISTRY

**`/skills`**
- Header: "Skill Registry" + "New Skill" + "Import .md" buttons
- Stats: Total / Active / Used by Agents
- Search bar
- Skills list (cards):
  - Name, Category badge, Description (first line of MD), Version, Used by N agents, Edit / Delete

**`/skills/new`**
- Form fields:
  - Name (text)
  - Category (dropdown: dev | qa | devops | planning | custom)
  - Description (text)
  - Version (text, default "1.0.0")
- Large MD editor (@uiw/react-md-editor) for skill content
- MD editor should show a starter template based on selected category
- Save button → redirects to skill detail

**`/skills/[id]`**
- Same form as new, pre-filled for editing
- Preview panel: rendered MD on the right, editor on left (split view)
- "Agents using this skill" section at bottom
- Delete button (disabled if agents are using it)

**Skill MD starter templates (inject on category select):**

```markdown
<!-- DEV template -->
# Skill: [Name]
## Purpose
Describe what this skill enables the agent to do.

## Tech Stack Context
- Language:
- Framework:
- Key libraries:

## Coding Standards
- ...

## Branch Naming Convention
- Format: agent/[ticket-id]-[short-description]

## What to avoid
- ...
```

---

### AGENTS

**`/agents`**
- Header: "Agents" + "New Agent" button
- Stats: Configured / Active / Skill Associations / In Pods
- Agent search
- Agent cards (left panel) → click to see detail on right
- Each card: Name, Role badge, Skills count, Pod count, Active toggle

**`/agents/new`**
- Step 1 — Basic Info:
  - Name, Role (dropdown: Sprint | Dev | QA | DevOps | Custom), Description
- Step 2 — Skill Bindings:
  - Multi-select from skills list
  - Drag to reorder (priority = injection order into LLM context)
  - Preview: shows combined MD context length
- Step 3 — Repo Config:
  - Select repo connection (dropdown of connected GitHub/GitLab)
  - Default branch (text, default "main")
  - Branch prefix (text, default "agent/")
  - Max iterations (number, default 10)
  - LLM model (dropdown: claude-sonnet-4-6 | claude-opus-4-6)
- Save → agent created

**`/agents/[id]`**
- Same 3-step form, pre-filled
- "Pods using this agent" section
- Disable/Enable toggle
- Delete (disabled if in active pod)

---

### PODS

**`/pods`**
- Header: "Pods" + "New Pod" button
- Stats: Total Pods / Active / Projects using pods
- Pod cards: Name, Agent count, Projects assigned, Active toggle

**`/pods/new`**
- Step 1 — Pod Info: Name, Description
- Step 2 — Agent Builder:
  - "Add Agent" → select from agents list
  - Each added agent shows: Name, Role, execution_order (auto-assigned, draggable to reorder)
  - Per agent config: count (how many), on_failure (retry/escalate/stop), max_retries
  - Visual workflow preview: shows execution order as a simple linear flow diagram
- Step 3 — Workflow Topology:
  - Handoff condition per step (previous step must be: success | any)
  - Failure behavior: retry same agent | escalate to next | stop run
- Save → pod created

**`/pods/[id]`**
- Same editor, pre-filled
- "Projects using this pod" list
- Duplicate pod option

---

### PROJECTS

**`/projects`**
- Header: "Projects" + "New Project" button
- Project cards: Name, Type badge, Pod name, Active runs count, Last run status

**`/projects/new`** — Onboarding Wizard (4 steps)

- Step 1 — Project Info:
  - Project Name, Description, Type (Backend/Frontend/Fullstack/Mobile/Data/Other)

- Step 2 — Source Control:
  - Select repo connection (from connected GitHub/GitLab)
  - Once selected: fetch and show repo list → select repo
  - Select default deploy branches per environment:
    - Dev env → branch name
    - QA env → branch name
    - Prod env → branch name

- Step 3 — Issue Tracker:
  - Select Jira connection
  - Fetch Jira projects → select project key
  - Auto-sync tickets after save: Yes/No toggle

- Step 4 — Pod + Context:
  - Select Pod (from pods list) — required
  - Project Context MD editor (optional): describe codebase conventions, architecture, stack for this specific project
  - Review summary → "Create Project"

**`/projects/[id]`** — Project Overview
- Header: project name, type badge, pod name, "Sync Tickets" button
- Tabs: Overview | Tickets | Runs | Settings
- Overview tab: stats (open tickets, active runs, last deploy), recent activity feed

**`/projects/[id]/tickets`**
- Ticket list pulled from Jira (cached in DB, "Sync" refreshes from Jira API)
- Filters: Status | Priority | Type
- Ticket table: ID, Title, Type, Priority, Status, Jira link
- Click row → ticket detail page
- "Assign to Pod" button per row

**`/projects/[id]/tickets/[ticketId]`**
- Ticket detail: ID, Title, Description (rendered), Priority, Type, Status, Jira link
- Assigned runs for this ticket
- "Run with Pod" button → confirm modal → triggers run
- If active run exists: show run status inline

**`/projects/[id]/runs`**
- Run history for this project
- Same as global runs page but scoped to project

**`/projects/[id]/settings`**
- Edit project name, description, type
- Change pod assignment
- Change repo/Jira connections
- Update deploy branch config
- Update project context MD
- Danger zone: Archive project / Delete project

---

### RUNS

**`/runs`** — All Runs (global)
- Stats: Total / Running / Awaiting Approval / Completed / Failed
- Filter: Status | Project | Pod | Date range
- Runs table: Project, Ticket ID, Pod, Status badge, Current step, Started, Duration, Actions

**`/runs/[id]`** — Run Detail + Approval Gate

Layout: two-panel

Left panel — Step Trace:
- Run header: Ticket ID, Project, Pod, Status, Branch name, PR link
- Step-by-step trace (vertical timeline):
  - Each step: agent role icon, step name, status badge, duration, expand/collapse log
  - Logs show raw LLM output and tool calls
  - Current step shows live streaming if run is active

Right panel — Approval Gate (shown when status = "awaiting_approval"):
- PR Diff viewer (react-diff-viewer-continued) showing what the agent changed
- Test results summary: pass/fail counts, coverage %
- Agent's explanation of changes (from sprint plan)
- Two buttons: "Approve & Deploy" (green) | "Request Changes" (red)
- Comment textarea (required for Request Changes)
- Approval history (if previously reviewed)

If run failed:
- Error message displayed prominently
- "Retry Run" button
- Which step failed and why

---

### AUDIT LOG

**`/audit`**
- Full audit trail of all platform actions
- Filters: User | Action type | Entity type | Date range
- Table: Timestamp, User, Action, Entity, Details
- Export to CSV button

---

### SETTINGS

**`/settings`**
- Profile: name, email, avatar
- Organization: org name
- LLM Config: default model, API key status (masked)
- Notification preferences: email on approval needed, email on run fail
- Danger zone: Delete account

---

## 6. API Endpoints

### Auth
```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/refresh
GET    /api/auth/github/url          → returns OAuth URL
GET    /api/auth/github/callback     → exchanges code for token
GET    /api/auth/jira/url
GET    /api/auth/jira/callback
GET    /api/auth/me
```

### Connections
```
GET    /api/connections              → list all
POST   /api/connections              → create
GET    /api/connections/{id}
PUT    /api/connections/{id}
DELETE /api/connections/{id}
POST   /api/connections/{id}/test    → test connectivity
GET    /api/connections/{id}/repos   → fetch repos from GitHub/GitLab
GET    /api/connections/{id}/projects → fetch Jira projects
```

### Skills
```
GET    /api/skills
POST   /api/skills
GET    /api/skills/{id}
PUT    /api/skills/{id}
DELETE /api/skills/{id}
POST   /api/skills/import            → import from .md file upload
```

### Agents
```
GET    /api/agents
POST   /api/agents
GET    /api/agents/{id}
PUT    /api/agents/{id}
DELETE /api/agents/{id}
PATCH  /api/agents/{id}/toggle       → enable/disable
GET    /api/agents/{id}/skills       → get bound skills
POST   /api/agents/{id}/skills       → bind skill
DELETE /api/agents/{id}/skills/{skillId}
```

### Pods
```
GET    /api/pods
POST   /api/pods
GET    /api/pods/{id}
PUT    /api/pods/{id}
DELETE /api/pods/{id}
POST   /api/pods/{id}/duplicate
GET    /api/pods/{id}/agents
POST   /api/pods/{id}/agents         → add agent to pod
PUT    /api/pods/{id}/agents/{agentId} → update topology config
DELETE /api/pods/{id}/agents/{agentId}
```

### Projects
```
GET    /api/projects
POST   /api/projects
GET    /api/projects/{id}
PUT    /api/projects/{id}
DELETE /api/projects/{id}
PATCH  /api/projects/{id}/archive
```

### Tickets
```
GET    /api/projects/{id}/tickets         → list cached tickets
POST   /api/projects/{id}/tickets/sync    → re-fetch from Jira
GET    /api/projects/{id}/tickets/{ticketId}
```

### Runs
```
GET    /api/runs                          → all runs (filterable)
POST   /api/runs                          → trigger new run {project_id, ticket_id, pod_id}
GET    /api/runs/{id}
GET    /api/runs/{id}/steps               → step trace
POST   /api/runs/{id}/approve             → {decision: "approved"|"changes_requested", comment}
POST   /api/runs/{id}/retry
DELETE /api/runs/{id}/cancel
GET    /api/projects/{id}/runs            → runs scoped to project
```

### Audit
```
GET    /api/audit                         → filterable audit log
GET    /api/audit/export                  → CSV download
```

### Settings
```
GET    /api/settings
PUT    /api/settings
PUT    /api/settings/llm                  → update LLM API key
```

---

## 7. Agent Orchestration (LangGraph)

### State Definition
```python
# backend/app/agents/orchestrator.py

from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END

class SDLCState(TypedDict):
    run_id: str
    ticket: dict                  # full ticket data
    project: dict                 # project config
    pod: dict                     # pod + agents config
    sprint_plan: Optional[str]    # output of sprint agent
    branch_name: Optional[str]    # created by dev agent
    code_changes: Optional[list]  # list of file changes
    pr_url: Optional[str]
    pr_number: Optional[int]
    test_results: Optional[dict]  # {passed, failed, coverage}
    current_agent: str
    iteration: int
    max_iterations: int
    errors: List[str]
    awaiting_approval: bool
    approval_decision: Optional[str]
    deploy_env: str               # dev | qa | prod
    status: str
```

### Graph Flow
```
START
  └─► sprint_agent_node
        └─► dev_agent_node
              └─► qa_agent_node
                    ├─► (tests pass) ──► await_approval_node
                    │                         └─► (approved) ──► devops_agent_node
                    │                         └─► (changes_requested) ──► dev_agent_node (retry)
                    └─► (tests fail, retry < max) ──► dev_agent_node
                    └─► (tests fail, max retries) ──► END (failed)
```

### Each Agent Node
```python
# Each node follows this pattern:

async def sprint_agent_node(state: SDLCState) -> SDLCState:
    # 1. Load agent config from DB
    # 2. Build system prompt: skill MDs + project context MD + ticket data
    # 3. Call Claude API
    # 4. Parse output into structured sprint plan
    # 5. Emit socket event: run step update
    # 6. Write run_step to DB
    # 7. Return updated state
    ...

async def dev_agent_node(state: SDLCState) -> SDLCState:
    # 1. Load dev agent config + skill MDs
    # 2. Read sprint plan from state
    # 3. Call Claude API to generate code changes
    # 4. Use GitHub service to: create branch, commit changes, open PR
    # 5. Emit socket event: step update + PR URL
    # 6. Write run_step to DB
    # 7. Return updated state
    ...

async def qa_agent_node(state: SDLCState) -> SDLCState:
    # 1. Load QA agent config + skill MDs
    # 2. Trigger test run via GitHub Actions API or direct test runner
    # 3. Poll for results (with timeout)
    # 4. Parse test output
    # 5. Decide: pass → continue, fail → retry dev, max retries → fail run
    # 6. Emit socket event
    # 7. Return updated state
    ...

async def await_approval_node(state: SDLCState) -> SDLCState:
    # 1. Update run status to "awaiting_approval"
    # 2. Emit socket event: approval needed
    # 3. Send notification (email/Slack)
    # 4. Return state — graph PAUSES here
    # (Graph resumes when /api/runs/{id}/approve is called)
    ...

async def devops_agent_node(state: SDLCState) -> SDLCState:
    # 1. Merge PR
    # 2. Trigger deploy to current env (dev first)
    # 3. Run smoke test on deployed env
    # 4. If pass: move to next env (QA, then prod)
    # 5. If fail: re-queue dev agent loop
    # 6. Emit socket event per env deploy
    # 7. Return updated state
    ...
```

---

## 8. WebSocket Events (Real-time Run Updates)

```typescript
// Frontend listens to these events via socket.io

"run:started"           → { runId, ticketId, podName }
"run:step:started"      → { runId, stepName, agentRole }
"run:step:log"          → { runId, stepName, log: string }   // streamed line by line
"run:step:completed"    → { runId, stepName, status, output }
"run:step:failed"       → { runId, stepName, error }
"run:awaiting_approval" → { runId, prUrl, prNumber }
"run:approved"          → { runId, reviewer, decision }
"run:deploy:started"    → { runId, env }
"run:deploy:completed"  → { runId, env, url }
"run:completed"         → { runId, status }
"run:failed"            → { runId, error, retryCount }
```

---

## 9. Environment Variables

```bash
# backend/.env

DATABASE_URL=postgresql://user:pass@localhost:5432/agentic_sdlc
REDIS_URL=redis://localhost:6379

ANTHROPIC_API_KEY=sk-ant-...

GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=http://localhost:8000/auth/github/callback

GITLAB_CLIENT_ID=
GITLAB_CLIENT_SECRET=
GITLAB_REDIRECT_URI=

JIRA_CLIENT_ID=
JIRA_CLIENT_SECRET=
JIRA_REDIRECT_URI=

MINIO_ENDPOINT=http://minio:9000           # internal Docker service name
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=agentic-sdlc-skills
MINIO_PUBLIC_URL=https://yourdomain.com/minio  # public URL via Nginx proxy

JWT_SECRET=your-secret-key
JWT_EXPIRY_HOURS=24

FRONTEND_URL=http://localhost:3000
ENCRYPTION_KEY=32-char-key-for-token-encryption
```

```bash
# frontend/.env

VITE_API_URL=https://yourdomain.com/api   # Nginx proxies /api to FastAPI
VITE_SOCKET_URL=https://yourdomain.com
VITE_GITHUB_CLIENT_ID=
```

---

## 10. Build Order for Claude Code

Follow this exact sequence. Each phase must be complete and working before moving to the next.

### Phase 1 — Foundation (Week 1)
```
1.  Set up Vite + React project with TypeScript, Tailwind, shadcn/ui, React Router v6
2.  Set up FastAPI project with SQLAlchemy, Alembic, Pydantic
3.  Set up PostgreSQL + run initial migration (all tables)
4.  Set up Redis + Celery
5.  Implement JWT auth (register, login, /me)
6.  Build DashboardLayout (sidebar + topbar) and AuthLayout in React
7.  Build auth pages (LoginPage, RegisterPage) with React Router routes
```

### Phase 2 — Connections (Week 1-2)
```
8.  GitHub OAuth flow (backend + frontend callback)
9.  Jira OAuth/API token flow
10. Connections CRUD API
11. Connections list page + add connection modal
12. Connection test endpoint + UI feedback
13. Fetch repos from GitHub connection
14. Fetch projects from Jira connection
```

### Phase 3 — Skills (Week 2)
```
15. Skills CRUD API
16. Skills list page
17. New skill page with MD editor + category templates
18. Skill detail/edit page with split preview
```

### Phase 4 — Agents (Week 2-3)
```
19. Agents CRUD API
20. Agent-skill binding API
21. Agents list page
22. New agent wizard (3 steps: info, skills, repo config)
23. Agent detail/edit page
```

### Phase 5 — Pods (Week 3)
```
24. Pods CRUD API
25. Pod-agent topology API
26. Pods list page
27. New pod wizard (info + agent builder + topology)
28. Pod detail/edit page
```

### Phase 6 — Projects (Week 3-4)
```
29. Projects CRUD API
30. Ticket sync API (Jira fetch + cache in DB)
31. Project onboarding wizard (4 steps)
32. Project list page
33. Project detail page (tabs: overview, tickets, runs, settings)
34. Ticket list + sync button
35. Ticket detail page + "Run with Pod" trigger
```

### Phase 7 — Agent Orchestration (Week 4-5)
```
36. LangGraph state definition
37. Sprint agent node (ticket → sprint plan via Claude API)
38. Dev agent node (sprint plan → branch → code → PR via GitHub API)
39. QA agent node (test trigger → parse results)
40. Await approval node (pause graph, update run status)
41. DevOps agent node (merge PR → deploy → smoke test)
42. Celery task: trigger_run (wraps full graph execution)
43. Run creation API + trigger endpoint
44. WebSocket socket.io setup (emit events from each agent node)
```

### Phase 8 — Runs UI (Week 5)
```
45. Runs CRUD API (list, get, approve, retry, cancel)
46. Run steps API
47. Global runs list page
48. Run detail page (step trace + approval gate)
49. PR diff viewer component
50. Frontend socket.io listener (real-time step updates)
51. Approval gate UI (approve/reject + comment)
```

### Phase 9 — Dashboard + Audit (Week 6)
```
52. Dashboard stats API
53. Dashboard page with stats + recent runs
54. Audit log middleware (auto-log all mutations)
55. Audit log API
56. Audit log page
57. Settings page (profile + LLM config)
```

### Phase 10 — Polish (Week 6)
```
58. Error handling + toast notifications throughout
59. Loading states + skeleton screens
60. Empty states for all list pages
61. Responsive layout check
62. API error boundaries in frontend
63. Run retry logic in orchestrator
64. Token encryption for stored OAuth tokens
65. Basic input validation on all forms
```

---

## 11. Key Implementation Notes for Claude Code

**Token storage:** Never store raw OAuth tokens in the DB. Encrypt using the `ENCRYPTION_KEY` env var with Fernet (Python cryptography library) before storing. Decrypt only in the service layer when making API calls.

**LangGraph graph persistence:** Use LangGraph's built-in checkpoint saver with PostgreSQL so run state survives server restarts. The await_approval_node pauses the graph — it resumes when the `/approve` endpoint is called, which calls `graph.update_state()` with the approval decision.

**Skill MD injection:** When building the LLM system prompt for any agent, concatenate: (1) agent role description, (2) all bound skill MDs in priority order, (3) project context MD, (4) current task context (ticket or step output). Keep total context under 180K tokens.

**GitHub API operations in dev agent:** Create branch from default branch → commit file changes one by one using GitHub Contents API → open PR with sprint plan as description. Use PyGithub library for simplicity.

**Real-time run streaming:** Socket.io rooms = run IDs. Frontend joins room `run:{runId}` on the run detail page. Backend emits to that room from inside each agent node.

**Jira ticket sync:** On "Sync Tickets" button, call Jira REST API `/rest/api/3/search` with JQL `project={key} AND status != Done ORDER BY updated DESC`. Upsert into tickets table using `jira_id` as unique key.

**Celery task for runs:** Do NOT run the entire LangGraph graph in a single Celery task — the await_approval_node pauses indefinitely for human input, which would exhaust Celery workers. Instead use two tasks:
- `task_run_until_approval(run_id)` — runs the graph from start (or last checkpoint) until the graph pauses at await_approval_node, then the Celery task completes. State is persisted by the LangGraph PostgreSQL checkpoint saver.
- `task_resume_after_approval(run_id)` — triggered by the `/approve` endpoint, resumes the graph from the checkpoint and runs through to completion (devops deploy).

This way Celery workers are never held open waiting for a human.

**Multi-environment deploy loop:** DevOps agent deploys to envs in order: dev → QA → prod. Each env deploy is a separate run_step. After each deploy, QA agent is invoked again to verify on that env. Only moves to next env on pass.

**MinIO instead of S3:** Use the `minio` Python client (`pip install minio`). The API is identical to boto3 S3 calls — bucket creation, put_object, get_object, presigned URLs all work the same way. Storage service should expose the same interface so swapping to S3 later requires zero code change.

---

## 12. Contabo VPS Deployment

### Updated Repo Structure (add to root)
```
agentic-sdlc/
├── docker-compose.yml          # all services
├── docker-compose.prod.yml     # production overrides
├── nginx/
│   ├── nginx.conf              # main Nginx config
│   └── conf.d/
│       └── app.conf            # site-specific routing
├── frontend/
│   └── Dockerfile
├── backend/
│   └── Dockerfile
└── .github/
    └── workflows/
        └── deploy.yml          # GitHub Actions SSH deploy
```

### `docker-compose.yml`
```yaml
version: "3.9"

services:

  postgres:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_USER: sdlc_user
      POSTGRES_PASSWORD: sdlc_pass
      POSTGRES_DB: agentic_sdlc
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"             # internal only in prod (remove port mapping)

  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio:latest
    restart: always
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"             # API
      - "9001:9001"             # Console UI

  backend:
    build: ./backend
    restart: always
    env_file: ./backend/.env
    depends_on:
      - postgres
      - redis
      - minio
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app          # remove in prod (use image only)

  celery_worker:
    build: ./backend
    restart: always
    command: celery -A celery_app worker --loglevel=info --pool=gevent --concurrency=10
    env_file: ./backend/.env
    depends_on:
      - postgres
      - redis
      - minio

  frontend:
    build: ./frontend
    restart: always
    ports:
      - "3000:80"               # nginx inside container serves on 80
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - /etc/letsencrypt:/etc/letsencrypt:ro   # SSL certs
    depends_on:
      - frontend
      - backend

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

### `nginx/conf.d/app.conf`
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    client_max_body_size 20M;

    # Frontend (Vite + React, served by nginx)
    location / {
        proxy_pass         http://frontend:80;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
    }

    # Backend API (FastAPI)
    location /api/ {
        rewrite            ^/api/(.*)$ /$1 break;
        proxy_pass         http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket (Socket.io)
    location /socket.io/ {
        proxy_pass         http://backend:8000/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
    }

    # MinIO (file storage API)
    location /minio/ {
        rewrite            ^/minio/(.*)$ /$1 break;
        proxy_pass         http://minio:9000;
        proxy_set_header   Host $host;
    }
}
```

### `backend/Dockerfile`
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN alembic upgrade head    # run migrations on start

CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

### `frontend/Dockerfile`
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build                     # outputs to /app/dist

FROM nginx:alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

> `nginx-spa.conf` — needed so React Router deep links work correctly:
> ```nginx
> server {
>     listen 80;
>     root /usr/share/nginx/html;
>     index index.html;
>     location / {
>         try_files $uri $uri/ /index.html;
>     }
> }
> ```

### `github/workflows/deploy.yml` — Auto-deploy on push to main
```yaml
name: Deploy to Contabo

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: SSH deploy
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.CONTABO_HOST }}
          username: ${{ secrets.CONTABO_USER }}
          key: ${{ secrets.CONTABO_SSH_KEY }}
          script: |
            cd /opt/agentic-sdlc
            git pull origin main
            docker compose pull
            docker compose up -d --build
            docker compose exec backend alembic upgrade head
            docker image prune -f
```

### First-time Contabo Server Setup (run once)
```bash
# 1. SSH into Contabo VPS
ssh root@your-contabo-ip

# 2. Install Docker + Docker Compose
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
apt install docker-compose-plugin -y

# 3. Clone repo
mkdir -p /opt/agentic-sdlc
cd /opt/agentic-sdlc
git clone https://github.com/your-org/agentic-sdlc.git .

# 4. Add .env files
nano backend/.env        # paste backend env vars
nano frontend/.env.local # paste frontend env vars

# 5. SSL with Let's Encrypt (before starting Nginx)
apt install certbot -y
certbot certonly --standalone -d yourdomain.com

# 6. Start everything
docker compose up -d

# 7. Create MinIO bucket (one-time)
docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker compose exec minio mc mb local/agentic-sdlc-skills

# 8. Verify all services running
docker compose ps
```

### GitHub Actions Secrets to Add
```
CONTABO_HOST       → your Contabo VPS IP
CONTABO_USER       → root (or deploy user)
CONTABO_SSH_KEY    → private SSH key for the VPS
```
```
