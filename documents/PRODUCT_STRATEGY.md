# Agentic SDLC — Product Strategy & Investment Thesis

> **The one-liner:** The AI operating system for engineering teams — not just a copilot, not a black-box autonomous agent, but a fully configurable AI development workforce that humans stay in control of.

---

## 1. What You Have Today (Honest Assessment)

You have built a **technically complete v1** of something genuinely novel. Most teams building in this space either:
- Ship a single-purpose copilot (code completion, PR review)
- Build a fully autonomous agent (Devin-style: one agent, full control)

You've built a **composable multi-agent orchestration layer** for the entire SDLC — with human approval gates, audit logs, skill-based configuration, and real integrations (GitHub, Jira). That's a real structural advantage.

**What's working:**
- Full SDLC loop: plan → code → QA → human approval → deploy
- Configurable AI agents built from skill markdown files
- Pod system (multi-agent pipelines with execution order)
- Real-time step-by-step run visibility via WebSocket
- Audit trail on every action
- GitHub PR creation, diff viewing, branch management
- Jira ticket sync and status tracking

**What's missing before you can raise:**  
See Section 5.

---

## 2. The Market Opportunity

### Why Now
The AI developer tools market crossed $4B in 2025 and is projected at $20B+ by 2028. But the market is fragmented between two extreme ends:

| Category | Examples | Problem |
|---|---|---|
| Autocomplete / Copilot | GitHub Copilot, Cursor, Codeium | Assists one developer; doesn't run workflows |
| Fully autonomous agents | Devin, SWE-agent | Black box; enterprise won't trust it in production |
| Project management AI | Linear, Notion AI | No code execution; just text |

**The gap you fill:** Enterprise-safe, configurable, multi-agent SDLC automation where engineering leads define how AI behaves, what it's allowed to do, and where humans must approve.

### Buyer Profile
- **Primary buyer:** Head of Engineering / VP of Engineering at B2B SaaS companies (50–500 engineers)
- **Pain:** Backlog never shrinks, junior developers are expensive and slow, repetitive ticket work burns senior engineers
- **Budget:** Already spending $200–500/engineer/month on tooling (GitHub, Jira, Datadog, etc.)
- **Decision criteria:** Security, auditability, control (they won't buy what they can't govern)

### The Real Pitch to Investors
> "Every engineering team knows they'll eventually run AI agents on their codebase. The question is who controls how those agents behave, what they're allowed to touch, and when humans stay in the loop. We sell the governance layer — the control plane — on top of which AI development runs."

---

## 3. Competitive Landscape

```
                    HIGH CONTROL
                         │
           ┌─────────────┼─────────────────┐
           │             │                 │
    GitHub │        [YOU ARE HERE]         │
    Copilot│    Agentic SDLC               │
           │    - configurable agents      │
           │    - multi-agent pods         │
           │    - human approval gate      │
           │                               │
──────────────────────────────────────────────── SCOPE
 NARROW    │                          BROAD│
(1 action) │                  (full loop)  │
           │                               │
           │         Devin                 │
           │         SWE-agent             │
           │         (low control)         │
           └─────────────────────────────  ┘
                         │
                    LOW CONTROL
```

### Direct Competitors

| Tool | What they do | Your edge |
|---|---|---|
| **Devin (Cognition)** | Fully autonomous coding agent | No enterprise controls, no configurable workflows, black box |
| **GitHub Copilot Workspace** | AI-assisted planning → code in GitHub | Single-agent, no multi-step orchestration, no pod system |
| **Cursor** | IDE copilot with agent mode | Assists one dev, doesn't run unattended workflows |
| **Linear** | AI project management | No code execution at all |
| **Sweep AI** | AI PR creation from GitHub issues | Single-purpose, not orchestrated, no approval gate |
| **Codegen.sh** | AI coding agent | No governance, early stage |

