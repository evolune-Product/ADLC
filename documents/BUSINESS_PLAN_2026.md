# ADLC / Agentic SDLC — Business Plan

**Version 2.0 · August 2026** · Supersedes the pricing and roadmap sections of `PRODUCT_STRATEGY.md`
Companion research: [`MARKET_AND_COMPETITIVE_RESEARCH_2026.md`](./MARKET_AND_COMPETITIVE_RESEARCH_2026.md)

---

## 1. The business in one page

| | |
|---|---|
| **What** | The governed execution layer for AI software delivery: ticket → plan → code → review → **human approval** → multi-env deploy, with policy, audit and per-run cost attribution |
| **Who buys** | VP/Head of Engineering or Platform lead at a 20–500-engineer software org already running 2+ AI coding tools |
| **Why now** | 97% of enterprises use AI coding; review time is up 91%; governance is the ROI multiplier; EU AI Act Art. 50 lands 2 Aug 2026 |
| **Why us** | Skills (behaviour-as-markdown) × Pods (ordered multi-agent pipelines) × Policies (who approves what) × Memory (per-codebase learning) — none of the funded competitors ship all four |
| **Business model** | Hybrid: platform fee per governed seat **+ metered runs**, with LLM cost pass-through or BYO-key |
| **Wedge** | The **approval gate with teeth**: reviewer-agent score thresholds + N-approver policy + immutable evidence |
| **Moat over time** | Org skill library → codebase memory → run history → compliance evidence. All three compound and none are portable to a competitor |

---

## 2. Pricing

Designed against the 2026 reality that per-seat is collapsing (21%→15%) and hybrid base+usage is now 41% of SaaS. Anchors: Devin ≈ $9/agent-hour, GitHub agent session $6–12, standalone AI review $24–30/dev/mo, Tabnine agentic tier $59/user.

| Tier | Platform fee | Included runs | Overage | Seats | Key gates |
|---|---|---|---|---|---|
| **Free** | $0 | 25 runs/mo | — (hard stop) | 1 | 1 project, community skills, BYO-LLM key required |
| **Team** | **$199/mo** | 250 runs | **$0.60/run** | 10 incl., $12/extra | Slack + email alerts, policies, reviewer agent, ROI dashboard |
| **Growth** | **$699/mo** | 1,000 runs | **$0.45/run** | 30 incl., $10/extra | Codebase memory, marketplace, multi-env pipelines, API + webhooks, SSO |
| **Enterprise** | from **$3,500/mo** (typ. $40–250K/yr) | Custom | Committed-use | Unlimited | Self-hosted/VPC, BYO-LLM, SAML/SCIM, RBAC, 2-approver policies, evidence export, SLA, named CSM |

**Rationale for the changes vs. v1 ($149/$499):**
- v1 gave 100 runs for $149 = $1.49/run of *revenue* against $0.30–0.80 of LLM cost — a 46–80% margin that collapses on heavy users. v2 sets the included-run price at **$0.80/run** (Team) and **$0.70/run** (Growth) with overages priced *above* worst-case token cost, so heavy usage is accretive rather than dilutive.
- Seats are priced but not the primary meter: they gate *governance* (who can approve, who can see audit), which is what enterprises actually buy.
- Free tier requires BYO-LLM key → zero marginal COGS on the acquisition funnel.

**Additional revenue lines**
1. **Marketplace** — 30% of paid skill/template revenue (creator keeps 70%).
2. **LLM margin** — platform-provided key at ~25% markup, or 0% with BYO-key (enterprise expects BYO).
3. **Self-hosted license** — annual license key, near-100% gross margin (no inference cost borne).
4. **Compliance pack** — evidence export + retention + audit assistance as a $X/yr enterprise add-on.

---

## 3. Unit economics

**Cost per run** (Claude Sonnet-class, measured envelope): sprint plan ~8K in / 2K out, dev ~25K in / 8K out, review ~30K in / 4K out, QA ~10K in / 2K out.

