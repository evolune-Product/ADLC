# ADLC / Agentic SDLC — Deep Market & Competitive Research

**Prepared:** August 2026 · **Horizon:** 2026 → 2028
**Method:** Web research across analyst notes (Forrester, Gartner citations), vendor pricing pages, funding announcements, benchmark leaderboards, regulatory texts and practitioner surveys. Every non-obvious number is sourced inline. Figures from secondary aggregators are marked as such — analyst market sizings disagree by 2× depending on scope, so ranges are given rather than a single number.

---

## 0. Executive Summary — the eight findings that matter

1. **The category now has an analyst name.** Forrester launched *The Agentic Development Platforms (ADP) Landscape, Q3 2026* covering **25 vendors**, defining ADPs as "software development platforms that use agentic AI to help teams build software of all kinds." Crucially, Forrester says differentiation has moved **off code generation** and onto *orchestration, enterprise context, governance, model agility, cost transparency, code ownership/auditability, and human oversight*. That list is, almost line for line, what this codebase already implements. ([Forrester](https://www.forrester.com/blogs/launching-the-agentic-development-platforms-vendor-landscape-q3-2026/))
2. **The money is real but the seat model is dying.** AI coding tools produced ~**$12.8B revenue in 2026**, up from $5.1B in 2024; per-seat pricing fell from 21% → 15% of SaaS in twelve months while **hybrid base+usage hit 41% adoption**. A pure $/seat plan is now a *positioning liability*, not a simplification. ([Exceeds](https://blog.exceeds.ai/ai-coding-us-market-share/), [Monetizely](https://www.getmonetizely.com/blogs/the-2026-guide-to-saas-ai-and-agentic-pricing-models))
3. **The bottleneck moved from writing code to trusting it.** Faros AI found **review time rose 91%** on high-AI-adoption teams; 46% of developers distrust AI output and 66% cite "almost right but not quite" as their top frustration. The scarce resource in 2026 is *review and governance capacity*, not code volume. ([Forrester](https://www.forrester.com/blogs/agentic-software-development-takes-the-lead-from-code-assistants-to-orchestrated-sdlc-agents/), [Black Duck study via PRNewswire](https://www.prnewswire.com/news-releases/ai-coding-hits-97-enterprise-adoption-new-black-duck-study-shows-governance-is-the-roi-multiplier-302794103.html))
4. **Governance is the ROI multiplier, and buyers now say so out loud.** Black Duck's 2026 study puts enterprise AI-coding adoption at **97%** and frames governance as the multiplier on returns. Enterprise procurement increasingly asks for AI-governance evidence *before* signing. ([PRNewswire](https://www.prnewswire.com/news-releases/ai-coding-hits-97-enterprise-adoption-new-black-duck-study-shows-governance-is-the-roi-multiplier-302794103.html))
5. **Well-funded incumbents are converging on this space from three directions**: agent vendors adding governance (Factory $150M @ $1.5B; Devin/Cognition; OpenHands' "Agent Control Plane"), platform owners adding orchestration (GitHub **Agent HQ / Mission Control**, Atlassian **Agents in Jira**), and measurement vendors adding policy (Faros, LinearB gitStream, DX-inside-Atlassian).
6. **Nobody owns "the approval gate + skill-defined behaviour + audit trail" as the product.** Everyone has *a* piece: GitHub has multi-agent orchestration without configurable agent behaviour; OpenHands has a control plane without ticket→deploy loop; Faros has measurement without execution; CodeRabbit/Greptile have review without the run. The wedge is real but narrow, and it closes in roughly **12–18 months**.
7. **Regulatory tailwind starts now.** EU AI Act **Article 50 transparency obligations apply from 2 August 2026**; high-risk regimes land Dec 2027 / Aug 2028. ISO/IEC 42001 is becoming the procurement baseline (Augment Code certified in May 2025 as a marketing wedge). An audit-log-and-approval-native platform sells into that. ([artificialintelligenceact.eu](https://artificialintelligenceact.eu/), [Augment](https://www.augmentcode.com/guides/eu-ai-act-2026))
8. **Strategic conclusion:** do **not** compete on autonomy or model quality. Compete as the **governed execution layer** — the thing that decides *which* agent may touch *what*, under *whose* approval, at *what* cost, with *what* evidence. Sell the control plane; stay model-agnostic and agent-agnostic on purpose.

---

## 1. Market sizing (ranges, with scope caveats)

| Scope | 2026 | Forward | CAGR | Source |
|---|---|---|---|---|
| AI coding tools revenue (actual, aggregated) | **$12.8B** (from $5.1B in 2024) | — | — | [Exceeds](https://blog.exceeds.ai/ai-coding-us-market-share/) |
| "AI code tools" market | $9.35–9.46B | $22.2B by 2030 / $29.96B by 2031 | 23.8–26.2% | [Mordor](https://www.mordorintelligence.com/industry-reports/artificial-intelligence-code-tools-market) |
| "AI code generation + developer assistant" | $16.13B | $78.97B by 2031 | **37.4%** | [Mordor](https://www.mordorintelligence.com/industry-reports/ai-code-generation-and-developer-assistant-market) |
| Coding-**agent** sub-segment | — | — | **52.1%** | MarketIntelo via [Software Strategies](https://softwarestrategiesblog.com/2026/02/26/roundup-of-agentic-ai-forecasts-and-market-estimates-2026/) |
| Agentic AI (all uses) | $9.14–10.86B | — | — | [Tech-Insider](https://tech-insider.org/agentic-ai-enterprise-2026-market-analysis/) |
| Departmental AI spend on *coding* | $4.0B (2025) = **55% of all departmental AI spend** | — | — | [Software Strategies](https://softwarestrategiesblog.com/2026/02/26/roundup-of-agentic-ai-forecasts-and-market-estimates-2026/) |

**Reading it honestly:** the wide spread (9.35 vs 16.13 for the "same" year) is a scope artefact — the larger number folds in IDE assistants and platform-bundled AI. What is *not* in dispute: coding is the single largest line item of enterprise AI spend, and the agentic slice is compounding ~2× faster than the assistant slice.

### Serviceable market for a governance-layer product
- Bottom-up: ~**every org running ≥2 coding agents** needs orchestration + policy. Practitioner reports say most engineering orgs in 2026 run **three or four AI coding tools simultaneously** ([MarkTechPost](https://www.marktechpost.com/2026/06/10/ai-coding-agents-development-platforms-2026/)) — that fragmentation *is* the demand signal for a control plane.
- Gartner: **60% of enterprise AI rollouts will include agentic capabilities by end-2026**, and **40% of enterprise applications will embed task-specific agents by end-2026** (from <5% in 2025). ([Gartner via Ciklum](https://www.ciklum.com/blog/ai-revolutionize-software-development-lifecycle/), [Gartner via Augment](https://www.augmentcode.com/tools/13-best-ai-coding-tools-for-complex-codebases))
- CrewAI's 2026 survey: **100% of surveyed enterprises plan to expand agentic AI in 2026**; ~75% call it a critical priority. ([BusinessWire](https://www.businesswire.com/news/home/20260211693427/en/Agentic-AI-Reaches-Tipping-Point-100-of-Enterprises-Plan-to-Expand-Adoption-in-2026-New-CrewAI-Survey-Finds))

---

## 2. Demand-side truth: what actually hurts in 2026

| Symptom | Evidence | Implication for ADLC |
|---|---|---|
| Review capacity is the new constraint | Review time **+91%** on high-adoption teams (Faros AI) | The Reviewer agent + approval gate is the *product*, not a feature |
| Trust deficit | **46%** of devs distrust AI output; **66%** say "almost right but not quite" | Ship evidence: diffs, findings, test results, score thresholds |
| Adoption is saturated, governance is not | **97%** enterprise adoption of AI coding; governance framed as ROI multiplier | Sell to the person accountable for the blast radius, not the IDE user |
| Cost opacity | Agentic sessions ≈ **1000× tokens** of single-turn; one GitHub agent session costs **$6–12+** | Per-run cost attribution is a buying criterion, not a nicety |
| Tool sprawl | 3–4 concurrent agent tools per org | Be the neutral layer above them; never force a single agent |
| Regulatory pressure | EU AI Act Art. 50 from **2 Aug 2026**; ISO 42001 becoming baseline | Compliance export = enterprise unlock |

---

## 3. Competitive landscape

### 3.1 The map (four blocks, not one)

```
                         GOVERNED / AUDITABLE
                                  ▲
   Faros AI · Jellyfish · LinearB │  ★ ADLC (Agentic SDLC)
   DX (Atlassian)                 │  OpenHands Enterprise
   ── measure, don't execute ──   │  Tabnine Agentic · Cody Enterprise
                                  │
◀── NARROW SCOPE ─────────────────┼───────────────── FULL SDLC LOOP ──▶
                                  │
   CodeRabbit · Greptile · Qodo   │  Devin (Cognition) · Factory Droids
   Copilot autocomplete           │  GitHub Agent HQ · Claude Code · Cursor
   ── review or write, one step ──│  ── execute, thin governance ──
                                  ▼
                          UNGOVERNED / OPAQUE
```

### 3.2 Direct competitors — full-loop agent platforms

| Vendor | Funding / scale | Pricing (2026) | Strengths | Exploitable gaps |
|---|---|---|---|---|
| **Devin — Cognition** | Acquired Windsurf (Jul 2025) | Core $20 + **$2.25/ACU**; **Team $500/mo** ≈ 250 ACU ≈ 62.5 agent-hours; Enterprise custom + VPC | Brand, parallel sub-agents, sandboxed cloud | ACU billing is opaque to finance; configurability of *agent behaviour* is thin; approval policy not first-class ([Devin pricing](https://www.usecarly.com/blog/devin-pricing/), [Cognition plans](https://www.eesel.ai/blog/cognition-ai-pricing)) |
| **Factory.ai (Droids)** | **$150M Series C @ $1.5B**, Apr 2026, Khosla-led (Sequoia, Blackstone, Insight, NEA); ~$220M total | Enterprise, custom | Morgan Stanley, EY, Nvidia, Adobe, Palo Alto Networks, Adyen, MongoDB, Bayer, Zapier; full-SDLC ambition | Enterprise-only motion → no self-serve wedge; the *skill/pod* configuration primitive isn't their story ([CryptoBriefing](https://cryptobriefing.com/factory-ai-150m-series-c-funding/), [Idlen](https://www.idlen.io/news/factory-ai-150-million-1-5-billion-droids-coding-agents-enterprise-april-2026/)) |
| **GitHub Agent HQ + Mission Control** | Microsoft | Requires paid Copilot: Pro **$10**, Pro+ **$21**, Business **$19/user**, Enterprise **$39/user**; usage-based **AI Credits since 1 Jun 2026** (1 credit = $0.01) | Distribution; runs Copilot + Claude + Codex side by side; compare PRs from multiple agents | Locked to GitHub; no Jira-native loop; governance = repo permissions, not policy-as-config; costs balloon ($6–12+/session) ([Fundesk](https://www.fundesk.io/github-agent-hq-multi-agent-development-guide), [UsageBox](https://usagebox.com/articles/github-copilot-usage-based-billing-2026)) |
| **OpenHands (All Hands AI)** | **$23.8M** raised; **70K+ GitHub stars**; 72–72.8% SWE-bench Verified | OSS free (MIT, BYO-LLM); Enterprise custom — VPC/K8s, **Agent Control Plane, SAML/SSO, RBAC, budget enforcement, usage reporting** | The credible open-source enterprise contender; already ships the control-plane vocabulary | Agent-centric, not lifecycle-centric: no ticket→sprint-plan→PR→multi-env deploy chain, no Jira/Linear system-of-record loop ([AgentMarketCap](https://agentmarketcap.ai/blog/2026/04/06/openhands-open-source-coding-agent-allhands-ai-series-a-swe-bench)) |
| **Cursor (Anysphere)** | ~**$4B ARR** est. 2026; **26% market share**; **acquired by SpaceX for $60B**, signed 16 Jun 2026, closing Q3 pending approval | Seat + usage | Fastest SaaS ramp in history; 64% of Fortune 500 | IDE-centric — assists a human at a keyboard; unattended, policy-bound runs are not the product; acquisition creates enterprise-procurement uncertainty ([TNW](https://thenextweb.com/news/cursor-anysphere-2-billion-funding-50-billion-valuation-ai-coding), [Getlatka](https://getlatka.com/companies/cursor.com)) |
| **Claude Code (Anthropic)** | ~13% share (May 2026) | Seat/usage | Best-in-class model; terminal+IDE+web | Deliberately a tool, not a governance platform — complements ADLC rather than replacing it |

### 3.3 Adjacent — review-only vendors (they own the step ADLC must beat)

| Vendor | Price | Notes |
|---|---|---|
| **CodeRabbit** | **$24/dev/mo** annual ($30 monthly); Pro+ **$48** adds unit-test generation | Signal-to-noise leader |
| **Greptile** | **$30/seat**, 50 reviews included; free starter | **Series A led by Benchmark at $180M valuation (2026)** |
| **Qodo** | **$30/user** (Teams) | Multi-agent review + Qodo Cover test generation |
| **Macroscope** | usage-based ≈ **$0.95/review** | Proof that per-unit review pricing clears the market |

Sources: [Levelop](https://levelop.dev/blog/best-ai-code-review-tools-2026-coderabbit-greptile-qodo-compared), [Stork](https://www.stork.ai/blog/best-ai-code-review-tools-2026).

**Read:** a standalone AI review costs $24–30/dev/month or ~$1/review. ADLC's Reviewer agent must be *bundled* — priced as part of the run, not as a line item — or it loses on price to specialists.

### 3.4 Adjacent — context/enterprise assistants

| Vendor | Price | Notable |
|---|---|---|
| **Sourcegraph Cody** | **$59/user/mo**, enterprise-only (free/Pro discontinued); Amp free | Pre-indexing + vector embeddings for multi-repo context |
| **Tabnine** | Code Assistant **$39/user**; **Agentic Platform $59/user** | Prices the "agentic" tier at a **51% premium** over assistant |
| **Augment Code** | Enterprise | **First AI coding assistant certified ISO/IEC 42001** (May 2025) — compliance as a wedge; context engine spanning 400–500K files |

([WeavAI](https://weavai.app/blog/en/2026/04/30/sourcegraph-cody-review-2026-enterprise-ai-at-59-mo/), [Augment](https://www.augmentcode.com/tools/best-enterprise-ai-code-generators))

### 3.5 Adjacent — engineering intelligence (the ROI narrative owners)

**Faros AI** (AI-coding ROI across 22,000 developers), **Jellyfish** (AI Impact module), **LinearB** (gitStream policy engine — closest to "policy" of the three), **DX** — **acquired by Atlassian for $1B in late 2025**, now wired into Jira/Bitbucket/Compass. ([Cortex](https://www.cortex.io/post/engineering-intelligence-platforms-definition-benefits-tools), [Jellyfish](https://jellyfish.co/blog/faros-ai-alternatives/))

**Why this matters more than it looks:** these vendors own the CFO conversation ("what did AI actually save us?") but cannot execute work. ADLC generates the ground-truth event stream they resell — ticket → plan → PR → review → approval → deploy, with timestamps and cost. **ADLC should emit its analytics as a first-class product surface *and* an export**, or Faros/Jellyfish will own the value narrative for work ADLC performed.

### 3.6 Platform risk (the real threat)

- **Atlassian**: Rovo MCP Server GA **Feb 2026** (60+ tools across Jira/Confluence/Bitbucket/Compass); **"Agents in Jira" open beta Mar 2026** — agents appear as *assignees* on the board, with GitHub Copilot coding agent as the first integrated agent. ([Codex KB](https://codex.danielvaughan.com/2026/04/20/codex-cli-jira-ticket-driven-development-atlassian-mcp-automation/))
- **GitHub**: Agent HQ makes multi-agent orchestration a platform primitive.

**Consequence:** "ticket → PR" as a *feature* will be commoditised by the two systems of record within 12–18 months. The defensible surface is what neither will do well: **cross-vendor, policy-bound, cost-attributed, auditable execution that an engineering leader configures** — plus the org's accumulated skills and codebase memory.

---

## 4. Standards & interoperability (build against these, not around them)

| Standard | 2026 status | Action for ADLC |
|---|---|---|
| **MCP** | ~**97M monthly SDK downloads (Mar 2026)**, up from 2M at launch (Nov 2024) — ~4,750% growth; ~110M/mo by mid-2026 | Expose ADLC as an **MCP server** (tools: `list_runs`, `approve_run`, `trigger_run`) and consume MCP tool servers inside agents |
| **A2A** | **v1.0 April 2026**, 150+ orgs, integrated in AWS/Azure/GCP | Roadmap: publish an Agent Card so ADLC pods are callable by other orchestrators |
| **AGENTS.md / skills-as-markdown** | De facto convention | Already ADLC's native format — import/export `AGENTS.md` and Claude-style skills verbatim |

([arXiv survey](https://arxiv.org/pdf/2505.02279), [Governance gaps in interoperability protocols](https://arxiv.org/pdf/2606.31498))

Note the arXiv finding that MCP/A2A/ACP **cannot express governance constraints** — permissions, approval requirements, spend limits. That gap is precisely ADLC's product thesis, and it is now academically documented.

---

## 5. Regulatory & compliance surface

| Instrument | Date | What it demands | ADLC feature that answers it |
|---|---|---|---|
| **EU AI Act Art. 50** (transparency) | **2 Aug 2026** | Disclose AI-generated content / AI interaction | Machine-readable "authored by agent X, model Y, approved by human Z" on every PR and commit |
| **EU AI Act high-risk** | Dec 2027 / Aug 2028 | Risk mgmt, logging, human oversight, technical documentation | Immutable audit log, approval policies, evidence export |
| **SOC 2 Type II** | Now | Least-privilege, immutable logging of inputs/outputs, continuous monitoring | Audit middleware + retention policy + access reviews |
| **ISO/IEC 42001** | Baseline expectation by ~2026–2028 | AI management system across lifecycle | Policy registry, model inventory, incident/rollback trail |
| **FINRA 2026 report** | Now (financial services) | Names three agent risks: **autonomy, scope creep, auditability** | Approval gate, tool/branch allowlists, run trace |

Note (important, and honest): ordinary AI *coding assistance* is generally **not** an Annex III high-risk use. The compliance sell is therefore about the customer's **own** AI-governance posture and procurement checklist — not about ADLC being a regulated high-risk system. Positioning it otherwise would be FUD, and enterprise buyers will catch it. ([Legal Nodes](https://www.legalnodes.com/article/eu-ai-act-2026-updates-compliance-requirements-and-business-risks), [Augment](https://www.augmentcode.com/guides/eu-ai-act-2026))

---

## 6. Pricing intelligence

### What the market actually charges (2026)

| Model | Example | Price point |
|---|---|---|
| Per-seat assistant | Copilot Business / Enterprise | $19 / $39 per user |
| Per-seat agentic | Tabnine Agentic; Cody Enterprise | $59 per user |
| Per-seat review | CodeRabbit $24 · Greptile $30 · Qodo $30 | ~$24–30 per dev |
| Per-unit outcome | Macroscope ~$0.95/review; Intercom $0.99/resolution | ~$1 per unit of work |
| Agent-time credits | Devin **$2.25/ACU** (~15 min of agent work) → **~$9/agent-hour** | Team $500/mo |
| Platform credits | GitHub AI Credits, 1¢ each; agent session $6–12+ | Usage-based since Jun 2026 |

### Structural trend
Per-seat **21% → 15%** of SaaS in 12 months; **hybrid (base + usage overage) at 41%** and now the default; Gartner expects **40% of enterprise SaaS to carry outcome-based elements by 2026**. ([Monetizely](https://www.getmonetizely.com/blogs/the-2026-guide-to-saas-ai-and-agentic-pricing-models), [Korix](https://korixinc.com/learning-center/ai-pricing-models-2026))

**Implication for ADLC:** price **hybrid — platform fee (governance seats) + metered runs**, with per-run LLM cost attribution shown in the UI. A run is a defensible billing unit because it maps to a ticket, which maps to a Jira/Linear item the buyer already counts. Anchor against Devin's ~$9/agent-hour and GitHub's $6–12/session: a *governed* run at $2–4 marginal price is a value story, not a discount story.

---

## 7. Funding environment (if ADLC raises)

| Benchmark | 2026 number |
|---|---|
| Pre-seed agentic AI | $5–20K ARR **or credible LOIs** |
| Seed expectation | **$300–500K ARR**, efficient growth, clear unit economics |
| Series A | **$1–3M ARR** + repeatable acquisition |
| Median US seed pre-money | ~$16M; AI premium → ~$17.9M median |
| AI revenue multiple | $2M ARR AI → **$80–100M (40–50×)** vs traditional SaaS 10–20× |
| Top-quartile NDR | **140–170%** |

([CRV KPIs](https://www.crv.com/content/key-performance-indicators), [AI Business](https://aibusiness.vc/startups/ai-startup-metrics-investors-track), [Eqvista](https://eqvista.com/ai-startup-fundraising-trends/))

**Translation:** with an org model, metered billing, and 3–5 design partners producing ~$5–20K ARR, ADLC is a credible pre-seed. The gate to seed is **$300K+ ARR**, i.e. roughly **15–25 paying teams on the $149–499 tiers**, or **3–5 enterprise pilots**.

---

## 8. Model layer (buy, don't build)

Claude Opus 5 leads SWE-bench Verified at **96–97%**, with GPT-5.6 Sol at 96.2% and Claude Fable 5 at 95.0%; on Anthropic's harder agentic Frontier-Bench v0.1, Opus 5 leads at **43.3%**. ([llm-stats](https://llm-stats.com/benchmarks/swe-bench-verified), [claude5.ai](https://claude5.ai/news/claude-opus-5-benchmark-results-analysis))

Two consequences:
1. **Raw code-writing ability is commoditised and near-saturated on the classic benchmark.** Any moat built on "our agent writes better code" evaporates on the next model release.
2. **The remaining 3–4% on SWE-bench Verified and the 57% gap on Frontier-Bench are exactly where human approval earns its keep.** The gate isn't temporary scaffolding — it's the honest response to a residual failure rate that no vendor has eliminated.

→ ADLC must be **multi-model by architecture** (Anthropic default, plus OpenAI / Azure / Bedrock / local Ollama for self-hosted buyers). Forrester lists "model agility" as an ADP differentiator; enterprises will not sign a single-model dependency.

---

## 9. Positioning — the sentence to defend

> **ADLC is the governed execution layer for AI software delivery.** Engineering leaders define *how* agents behave (skills), *which* agents run in *what order* (pods), *what must be approved by whom* (policies), and *what it costs* (metered runs) — and get an audit trail their auditors accept.

**Not:** "a better Devin." **Not:** "AI writes your code." Those framings lose to $60B and $1.5B competitors on distribution and model spend.

### Message per buyer
| Buyer | Headline | Proof required |
|---|---|---|
| VP Engineering | "Your agents already ship code. Who approves it?" | Approval gate, policy config, run trace |
| Platform / DevEx lead | "One control plane across Copilot, Claude, Cursor, Devin" | Multi-model, connections, templates |
| CISO / Compliance | "Every agent action is attributable and exportable" | Audit log, retention, evidence export, SSO |
| CFO | "Cost per ticket, not cost per seat" | Per-run token/$ attribution, budget caps |

### Where ADLC loses today (state it before an investor does)
1. No live deployment, no design partners, no usage data.
2. Model-agnosticism was aspirational until this build (Anthropic hardcoded).
3. Review agent existed only as a roadmap line — the differentiator was unbuilt.
4. No cost attribution, so the CFO story was unprovable.
5. No self-hosted story, which is table stakes against OpenHands/Factory in enterprise.

*(Items 2–5 are addressed by the implementation shipped alongside this document; item 1 is a go-to-market task, not an engineering one.)*

---

## 10. Threat register & counters

| Threat | Likelihood | Counter |
|---|---|---|
| GitHub Agent HQ adds policies/approvals | **High**, 12–18 mo | Be cross-platform (GitLab, Jira, Linear); own the ticket-side loop GitHub won't |
| Atlassian makes "Agents in Jira" governed | **High** | Ship the ADLC MCP server; be the execution engine *behind* Jira agents |
| Factory/Cognition move down-market | Medium | Self-serve + free tier + OSS-friendly skills; they are enterprise-sales-shaped |
| OpenHands adds SDLC loop | Medium | They are agent-shaped, not lifecycle-shaped; lead with Jira/Linear + multi-env deploy |
| Model vendors ship end-to-end platforms | Medium | Stay model-neutral; neutrality is the product |
| Commoditisation of review | High | Bundle review into the run; never sell it standalone |
| Enterprise refuses SaaS for source code | **Certain** | Self-hosted + BYO-LLM + license key (built) |

---

## 11. Sources

- [Forrester — Launching the Agentic Development Platforms Vendor Landscape, Q3 2026](https://www.forrester.com/blogs/launching-the-agentic-development-platforms-vendor-landscape-q3-2026/)
- [Forrester — Agentic Software Development Takes The Lead](https://www.forrester.com/blogs/agentic-software-development-takes-the-lead-from-code-assistants-to-orchestrated-sdlc-agents/)
- [Black Duck / PRNewswire — AI coding hits 97% enterprise adoption; governance is the ROI multiplier](https://www.prnewswire.com/news-releases/ai-coding-hits-97-enterprise-adoption-new-black-duck-study-shows-governance-is-the-roi-multiplier-302794103.html)
- [PwC — Agentic SDLC in practice (PDF)](https://www.pwc.com/m1/en/publications/2026/docs/future-of-solutions-dev-and-delivery-in-the-rise-of-gen-ai.pdf)
- [Factory $150M Series C at $1.5B](https://cryptobriefing.com/factory-ai-150m-series-c-funding/) · [Factory enterprise customers](https://www.idlen.io/news/factory-ai-150-million-1-5-billion-droids-coding-agents-enterprise-april-2026/)
- [Devin pricing 2026 (ACUs)](https://www.usecarly.com/blog/devin-pricing/) · [Cognition plan lineup](https://www.eesel.ai/blog/cognition-ai-pricing)
- [GitHub Agent HQ guide](https://www.fundesk.io/github-agent-hq-multi-agent-development-guide) · [GitHub usage-based billing 2026](https://usagebox.com/articles/github-copilot-usage-based-billing-2026) · [Copilot plans](https://github.com/features/copilot/plans)
- [OpenHands enterprise & funding](https://agentmarketcap.ai/blog/2026/04/06/openhands-open-source-coding-agent-allhands-ai-series-a-swe-bench)
- [Cursor ARR / SpaceX acquisition](https://thenextweb.com/news/cursor-anysphere-2-billion-funding-50-billion-valuation-ai-coding) · [Cursor revenue estimates](https://getlatka.com/companies/cursor.com)
- [AI code review pricing comparison](https://levelop.dev/blog/best-ai-code-review-tools-2026-coderabbit-greptile-qodo-compared) · [Stork comparison](https://www.stork.ai/blog/best-ai-code-review-tools-2026)
- [Sourcegraph Cody enterprise pricing](https://weavai.app/blog/en/2026/04/30/sourcegraph-cody-review-2026-enterprise-ai-at-59-mo/) · [Enterprise code generators / ISO 42001](https://www.augmentcode.com/tools/best-enterprise-ai-code-generators)
- [Engineering intelligence platforms 2026](https://www.cortex.io/post/engineering-intelligence-platforms-definition-benefits-tools) · [Faros alternatives / DX-Atlassian](https://jellyfish.co/blog/faros-ai-alternatives/)
- [Atlassian Rovo MCP + Agents in Jira](https://codex.danielvaughan.com/2026/04/20/codex-cli-jira-ticket-driven-development-atlassian-mcp-automation/)
- [AI agent control plane 2026](https://preloop.ai/resources/ai-agent-control-plane-2026) · [AI agent governance & audit trails](https://zylos.ai/research/2026-05-01-ai-agent-governance-compliance-2026/)
- [Governance gaps in MCP/A2A/ACP (arXiv)](https://arxiv.org/pdf/2606.31498) · [Agent interoperability protocol survey (arXiv)](https://arxiv.org/pdf/2505.02279)
- [EU AI Act portal](https://artificialintelligenceact.eu/) · [EU AI Act 2026 for dev teams](https://www.augmentcode.com/guides/eu-ai-act-2026) · [Legal Nodes 2026 update](https://www.legalnodes.com/article/eu-ai-act-2026-updates-compliance-requirements-and-business-risks)
- [2026 guide to SaaS/AI/agentic pricing](https://www.getmonetizely.com/blogs/the-2026-guide-to-saas-ai-and-agentic-pricing-models) · [AI pricing models 2026](https://korixinc.com/learning-center/ai-pricing-models-2026)
- [CRV startup KPIs 2026](https://www.crv.com/content/key-performance-indicators) · [AI startup metrics benchmarks](https://aibusiness.vc/startups/ai-startup-metrics-investors-track) · [AI fundraising trends](https://eqvista.com/ai-startup-fundraising-trends/)
- [SWE-bench Verified leaderboard](https://llm-stats.com/benchmarks/swe-bench-verified) · [Claude Opus 5 benchmarks](https://claude5.ai/news/claude-opus-5-benchmark-results-analysis)
- [AI coding market share/revenue](https://blog.exceeds.ai/ai-coding-us-market-share/) · [Agentic AI forecast roundup](https://softwarestrategiesblog.com/2026/02/26/roundup-of-agentic-ai-forecasts-and-market-estimates-2026/) · [AI code tools market](https://www.mordorintelligence.com/industry-reports/artificial-intelligence-code-tools-market)
- [Top AI coding agents & platforms 2026](https://www.marktechpost.com/2026/06/10/ai-coding-agents-development-platforms-2026/) · [CrewAI enterprise agentic survey](https://www.businesswire.com/news/home/20260211693427/en/Agentic-AI-Reaches-Tipping-Point-100-of-Enterprises-Plan-to-Expand-Adoption-in-2026-New-CrewAI-Survey-Finds)