**Your structural moat:** The skill + agent + pod abstraction. No one else lets an engineering lead say: *"This is exactly how my planning agent thinks, these are the rules my QA agent follows, and here is the approval gate before anything ships."*

---

## 4. Why It's Not Yet Investable (and What to Fix)

Investors at pre-seed/seed will ask these 5 questions. Here's the honest gap analysis:

| Question | Current State | What's Needed |
|---|---|---|
| "Who pays for this and how?" | No billing, no pricing | SaaS billing, usage tracking |
| "Can a team use it, not just one person?" | Single-user (no RBAC, no orgs) | Multi-user, org/team model |
| "What's the moat?" | The abstraction exists | Skill library/marketplace, network effects |
| "Do you have users?" | Demo-able but no public users | At least 3 design partners |
| "Can I see the ROI?" | No metrics tracking | ROI dashboard, time-saved tracking |

---

## 5. Product Roadmap — What to Build Next

Organized into four horizons: **Revenue** → **Stickiness** → **Moat** → **Category**.

---

### Horizon 1 — Revenue Foundation (0–3 months)
*Goal: First paying customer. These are "table stakes" features.*

#### 5.1 Multi-User & Organizations
The single biggest blocker. No engineering team makes a purchase decision as one person.

**What to build:**
- `organizations` table — name, plan, seats
- `org_members` table — org_id, user_id, role (owner / admin / member / viewer)
- Organization switcher in sidebar
- Invite by email (send token, accept flow)
- Resource scoping: skills, agents, pods, projects belong to an org, not a user

**Why it matters:** B2B SaaS is never a solo purchase. The moment you add org support, you go from "toy" to "team tool."

#### 5.2 SaaS Billing & Plans
Without this, you can't raise on a revenue story.

**What to build:**
- Stripe integration (Checkout + Customer Portal + Webhooks)
- Plan tiers (see Section 6 — Business Model)
- Usage tracking: `ai_run_credits` per org per month, LLM token cost per run
- Billing page in Settings
- Paywall enforcement (block runs when over limit)
- Usage dashboard: runs used / limit, estimated cost

**Why it matters:** Investors fund businesses, not projects. Billing signals you're building a business.

#### 5.3 GitHub OAuth Login
Currently email/password only. Every developer expects "Sign in with GitHub."

**What to build:**
- GitHub OAuth login button on `/login` and `/register`
- Auto-populate name, email, avatar from GitHub
- Link to existing account if same email exists

**Why it matters:** It's a trust signal and reduces friction. GitHub is where your buyers live.

#### 5.4 Notifications & Alerts
Currently no way to notify a developer that their approval is needed.

**What to build:**
- Email notifications: run awaiting approval, run failed, run completed
- Slack webhook integration (one-click setup in Settings)
- In-app notification bell with unread count
- `notifications` DB table (user_id, type, payload, read_at)

**Why it matters:** The approval gate is your biggest differentiator. It's worthless if reviewers miss it.

---

### Horizon 2 — Platform Stickiness (3–6 months)
*Goal: Users can't leave because too much of their workflow lives here.*

#### 5.5 ROI & Productivity Analytics
The #1 question every engineering manager will ask: *"How much time did this save?"*

**What to build:**
- Per-run: time from ticket open → PR merged vs. team average
- Per-project: tickets shipped per week (AI vs. manual baseline)
- Per-agent: success rate, avg tokens used, avg run time
- Org-wide: estimated hours saved, estimated cost saved (at $X/engineer-hour)
- Exportable reports (PDF / CSV)
- Weekly digest email to org admins

**Why it matters:** This is your renewal and upsell story. If you can show "we saved your team 40 hours last month," you never churn.

#### 5.6 Run Quality & Feedback Loop
Currently runs are binary (pass/fail). No way to improve agents over time.

**What to build:**
- Per-run feedback: thumbs up/down on agent output quality
- Reviewer comment on PR diff becomes training signal (stored in `run_feedback` table)
- "Replay" a failed run with different agent config
- Agent performance score (success rate, avg review cycles)
- Skill effectiveness rating (which skills produce the best code?)