| Scenario | LLM cost | Infra | Total COGS | Team price | Gross margin |
|---|---|---|---|---|---|
| Simple ticket | $0.18 | $0.02 | **$0.20** | $0.80 | **75%** |
| Median ticket | $0.42 | $0.03 | **$0.45** | $0.80 | **44%** |
| Complex + 2 dev retries | $1.10 | $0.05 | **$1.15** | $0.80 | **−44%** ⚠ |
| Median, BYO-key | $0.00 | $0.03 | **$0.03** | $0.80 | **96%** |

**Three controls make this safe** (all implemented):
1. **Per-run budget cap** — a run aborts when projected token spend exceeds the plan's per-run ceiling.
2. **Retry cap** — dev retries are bounded (default 2) and each retry is metered.
3. **BYO-key** — pushes the tail-risk scenario to the customer; enterprises prefer it anyway.

**Blended target:** 72–80% gross margin at Team/Growth, >90% on self-hosted.

**Customer economics (Team, 15-engineer team):** $199 + ~150 overage runs × $0.60 = **$289/mo ≈ $3,470/yr**. Against one engineer-week saved per month at a $120K loaded salary (~$2,300/week), payback is ~1.2 months of a single week's saving. That is the ROI sentence for the deck, and the dashboard computes it from real run data rather than assertion.

---

## 4. Financial model (base case, conservative)

| | M0–3 | M4–6 | M7–9 | M10–12 | M13–18 |
|---|---|---|---|---|---|
| Design partners (free) | 3 | 5 | 5 | 5 | 5 |
| Paying teams | 0 | 4 | 12 | 25 | 60 |
| Enterprise pilots | 0 | 0 | 1 | 2 | 5 |
| MRR | $0 | ~$1.1K | ~$4.2K | ~$11K | ~$38K |
| ARR exit | — | $13K | $50K | **$132K** | **$456K** |
| Burn (2 FTE + infra) | $9K/mo | $12K/mo | $14K/mo | $16K/mo | $28K/mo |

**Milestone gates**
- **Pre-seed ready (M6):** 5 design partners, 3 paying, LOIs — matches the 2026 pre-seed bar of $5–20K ARR or credible LOIs.
- **Seed ready (M12–15):** **$300–500K ARR** run-rate, NDR >120%, ≥10 runs/org/week.
- **Series A (M24):** $1–3M ARR, 2+ enterprise contracts >$50K, self-hosted GA.

---

## 5. The three numbers, instrumented

| Metric | Target at raise | Where it now comes from |
|---|---|---|
| Weekly Active Orgs (orgs with ≥1 run) | 5+ | `GET /analytics/summary` |
| Runs per org per week | 10+ | `GET /analytics/summary` |
| Ticket → merged PR (median) | <4h medium complexity | `GET /analytics/cycle-time` |
| *(added)* Approval latency | <2h | `GET /analytics/summary` — the gate is worthless if it stalls delivery |
| *(added)* Cost per merged PR | <$3 | `GET /analytics/cost` — the CFO metric |
| *(added)* Agent success rate | >70% first-pass | `GET /analytics/agents` — the quality metric competitors can't show |

---

## 6. Go-to-market

**Phase 1 — Design partners (M0–4).** 5 partners, 20–80 engineers, GitHub + Jira/Linear, already running ≥2 AI tools. Offer: free for 3 months, direct founder access, their workflow on the roadmap, co-marketed case study. Ask: weekly usage, a testimonial with a number, pilot-to-paid intent.

**Phase 2 — Self-serve funnel (M4–9).** Free tier with BYO-key → the skill/template marketplace is the top of funnel (public, SEO-indexable, no signup to browse). Content: "governed agent runs" comparison pages, EU AI Act readiness guides, per-run cost benchmarks. Motion is bottom-up to the platform/DevEx lead.

**Phase 3 — Enterprise (M9–18).** Self-hosted bundle + SSO + RBAC + evidence export. Land via a single pod on one repo, expand by repo and by team. Sell alongside — never against — Copilot/Cursor: *"keep your assistants, govern the unattended work."*

