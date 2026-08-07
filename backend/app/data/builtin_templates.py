"""
First-party template library — skills, agents and pods shipped with the platform.

Time-to-first-run is the self-serve growth constraint: starting from an empty
skill editor is hours of work before a user sees any value. These templates take
it to minutes, and they seed the marketplace so it is never an empty room on
launch day.

Skill content is deliberately written the way an engineering lead would write
it — specific rules, not motivational prose — because that is what actually
steers a model.
"""
from __future__ import annotations

SKILL_TEMPLATES: list[dict] = [
    {
        "slug": "python-backend-standards",
        "name": "Python Backend Standards",
        "category": "backend",
        "tags": ["python", "fastapi", "backend"],
        "description": "Type hints, error handling, layering and dependency rules for Python services.",
        "md_content": """# Python Backend Standards

## Structure
- Routers handle HTTP only: validate, call a service, shape the response. No business logic, no ORM queries in a route body beyond a simple fetch.
- Services own business logic and are import-safe (no FastAPI imports).
- Models are declarative only — no queries defined on the model class.

## Typing and validation
- Every public function is fully annotated. `from __future__ import annotations` at the top of new modules.
- Validate at the boundary with Pydantic; inside the service layer trust your own types.
- Never use bare `except:`. Catch the narrowest exception you can name and log with `logger.exception`.

## Database
- One unit of work per request; commit once at the end of a mutation.
- Every filter on a user-scoped table includes the owner clause. A missing scope filter is a security bug, not a style issue.
- Use `select`/`query` with explicit columns when the row is wide.

## Errors
- Raise `HTTPException` with a message a user can act on; never leak stack traces or SQL.
- 4xx means the caller can fix it; 5xx means we can.
""",
    },
    {
        "slug": "react-frontend-standards",
        "name": "React + TypeScript Standards",
        "category": "frontend",
        "tags": ["react", "typescript", "frontend"],
        "description": "Component structure, data fetching, and state rules for React 19 + TS.",
        "md_content": """# React + TypeScript Standards

## Components
- Function components only. One component per file, named the same as the file.
- Props get an explicit `interface`. No `any`, no `React.FC`.
- Extract a hook when a component's logic exceeds ~40 lines before the return.

## Data
- Server state goes through TanStack Query; never mirror it into local state.
- Client-only state (open/closed, form drafts) stays in `useState` or a store — not in the query cache.
- Mutations invalidate the specific query keys they affect, not the whole cache.

## Rendering
- Derive during render instead of syncing with `useEffect`. An effect that only computes a value is a bug.
- Every list has a stable `key` from data, never the array index.
- Loading and empty states are required, not optional — a spinner-less fetch is an unfinished component.

## Styling
- Tailwind utilities in the markup; extract a component when a class string repeats three times.
- Use design tokens (`bg-card`, `text-muted-foreground`), never raw hex or arbitrary greys.
""",
    },
    {
        "slug": "secure-coding-checklist",
        "name": "Secure Coding Checklist",
        "category": "security",
        "tags": ["security", "owasp", "review"],
        "description": "The security rules an agent must apply to every change it writes or reviews.",
        "md_content": """# Secure Coding Checklist

Apply to every change. A violation is a `high` or `critical` finding.

## Input and output
- Parameterised queries only. String-built SQL is critical, no exceptions.
- Escape or sanitise anything rendered into HTML. `dangerouslySetInnerHTML` requires a sanitiser in the same expression.
- Validate file paths against a canonical root before any read or write.

## AuthN / AuthZ
- Every endpoint that reads or mutates user data filters by the authenticated owner.
- Never trust an id from the client as proof of ownership — resolve and check it.
- Authorisation belongs in the service layer, not only in the UI.

## Secrets
- No credentials, tokens or keys in source, tests, fixtures or logs.
- Secrets come from environment/config only, and are redacted in any error output.

## Dependencies and crypto
- No new dependency for something the standard library does.
- Use vetted crypto primitives; never hand-roll hashing, signing or token generation.
- Compare secrets with a constant-time function.
""",
    },
    {
        "slug": "test-coverage-policy",
        "name": "Test Coverage Policy",
        "category": "testing",
        "tags": ["testing", "quality"],
        "description": "What must be tested, how tests are named, and what a good assertion looks like.",
        "md_content": """# Test Coverage Policy

## What must have a test
- Every bug fix ships with a test that fails before the fix.
- Every new branch of business logic (each `if`, each error path).
- Every public API contract: status code, response shape, and the auth failure case.

## What must not
- Do not test framework behaviour, getters, or that a mock was called.
- Do not assert on log output.

## Style
- Name tests `test_<subject>_<condition>_<expected>`.
- Arrange / act / assert, separated by blank lines.
- One behaviour per test. If the name needs "and", split it.
- Prefer real objects; mock only at process boundaries (network, clock, filesystem).

## Data
- Build fixtures with factories, not copied literals.
- No shared mutable state between tests; each test creates what it needs.
""",
    },
    {
        "slug": "pr-review-rubric",
        "name": "PR Review Rubric",
        "category": "review",
        "tags": ["review", "quality"],
        "description": "Severity definitions and review scope for the Reviewer agent.",
        "md_content": """# PR Review Rubric

## Severity
- **critical** — data loss, security hole, or a production outage path.
- **high** — incorrect behaviour a user will hit, or an untested error path in new logic.
- **medium** — correctness risk under load or edge input; missing test for a new branch.
- **low** — maintainability, naming, duplication with a clear cost.
- **info** — observation with no required action.

## In scope
Correctness, security, missing tests, resource leaks, N+1 queries, error handling, API contract changes, migration safety.

## Out of scope
Formatting a linter owns, personal style preferences, renaming that has no functional benefit.

## How to report
- One finding per problem, with the file and the line.
- State the failure the reader would observe, not just the rule that was broken.
- Always include a concrete suggested fix. "Consider refactoring" is not a finding.
""",
    },
    {
        "slug": "sprint-planning-rules",
        "name": "Sprint Planning Rules",
        "category": "planning",
        "tags": ["planning", "sprint"],
        "description": "How the Planner agent turns a ticket into an implementation plan.",
        "md_content": """# Sprint Planning Rules

## Output shape
1. **Goal** — one sentence a non-engineer understands.
2. **Files to change** — explicit paths, each with what changes and why.
3. **Steps** — ordered, each independently verifiable.
4. **Tests** — the specific cases that prove the goal is met.
5. **Risks** — what could break, and how to tell.

## Rules
- Never plan a change to a file you have not seen the contents of; say you need to read it.
- If the ticket is ambiguous, state the interpretation you are proceeding with, then proceed. Do not stall on a question.
- Keep the plan to the ticket's scope. Adjacent cleanups belong in a follow-up ticket, named in Risks.
- Prefer the smallest change that fully solves the problem over the most general one.
""",
    },
    {
        "slug": "api-design-guidelines",
        "name": "REST API Design Guidelines",
        "category": "backend",
        "tags": ["api", "rest", "http"],
        "description": "Resource naming, status codes, pagination and versioning conventions.",
        "md_content": """# REST API Design Guidelines

## Naming
- Plural nouns for collections: `/projects`, `/projects/{id}/runs`.
- Actions that are not CRUD become sub-resources: `POST /runs/{id}/approve`.
- Filters are query params; never encode a filter in the path.

## Status codes
- 200 read, 201 create (with the created body), 204 delete.
- 400 malformed, 401 unauthenticated, 403 authenticated but not allowed, 404 missing *or* not yours, 409 conflict, 422 semantically invalid.
- Never return 200 with an error body.

## Payloads
- snake_case JSON, ISO-8601 UTC timestamps, string UUIDs.
- Collections return an object with the list under a named key, not a bare array, so pagination can be added without a breaking change.

## Compatibility
- Adding an optional field is safe; removing or renaming one is a breaking change and needs a new version.
- Never repurpose an existing field's meaning.
""",
    },
    {
        "slug": "database-migration-safety",
        "name": "Database Migration Safety",
        "category": "backend",
        "tags": ["database", "migrations", "postgres"],
        "description": "Zero-downtime migration rules for a live system.",
        "md_content": """# Database Migration Safety

## The rule
Every migration must be safe to run while the previous version of the app is still serving traffic.

## Safe
- Add a nullable column; backfill in batches; add the NOT NULL constraint in a later migration.
- Create an index `CONCURRENTLY`.
- Add a new table.

## Unsafe without a multi-step plan
- Dropping or renaming a column still referenced by running code — deploy the code that stops using it first.
- Adding a NOT NULL column with no default to a large table.
- A blocking index build on a hot table.

## Always
- Provide a working `downgrade`.
- Never edit a migration that has run in any environment; add a new one.
- Wrap data backfills in explicit batches with a bounded loop, not one statement over the whole table.
""",
    },
    {
        "slug": "commit-and-pr-hygiene",
        "name": "Commit and PR Hygiene",
        "category": "process",
        "tags": ["git", "process"],
        "description": "Commit message format and what a PR description must contain.",
        "md_content": """# Commit and PR Hygiene

## Commits
- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- Subject in the imperative, under 72 characters, no trailing period.
- The body explains *why*; the diff already shows *what*.

## Pull requests
Every PR description contains:
1. What changed, in two sentences.
2. Why — link the ticket.
3. How it was verified (tests added, manual steps run).
4. Risk and rollback: what to watch after deploy, and how to revert.

## Size
- Under ~400 changed lines. Beyond that, split it — review quality falls off a cliff and this is where agent-written changes get rubber-stamped.
""",
    },
    {
        "slug": "observability-standards",
        "name": "Observability Standards",
        "category": "devops",
        "tags": ["logging", "metrics", "observability"],
        "description": "Logging, metrics and tracing rules so failures are diagnosable.",
        "md_content": """# Observability Standards

## Logging
- Structured logs (key/value), never f-string prose that has to be regex-parsed later.
- Levels: `error` = someone must act; `warning` = degraded but handled; `info` = state change worth auditing; `debug` = developer detail.
- Every log line in a request path carries the request/run id.
- Never log secrets, tokens, full request bodies, or personal data.

## Metrics
- Count every external call and its failures.
- Time every operation that can exceed 100ms.
- Emit a business metric for each product-meaningful event (run started, approval granted, deploy completed).

## Failure paths
- Every `except` either re-raises or logs with context. A silent `pass` needs a comment saying why silence is correct.
""",
    },
    {
        "slug": "docs-writing-style",
        "name": "Documentation Style",
        "category": "docs",
        "tags": ["docs", "writing"],
        "description": "How the agent writes READMEs, docstrings and changelogs.",
        "md_content": """# Documentation Style

## Docstrings
- Explain *why* the code exists and any non-obvious constraint. The signature already says what it takes.
- Document the failure modes: what it raises, and when it returns empty.
- No docstring is better than a docstring that restates the function name.

## READMEs
- First paragraph: what this is and who it is for.
- Then: run it locally in copy-pasteable commands that actually work from a clean clone.
- Then: configuration, with every environment variable and its default.

## Tone
- Second person, present tense, active voice.
- No marketing adjectives in technical docs.
- Show a real command or snippet instead of describing one.
""",
    },
    {
        "slug": "performance-budget",
        "name": "Performance Budget",
        "category": "quality",
        "tags": ["performance"],
        "description": "Concrete limits the agent must design within.",
        "md_content": """# Performance Budget

## Backend
- p95 API response under 300ms for reads, 800ms for writes.
- No unbounded query: every list endpoint has a limit, default 50, max 200.
- No N+1: if you iterate rows and query inside the loop, join or batch instead.
- Any call over 2s moves to a background task.

## Frontend
- No blocking request in a render path; fetch in a hook with a loading state.
- Debounce anything driven by typing (250ms minimum).
- Images have explicit dimensions to avoid layout shift.

## Data
- Index every column used in a WHERE or ORDER BY on a table expected to exceed 10k rows.
- Paginate anything that can grow without bound.
""",
    },
    {
        "slug": "deployment-runbook",
        "name": "Deployment Runbook",
        "category": "devops",
        "tags": ["deploy", "devops", "release"],
        "description": "Pre-flight, promotion and rollback steps the DevOps agent follows.",
        "md_content": """# Deployment Runbook

## Before promoting
- CI green on the exact commit being promoted.
- Migrations reviewed for the safety rules and applied before app rollout.
- Config/secrets required by the new code exist in the target environment.

## Promotion order
dev → qa → staging → production. Never skip an environment to save time; a skipped environment is where the outage comes from.

## After deploying
- Watch error rate and p95 latency for 10 minutes.
- Verify one real user-facing path manually.

## Rollback
- Revert first, diagnose after. A rollback needs no meeting.
- If a migration is not backward compatible, roll forward with a fix instead — say so explicitly in the PR's risk section.
""",
    },
    {
        "slug": "accessibility-baseline",
        "name": "Accessibility Baseline",
        "category": "frontend",
        "tags": ["a11y", "frontend"],
        "description": "The WCAG-shaped rules every UI change must satisfy.",
        "md_content": """# Accessibility Baseline

- Every interactive element is reachable and operable by keyboard, with a visible focus ring.
- Buttons are `<button>`, links are `<a>`. A `div` with `onClick` is a defect.
- Every input has a associated `<label>`; placeholder text is not a label.
- Images have `alt`; decorative images have `alt=""`.
- Text contrast at least 4.5:1; 3:1 for large text and UI borders.
- Colour is never the only signal — pair it with text or an icon.
- Modals trap focus, close on Escape, and restore focus to the trigger.
- Live regions announce async state changes (saving, error, success).
""",
    },
]