**Why it matters:** This starts building your data moat. The platform gets smarter the more it's used.

#### 5.7 Linear & GitLab Integrations
Jira is enterprise but slow. Linear is the darling of fast-growing startups. GitLab is the GitHub alternative for enterprise.

**What to build:**
- Linear connection type (OAuth, project sync, ticket sync)
- GitLab connection type (OAuth, repo access, PR creation)
- `connection.type` enum: `github | gitlab | jira | linear`
- Abstract the "ticket source" and "repo host" interfaces in the agent layer

**Why it matters:** Expands TAM. Linear shops can't use you today. GitLab shops (often larger enterprise) can't use you today.

#### 5.8 Agent Templates & Skill Library
Right now, users start from scratch. That's a long time-to-value.

**What to build:**
- Built-in skill library: 20+ pre-written skills across categories (frontend, backend, testing, security, docs)
- Agent templates: "Standard Web Dev Agent", "Python Backend Agent", "React Frontend Agent"
- Pod templates: "Standard 4-Agent SDLC", "Solo Dev Agent", "Code Review Only"
- One-click "Import template" on Skills/Agents/Pods pages
- Public skill library page (marketing + growth)

**Why it matters:** Reduces time-to-first-run from hours to minutes. Critical for self-serve growth.

#### 5.9 PR Review Agent (New Agent Type)
The missing 5th agent: code review before human approval.

**What to build:**
- `reviewer` agent role in the pod builder
- Agent node that reads the PR diff and posts structured review comments to GitHub
- Scores the PR on: test coverage, edge cases missed, security issues, style violations
- Blocks approval until reviewer agent passes (configurable threshold)
- Surfaces review findings in RunDetailPage

**Why it matters:** This makes the product defensible against "just use GitHub Copilot PR review" — your review agent is trained on YOUR skills and YOUR coding standards, not generic ones.

---

### Horizon 3 — Moat Builders (6–12 months)
*Goal: Create structural advantages that are hard to copy.*

#### 5.10 Skill Marketplace
The App Store moment for AI development agents.

**What to build:**
- Public marketplace at `/marketplace`
- Any user can publish a skill (version-controlled, semantic versioned)
- Skills can be: free / premium (paid, creator gets revenue share)
- Skill ratings, downloads, fork count
- "Install skill" → adds to your org's skill library
- Skill bundles: "Rails Full-Stack Bundle", "FastAPI + Postgres Bundle"
- Creator revenue share: 70/30 split (platform/creator)

**Why it matters:** This is your network effect. More users → more skills published → more value for new users → more users. Once a skill has 500 installs, the creator has no reason to port it to a competitor.

#### 5.11 Agentic Memory & Codebase Intelligence
Currently each run starts cold. The agents don't know anything about your codebase.

**What to build:**
- On project onboarding, index the repo: file structure, key patterns, test conventions, API patterns
- Store as vector embeddings (pgvector extension on Postgres)
- Each run: retrieve relevant context chunks before agent execution
- "Codebase memory" panel in ProjectDetailPage — shows what the agents know
- Memory update on each merged PR (agents learn from what was approved)

**Why it matters:** This is your deepest moat. After 6 months of runs on a codebase, the agents understand the project better than any new hire. Switching platforms means losing all that learned context.

#### 5.12 Self-Hosted / Private Cloud Deployment
Enterprise won't send code to your SaaS. They need to run it in their VPC.

**What to build:**
- Docker Compose "enterprise" bundle (everything self-contained)
- Helm chart for Kubernetes deployment
- Bring-your-own LLM support: OpenAI, Azure OpenAI, local Ollama
- License key validation (phone-home or air-gapped)
- Enterprise settings: SSO (SAML/OIDC), custom domain, IP allowlist
- Dedicated Slack channel for enterprise support