**Channels that fit this product:** Jira/Atlassian Marketplace listing, GitHub Marketplace app, MCP server registry, ISO 42001/SOC2 consultancy referrals. Channels that don't: paid search against Cursor/Copilot (unwinnable CAC).

---

## 7. Product strategy — what was built and why

The implementation shipped with this plan closes every gap an investor probes. Mapping:

| Investor question | Feature shipped | Endpoint / surface |
|---|---|---|
| "Who pays and how?" | Plans, subscriptions, metered runs, quota enforcement, Stripe checkout/portal/webhooks | `/billing/*`, `BillingPage` |
| "Can a team use it?" | Orgs, roles, invitations *(pre-existing)* + approval policies with N-approver rules | `/policies/*`, `PoliciesPage` |
| "What stops a rogue agent?" | Policy engine: min approvers, reviewer score threshold, protected paths/branches, env gating, budget caps | `app/services/policy_service.py` |
| "What's the moat?" | Skill/agent/pod templates, marketplace with installs+ratings, codebase memory (embeddings) | `/templates/*`, `/marketplace/*`, `/memory/*` |
| "Show me ROI" | Analytics: cycle time, cost/run, hours saved, agent success rates, CSV export | `/analytics/*`, `AnalyticsPage` |
| "Does it improve?" | Run feedback loop feeding agent scorecards | `/runs/{id}/feedback`, `/analytics/agents` |
| "Model lock-in?" | Provider abstraction: Anthropic / OpenAI / Azure / Bedrock / Ollama, per-org BYO-key | `app/services/llm_service.py` |
| "Will my CISO allow it?" | Immutable audit, retention policy, evidence export, API keys with scopes, signed webhooks, self-hosted compose | `/compliance/*`, `/apikeys/*`, `/webhooks/*` |
| "Beyond GitHub/Jira?" | GitLab + Linear connectors behind provider interfaces | `app/services/{gitlab,linear}_service.py` |
| "Interop?" | MCP server exposing runs/approvals as tools | `app/mcp_server.py` |

---

## 8. Risks and honest mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| GitHub/Atlassian absorb the category | **High** | Cross-platform by construction; ship the MCP server so ADLC is the engine *behind* their agents; own Jira↔GitLab and Linear↔GitHub combinations they will never prioritise |
| No users yet — everything above is a hypothesis | **High** | Design-partner program is the only M0–M4 priority; product work is now sufficient |
| LLM cost spike or model price change | Medium | BYO-key default at enterprise; per-run caps; provider abstraction lets pricing arbitrage happen in a config file |
| Agent writes bad code that gets merged | Medium | Reviewer agent + score threshold + human gate + protected paths + rollback records |
| Solo-founder bandwidth | **High** | The single-product focus rule: this is the one bet; everything else pauses |
| Marketplace stays empty | Medium | Seed with 20+ first-party skills (built); creators recruited from design partners |
| Enterprise sales cycle (6–9 mo) longer than runway | High | Self-serve tiers fund the wait; enterprise is upside, not plan |

---

## 9. 12-month operating plan

| Quarter | Focus | Definition of done |
|---|---|---|
| **Q1 (M1–3)** | Deploy + 5 design partners | Production URL, Stripe live, 5 orgs with ≥10 runs each |
| **Q2 (M4–6)** | Convert to paid; measure | 3+ paying teams, ROI dashboard cited in a testimonial with a number |
| **Q3 (M7–9)** | Self-serve + marketplace | 50 signups/mo organic, 20 published skills, first Growth-tier customer |
| **Q4 (M10–12)** | Enterprise readiness | Self-hosted install at 1 pilot, SSO, SOC 2 Type I kicked off, $130K ARR |

---

## 10. The ask (if raising)

**$750K–1.2M pre-seed** at a $6–10M post (below the ~$17.9M AI median — deliberately, to keep the round small and fast).
**Use of funds:** 2 engineers × 18 months (60%), design-partner + GTM (20%), infra/LLM credits (12%), SOC 2 + legal (8%).
**Milestone bought:** $300–500K ARR and 25+ paying teams = a fundable seed on 2026 benchmarks.