AGENT_TEMPLATES: list[dict] = [
    {
        "slug": "planner-agent",
        "name": "Planner Agent",
        "category": "planning",
        "description": "Turns a ticket into an explicit, file-level implementation plan.",
        "payload": {"role": "sprint", "llm_model": "claude-sonnet-4-6",
                    "skills": ["sprint-planning-rules", "api-design-guidelines"],
                    "config": {"max_iterations": 6}},
    },
    {
        "slug": "python-dev-agent",
        "name": "Python Backend Dev Agent",
        "category": "backend",
        "description": "Writes FastAPI/SQLAlchemy code to the org's backend standards.",
        "payload": {"role": "dev", "llm_model": "claude-sonnet-4-6",
                    "skills": ["python-backend-standards", "secure-coding-checklist",
                               "test-coverage-policy", "database-migration-safety"],
                    "config": {"max_iterations": 10}},
    },
    {
        "slug": "react-dev-agent",
        "name": "React Frontend Dev Agent",
        "category": "frontend",
        "description": "Writes React 19 + TypeScript UI to the org's frontend standards.",
        "payload": {"role": "dev", "llm_model": "claude-sonnet-4-6",
                    "skills": ["react-frontend-standards", "accessibility-baseline",
                               "test-coverage-policy"],
                    "config": {"max_iterations": 10}},
    },
    {
        "slug": "reviewer-agent",
        "name": "Reviewer Agent",
        "category": "review",
        "description": "Scores the PR against your rubric and posts structured findings.",
        "payload": {"role": "reviewer", "llm_model": "claude-sonnet-4-6",
                    "skills": ["pr-review-rubric", "secure-coding-checklist",
                               "performance-budget"],
                    "config": {"max_iterations": 4}},
    },
    {
        "slug": "qa-agent",
        "name": "QA Agent",
        "category": "testing",
        "description": "Verifies tests exist, run, and actually cover the change.",
        "payload": {"role": "qa", "llm_model": "claude-sonnet-4-6",
                    "skills": ["test-coverage-policy", "performance-budget"],
                    "config": {"max_iterations": 6}},
    },
    {
        "slug": "devops-agent",
        "name": "DevOps Agent",
        "category": "devops",
        "description": "Merges and promotes across environments following the runbook.",
        "payload": {"role": "devops", "llm_model": "claude-sonnet-4-6",
                    "skills": ["deployment-runbook", "observability-standards"],
                    "config": {"max_iterations": 4}},
    },
]