**Why it matters:** Enterprise contracts are $50K–500K/yr. They won't sign without self-hosted. This tier alone can be your Series A story.

#### 5.13 RBAC & Compliance Controls
**What to build:**
- Fine-grained permissions: who can create agents, run tickets, approve deployments, view audit logs
- Role templates: Owner / Lead Engineer / Developer / QA / Viewer
- Approval policies: require 2 approvers for production deploys
- Deploy environment controls: block direct production runs without approval policy
- SOC 2 Type II audit evidence export
- Data retention policies (auto-delete runs older than N days)

**Why it matters:** The approval gate is already built. This makes it enterprise-grade and compliance-ready.

---

### Horizon 4 — Category Creation (12–18 months)
*Goal: Own the category. "AI Dev Ops" or "Agentic Engineering Platform."*

#### 5.14 AI Sprint Planner (Jira/Linear Bi-Di Sync)
Currently tickets come from Jira. But sprint planning itself is manual.

**What to build:**
- AI sprint planning: given a backlog of tickets, suggest sprint composition based on agent capacity, complexity estimates, and team velocity
- Complexity scoring per ticket (agent estimates story points)
- Automatic dependency detection between tickets
- Sprint health dashboard: on-track / at-risk / blocked
- Write estimates back to Jira/Linear

#### 5.15 Multi-Environment Deploy Pipelines
Dev → Staging → Production progression with environment-specific agent configs.

**What to build:**
- `deploy_targets` JSONB already exists — build the UI and agent logic around it
- Environment-gated approval policies (staging auto-approve, production requires 2 humans)
- Rollback automation: if prod monitoring detects spike, trigger rollback run
- Deploy history timeline per environment

#### 5.16 IDE Extension (VS Code)
Bring the run stream into the developer's daily environment.

**What to build:**
- VS Code extension that shows live run steps in a sidebar panel
- "Assign to AI" right-click on a Jira ticket in the IDE
- Diff viewer inside VS Code (not just the web UI)
- Approve/reject from inside the IDE

#### 5.17 AI Code Archaeology ("Why was this written this way?")
A reverse feature: given a file or function, explain the full history of decisions that led to it — which runs wrote it, which skills were used, which human approved it.

**What to build:**
- Per-line Git blame linked back to the run that wrote it
- "Explain this code's origin" button in the web UI
- Run → file → skill traceability chain

---

## 6. Business Model

### Pricing Tiers

| Tier | Price | Includes | Target |
|---|---|---|---|
| **Starter** | Free | 1 user, 10 runs/month, 1 project | Individual devs, evaluation |
| **Team** | $149/month | 10 seats, 100 runs/month, 5 projects, Slack alerts, email support | Small startup (5–20 devs) |
| **Growth** | $499/month | 30 seats, 500 runs/month, unlimited projects, ROI dashboard, priority support | Series A startup (20–100 devs) |
| **Enterprise** | Custom (~$3–20K/month) | Unlimited + self-hosted option, SSO, RBAC, compliance, SLA, dedicated CSM | Enterprise engineering orgs |

### Revenue Levers
1. **Seat expansion** — Orgs buy more seats as they onboard more teams
2. **Run credits** — Overages billed at $0.50/run beyond plan limit
3. **Marketplace cut** — 30% of premium skill revenue
4. **Enterprise contracts** — Multi-year, high ACV, self-hosted premium
5. **LLM pass-through** — Option to use customer's own API key (no margin) vs. platform-provided (markup)

### Unit Economics (illustrative)
- LLM cost per run (avg): ~$0.30–0.80 (using Claude Sonnet at current pricing)
- At $149/month for 100 runs: ~$0.30 cost per run included → ~65–80% gross margin
- Enterprise self-hosted: nearly 100% gross margin (no LLM cost)
- Target gross margin at scale: **75–85%**

---

## 7. Design Partner Strategy (Before Raising)

You do not need 1,000 users to raise pre-seed. You need 3–5 deeply engaged design partners.

**Target profile:**
- B2B SaaS startup, Series A or B
- 5–30 engineers
- Already using GitHub + Jira/Linear
- Feeling the pain of slow ticket throughput or expensive engineering capacity

**What you offer them:**
- Free access for 3 months
- Direct Slack access to founders
- Their specific use case built into the product roadmap
- Co-marketing (case study, logo on website)

**What you get:**
- Real usage data
- Testimonials and metrics ("shipped 3x more tickets", "saved 40 hrs/month")
- Letters of intent / pilot-to-paid conversions
- Proof of retention over multiple weeks

---

## 8. The Investment Narrative

### Pre-Seed Deck Story Arc

**Slide 1 — The Problem:**
Engineering teams are drowning in tickets. Hiring is expensive, slow, and uncertain. AI tools exist but they either assist (Copilot) or go rogue (Devin). Neither is safe for production.

**Slide 2 — The Market:**
$20B+ AI developer tools market. Every engineering team will run AI agents on their codebase within 3 years. The question is who controls them.

**Slide 3 — The Product:**
[Demo video: ticket goes in, agents run, PR appears, human approves, deploys] You define the rules. AI executes. Humans stay in control.

**Slide 4 — Why We're Different:**
| | Copilot | Devin | Us |
|---|---|---|---|
| Unattended runs | No | Yes | Yes |
| Configurable behavior | No | No | Yes |
| Human approval gate | No | No | Yes |
| Audit trail | No | No | Yes |
| Multi-agent pipelines | No | No | Yes |

**Slide 5 — Traction:**
[Design partners, runs executed, time saved metrics]

**Slide 6 — Business Model:**
$149–499/month SaaS, enterprise custom. 75%+ gross margin.

**Slide 7 — The Ask:**
$X pre-seed. Use of funds: 3 engineers × 12 months, design partner program, first marketing.

---

## 9. The Three Numbers to Track From Day One

These are the metrics investors will ask for at every conversation:

| Metric | Why It Matters | Target at Raise |
|---|---|---|
| **Weekly Active Orgs** | Measures retention, not just signups | 5+ orgs with runs every week |
| **Runs per Org per Week** | Usage intensity — are they actually using it? | 10+ runs/org/week |
| **Time Ticket → Merged PR** | The ROI story. Faster = more value. | Under 4 hours avg for medium complexity |

---

## 10. Prioritized 90-Day Plan

If you can only do one thing at a time, do it in this order:

| Week | Priority | Why |
|---|---|---|
| 1–2 | GitHub OAuth login | Removes friction for target users |
| 3–4 | Multi-user / Org model | Unlocks team purchases |
| 5–6 | Email notifications (approval alerts) | Makes approval gate actually work |
| 7–8 | Stripe billing (Team tier only) | First revenue signal |
| 9–10 | 3 design partners onboarded | Real usage data |
| 11–12 | ROI dashboard (runs saved, time saved) | Retention + upsell story |

After 90 days you will have: an org model, a billing system, real users, and a metric that shows value. That is a raiseable pre-seed story.

---

## 11. The Platform Vision (18-Month Horizon)

In 18 months, Agentic SDLC becomes the **control plane for AI-augmented engineering teams**:

- Every engineering org has a "pod" that handles routine tickets autonomously
- Senior engineers define the rules once (in skills + agent config) and the platform runs thousands of tickets
- The platform knows more about your codebase than any individual developer (memory layer)
- The skill marketplace has 500+ community-contributed skills covering every stack
- Enterprise orgs run it inside their VPC, compliant with SOC 2, HIPAA, ISO 27001

The category you're creating: **Agentic Engineering Operations (AEO)** — the layer between your project management tools and your codebase where AI turns plans into shipped code, governed by humans.

---

*Document prepared: July 2026*  
*Platform version: v1.0 (Phases 1–10 complete)*