POD_TEMPLATES: list[dict] = [
    {
        "slug": "standard-sdlc-pod",
        "name": "Standard SDLC Pod",
        "category": "general",
        "description": "Plan → code → QA → review → human approval → deploy. The default.",
        "payload": {"agents": [
            {"template_slug": "planner-agent", "role": "sprint", "execution_order": 1,
             "on_failure": "stop", "max_retries": 1},
            {"template_slug": "python-dev-agent", "role": "dev", "execution_order": 2,
             "on_failure": "retry", "max_retries": 2},
            {"template_slug": "qa-agent", "role": "qa", "execution_order": 3,
             "on_failure": "retry", "max_retries": 2},
            {"template_slug": "reviewer-agent", "role": "reviewer", "execution_order": 4,
             "on_failure": "continue", "max_retries": 1},
            {"template_slug": "devops-agent", "role": "devops", "execution_order": 5,
             "on_failure": "stop", "max_retries": 1},
        ]},
    },
    {
        "slug": "review-only-pod",
        "name": "Review-Only Pod",
        "category": "review",
        "description": "No code generation — just governed AI review on incoming PRs.",
        "payload": {"agents": [
            {"template_slug": "reviewer-agent", "role": "reviewer", "execution_order": 1,
             "on_failure": "stop", "max_retries": 1},
        ]},
    },
    {
        "slug": "frontend-pod",
        "name": "Frontend Feature Pod",
        "category": "frontend",
        "description": "React-focused pipeline with accessibility and review gates.",
        "payload": {"agents": [
            {"template_slug": "planner-agent", "role": "sprint", "execution_order": 1,
             "on_failure": "stop", "max_retries": 1},
            {"template_slug": "react-dev-agent", "role": "dev", "execution_order": 2,
             "on_failure": "retry", "max_retries": 2},
            {"template_slug": "qa-agent", "role": "qa", "execution_order": 3,
             "on_failure": "retry", "max_retries": 2},
            {"template_slug": "reviewer-agent", "role": "reviewer", "execution_order": 4,
             "on_failure": "continue", "max_retries": 1},
        ]},
    },
]


def all_templates() -> list[dict]:
    """Flatten to the shape the Template table stores."""
    out: list[dict] = []
    for s in SKILL_TEMPLATES:
        out.append({
            "kind": "skill", "slug": s["slug"], "name": s["name"],
            "description": s["description"], "category": s["category"],
            "tags": s.get("tags", []),
            "payload": {"md_content": s["md_content"], "category": s["category"]},
        })
    for a in AGENT_TEMPLATES:
        out.append({
            "kind": "agent", "slug": a["slug"], "name": a["name"],
            "description": a["description"], "category": a["category"],
            "tags": [a["category"]], "payload": a["payload"],
        })
    for p in POD_TEMPLATES:
        out.append({
            "kind": "pod", "slug": p["slug"], "name": p["name"],
            "description": p["description"], "category": p["category"],
            "tags": [p["category"]], "payload": p["payload"],
        })
    return out
