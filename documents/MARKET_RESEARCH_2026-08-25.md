# ADLC — Market, Competition and the Route to ₹100 Cr

**Prepared:** 25 August 2026 · **Horizon:** 2026 → 2029
**Supersedes nothing.** This sits alongside `MARKET_AND_COMPETITIVE_RESEARCH_2026.md`
(16 Aug) and updates it in three places where that document is now wrong or thin:
the collaboration wedge, the India go-to-market, and the actual arithmetic of the
₹100 Cr goal. Everything else in the 16 Aug document still stands.

Same rule as that file: no figure without a source, and analyst sizings are given
as ranges because they disagree by 2× depending on scope.

---

## 0. The short version

1. **The category is real and growing fast.** The agentic-SDLC automation platform
   market was ~**$1.8B in 2025**, projected to **$38.4B by 2034 at 40.5% CAGR**
   ([MarketIntelo](https://marketintelo.com/report/agentic-sdlc-automation-platform-market)).
   Narrower "GenAI in SDLC" scopes put 2026 at **$845–874M** growing to
   **$9.49B by 2034 (35.3% CAGR)**
   ([Straits](https://straitsresearch.com/report/generative-ai-in-software-development-lifecycle-market)).
   The spread is a scope artefact; the direction is not in dispute.
2. **Forrester has named the category** — *Agentic Development Platforms*, 25
   vendors, Q3 2026 — and says differentiation has moved **off code generation**
   onto orchestration, governance, cost transparency and human oversight
   ([Forrester](https://www.forrester.com/blogs/launching-the-agentic-development-platforms-vendor-landscape-q3-2026/)).
   That is this codebase's existing thesis and it is holding.
3. **The new wedge is the one just built.** Nobody in the ADP landscape owns the
   *conversation*. Devin, Factory, Cursor and GitHub Agent HQ all assume Slack or
   Teams sits beside them. Atlassian is closest — agents in Jira comments
   ([Atlassian](https://www.businesswire.com/news/home/20260224033792/en/Atlassian-Introduces-Agents-in-Jira-to-Drive-Human-AI-Collaboration-at-Enterprise-Scale))
   — but a Jira comment is not a team's day. Phase 12 puts channels, agents and
   the approval gate in one surface.
4. **India is a distribution advantage, not a market to "also target".** Work
   groups are the most common chat-group type among Indian messaging users
   ([Statista](https://www.statista.com/statistics/1388603/india-popular-types-of-messaging-app-chat-groups)),
   and Indian SaaS has ~**250 companies past $10M ARR and 36 past $100M**
   ([wellows](https://wellows.com/blog/saas-startups/)). Sell in INR, ship
   DPDP-compliant, price against WhatsApp+Jira+Slack, not against Devin.
5. **The ₹100 Cr goal is achievable; unicorn in 3 years is not.** See §5. ₹100 Cr
   (~$11.5M) liquid needs roughly **$3–6M ARR and a secondary or acquisition** —
   hard but real. A $1B valuation in 36 months from zero users is not a plan, it
   is a lottery ticket, and treating it as the target distorts every decision
   below it.
6. **The binding constraint is not features. It is that nobody uses this yet.**
   The platform now has more surface area than most funded competitors. It has
   zero paying users. Every hour spent on feature #48 instead of customer #1 is
   negative expected value from here.

---

## 1. Market sizing

| Scope | 2026 | Forward | CAGR | Source |
|---|---|---|---|---|
| Agentic SDLC automation platforms | $1.8B *(2025)* | $38.4B by 2034 | **40.5%** | [MarketIntelo](https://marketintelo.com/report/agentic-sdlc-automation-platform-market) |
| GenAI in SDLC | $845–874M | $9.49B by 2034 | 35.3% | [Straits](https://straitsresearch.com/report/generative-ai-in-software-development-lifecycle-market), [Fortune BI](https://straitsresearch.com/report/generative-ai-in-software-development-lifecycle-market) |
| AI coding tools (actual revenue) | **$12.8B** (from $5.1B in 2024) | — | — | prior research doc |
| Team collaboration (the *other* budget line) | — | — | — | see §3.3 |

**Reading it honestly.** The "$1.8B → $38.4B" line is the one that describes this
product, and it is also the least mature estimate — a 40% CAGR forecast nine
years out is a directional claim, not a plannable number. What is plannable:
coding is the largest single line item of enterprise AI spend, and the agentic
slice compounds roughly 2× faster than the assistant slice.

### TAM / SAM / SOM, bottom-up

Top-down market numbers are near-useless for a company with no customers. The
bottom-up version:

| | Definition | Estimate | How it was derived |
|---|---|---|---|
| **TAM** | Every software org running ≥2 AI coding agents worldwide | ~$12–16B/yr | The AI-coding-tools revenue line, since orchestration is a tax on it |
| **SAM** | Orgs of 10–500 engineers that need governance *and* have no platform team to build it | ~$1.5–2.5B/yr | The segment too big for ungoverned agents, too small to build a control plane |
| **SOM (3yr)** | What one team can realistically win | **$3–6M ARR** | 150–400 paying orgs at $1–3K/mo. See §5 |

The SOM number is the only one that should drive a decision. Everything above it
is context for a fundraising deck.

---

## 2. What actually hurts in 2026

Unchanged from the 16 Aug research and still the strongest part of the case:

| Symptom | Evidence | What ADLC does about it |
|---|---|---|
| Review capacity is the constraint | Review time **+91%** on high-AI-adoption teams (Faros) | The Reviewer agent *is* added review capacity, bundled |
| Trust deficit | **46%** distrust AI output; **66%** say "almost right but not quite" | Diffs, findings, scores, an audit trail |
| Governance is the ROI multiplier | **97%** enterprise adoption of AI coding (Black Duck) | Policy gate, blast-radius checks, compliance export |
| Cost opacity | Agentic sessions ≈1000× the tokens of single-turn | Per-run cost attribution, budget caps, BYO keys |
| Tool sprawl | 3–4 concurrent agent tools per org | Model- and agent-agnostic by design |
| **Coordination sprawl** | *new in this pass* — see §3.3 | **Phase 12: Workspace** |

---

## 3. Competition

### 3.1 The execution layer (they write the code)

| Vendor | 2026 position | Pricing | Where ADLC differs |
|---|---|---|---|
| **Devin** (Cognition) | Cloud agent + persistent sandbox; acquired Windsurf, rebranded Devin Desktop; knowledge base learns codebase conventions | Free / $20 Pro / **$200 Max** / Teams $80 + $40/seat | Devin *is* the agent. ADLC governs whichever agent you use. Also: Cognition's terms permit training on customer data, opt-out **paid tiers only** ([theaiagentindex](https://theaiagentindex.com/agents/devin)) — a straight competitive opening |
| **Factory AI** | Multi-surface Droids (Desktop/CLI/SDK), Factory-managed cloud sandboxes | Plus / Max / Business / Enterprise | Written **no-training guarantee on every tier**, ISO 42001, ZDR on Business+ ([theaiagentindex](https://theaiagentindex.com/compare/factory-ai-vs-devin)). This is the bar to match on trust posture |
| **Cursor** | Hybrid local IDE + persistent cloud agents | from $20/mo | IDE-first. No approval gate, no policy engine |
| **GitHub Agent HQ** | Multi-agent orchestration, public preview Feb 2026; CodeQL review agent auto-scans agent PRs | Premium requests ≈$0.01/credit | Owns the repo. Cannot configure agent *behaviour* the way skill files do |

### 3.2 The management layer (they plan the work)

| Vendor | 2026 position | Pricing |
|---|---|---|
| **Atlassian Rovo / Agents in Jira** | Open beta: assign work to Rovo *and third-party* agents in Jira, iterate in comments, respects project permissions and approval flows | Rovo Dev **$20/dev/mo, 2,000 credits**; core Rovo rides existing Atlassian subs ([Atlassian](https://www.atlassian.com/software/rovo-dev/pricing)) |
| **GitLab Duo Agent Platform** | Agents implement issues, run code review against org standards | **$1/credit** on top of Duo; Duo Pro $19/user/mo ([GitLab Duo FAQ](https://cursor-alternatives.com/blog/gitlab-duo-faq/)) |
| **Linear** | Fast issue tracking, AI triage | per-seat |

**Atlassian is the real threat**, and more so than the 16 Aug document allowed.
It has the sprint planner, the agent-in-comments loop, the permissions model, and
the incumbency. What it does not have: a deploy approval gate with policy
enforcement, cross-tracker support (it is Jira, by definition), model agility, or
per-run cost attribution. Compete on *those*, never on "we also do tickets".

### 3.3 The collaboration layer — the gap Phase 12 fills

This is the part the previous research missed entirely.

Every competitor above assumes a chat tool sits beside it. Slack's 2026 feature
set is channels, threads, huddles, Canvas, Lists and 2,600+ integrations; Teams
matches it and anchors to Microsoft 365; **AI summaries are now table stakes
across all of them** ([Slack](https://slack.com/blog/compare/teams-alternatives),
[Zapier](https://zapier.com/blog/slack-vs-microsoft-teams/)).

Nobody has put the agent, the run and the approval in that surface — because
nobody else owns all three. That is a structural advantage, not a feature gap:

- Slack can *show* you a run via webhook. It has no `agents` table, so it cannot
  start one attributed to you, metered against your quota, gated by your policy.
- Jira can host an agent in a comment thread. It is not where the team's day
  happens, and it stops at the ticket.
- ADLC has the agent rows, the pod rows, the policy rows and the message rows in
  one database. `@qa PROJ-214` can therefore be a real run.

**The honest caveat:** "replace Slack" is a claim that has killed many products.
The realistic version is *replace the WhatsApp group that exists because Jira and
Slack were too heavy for a 12-person startup* — and, in enterprises, be the place
the governed conversation happens while Slack keeps the social one. Positioning
this as a Slack killer will lose deals. Positioning it as *"the conversation your
auditor can read"* wins them.

### 3.4 What was verified and what was not

Carried forward from `RESEARCH_TRIAGE_2026-08.md` and still true:
- Rovo **does** ship a Sprint Planning Agent — the "no competitor plans sprints"
  claim is dead and has been corrected in the code and docs.
- GitHub Agent HQ went to public preview **4 Feb 2026**, not Oct 2025.
- Claude Code "inference hooks" are prompt-content DLP, **not** an agent-action
  approval gate. No competitor yet has "block this merge without N approvers".

Still unverified, still do not quote to an investor: the smaller funding figures
(Sapiom, Meridian, Kana, Trase, Sycamore, WitnessAI, Baseliner.ai).

---

## 4. India and global go-to-market

### 4.1 Why India first is a real strategy, not patriotism

- **The pain is sharpest here.** Work/office groups are the most common chat-group
  type among Indian messaging users ([Statista](https://www.statista.com/statistics/1388603/india-popular-types-of-messaging-app-chat-groups)).
  A 15-person Bangalore startup coordinating a production deploy in a WhatsApp
  group is the modal customer, and they know it is a problem.
- **The market has depth.** ~250 Indian SaaS companies past $10M ARR, 36 past
  $100M; Indian SaaS grew at **24% CAGR FY19–FY24**
  ([wellows](https://wellows.com/blog/saas-startups/), [productgrowth](https://productgrowth.in/insights/india/india-saas-trends/)).
- **Price sensitivity is a moat here, not a problem.** Devin Max at $200/seat/mo
  is ₹17,400/seat/mo. That is unsellable to most Indian engineering teams. A
  platform priced in INR at a fraction of it, that also removes the Slack bill,
  is a different conversation.
- **Regulation is a forcing function.** The DPDP Act 2023 was notified 14 Nov 2025
  with phased compliance over 12–18 months and penalties to **₹250 Cr**
  ([Lexology](https://www.lexology.com/library/detail.aspx?g=b268c42c-af1f-449b-94e5-f46ab8ec6361),
  [MYITMANAGER](https://myitmanager.in/dpdp-act-compliance-india/)). Every Indian
  company processing personal data now needs consent notices, breach
  notification, and retention controls. An audit-log-native platform that can run
  **inside their own perimeter from a compose file** answers a question their
  current WhatsApp-group workflow answers very badly.

### 4.2 The commercial mechanics that must be built for India

Currently the billing path is Stripe-only (`stripe_service`, `price_cents`). For
India that is a blocker, not a preference:

| Requirement | Detail | Status |
|---|---|---|
| INR pricing + GST | 18% GST on SaaS; must be shown and invoiced | **not built** |
| Razorpay | Domestic 2% + GST (UPI/cards/netbanking) ([Razorpay](https://razorpay.com/blog/razorpay-payment-gateway-pricing-explained/)) | **not built** |
| International inbound | Razorpay MoneySaver Export Account: bank transfer **1% + GST**, zero forex markup, vs 3% + GST on international cards ([Razorpay](https://razorpay.com/blog/international-payment-processing-cost-in-india-2026-the-complete-rate-benchmark-for-indian-businesses)) | **not built** |
| FIRC / eFIRC | Mandatory evidence for zero-rated export GST refunds | process, not code |
| Data residency | DPDP-driven; the self-host tier already answers this | **partly built** (compose file) |

`price_cents` is already an integer money field, so an INR path is an additive
change rather than a refactor — but it is a real piece of work and it is the
single highest-leverage unbuilt commercial feature for the India motion.

### 4.3 Sequence

1. **India, self-serve, INR** — design partners from the founder's own network,
   priced ₹4,000–15,000/mo. Goal is 10 paying teams, not revenue.
2. **Global, self-serve, USD** — same product, Stripe, $99–499/mo. GEO/SEO and
   the VS Code extension are the distribution.
3. **Enterprise, both** — self-host + SSO + compliance export. This is where the
   $2–5K/mo contracts live and where the governance work already done pays.

Do not run all three at once. That is the mistake the `feedback_one_product_focus`
note already flags.

---

## 5. The ₹100 Cr question, answered with arithmetic

The goal as stated: **₹100 Cr liquid, personally, within 3 years**, ideally via
unicorn status.

### 5.1 What ₹100 Cr liquid actually requires

₹100 Cr ≈ **$11.5M** at ~₹87/USD. Liquid means post-tax, in hand.

Working backwards, with Indian LTCG on unlisted shares at 12.5% plus surcharge
(~14–15% effective for a gain this size):

| Step | Figure |
|---|---|
| Net needed | ₹100 Cr |
| Gross proceeds needed (÷ ~0.86) | **~₹116 Cr** ≈ $13.3M |
| Founder equity at exit, realistic post-seed | 40–55% |
| **Enterprise value required** | **~$24–33M** |

At the 4–9× ARR range private SaaS actually transacts at in 2026 — median ~4–5×,
7–10× only for >40% growth
([L40°](https://www.l40.com/insights/saas-multiples), [Aventis](https://aventis-advisors.com/saas-valuation-multiples/)) —
that implies:

> **$3–6M ARR within ~3 years, then a sale or a large secondary.**

That is roughly **150–400 paying customers at $1,000–3,000/month**. It is hard.
It is not fantasy. Retool reached $120M ARR and a $3.2B valuation; developer
tools carry **76.8% gross margins** and DevOps infrastructure trades at
**36.5× EBITDA vs 12.7× for SaaS generally** ([wellows](https://wellows.com/blog/saas-startups/), [ClearlyAcquired](https://www.clearlyacquired.com/blog/ebitda-multiples-for-saas-and-software-companies-2025-2026)).
The category rewards this shape of company.

### 5.2 Why unicorn-in-3-years is the wrong target

A $1B valuation at even a generous 15× forward ARR needs **~$65M ARR**. From
zero customers, in 36 months, that has been done perhaps a handful of times in
history and never without either a hyper-viral consumer loop or $100M+ of capital
behind a category creation story.

Chasing it directly causes three specific, predictable errors — all three of
which are already visible in this repo's history:

1. **Building breadth instead of depth.** 12 phases of features, zero users.
2. **Optimising for the deck, not the customer.** The market research is
   excellent; the customer discovery is absent.
3. **Refusing to charge early**, because ₹5,000/month "doesn't move the needle
   toward ₹100 Cr". It is the only thing that proves any of this is real.

The seed bar from the `marketing_ai_research` work — **$300–500K ARR plus 60 days
of production logs** — is the actual next milestone. Everything else is downstream
of it.

### 5.3 The plausible 3-year path

| Year | ARR target | Customers | What has to be true |
|---|---|---|---|
| **Y1** (to Aug 2027) | **$150–300K** | 20–40 | Deployed. 10 India design partners paying. INR billing live. One public case study with real numbers |
| **Y2** | **$1–2M** | 80–150 | Global self-serve working. Enterprise tier with 3–5 logos. NRR >110% |
| **Y3** | **$3–6M** | 150–400 | Growth >40% YoY sustained → the 7–10× multiple band, not the 4–5× one |
| **Exit** | **$24–33M EV** | — | Strategic buyer (Atlassian, GitLab, JFrog, Harness, or an Indian IT-services major buying an agentic delivery layer) |

Indian investors will underwrite this on **LTV/CAC ≥3:1, NRR ≥110%, and a clear
path to profitability** ([upGrowth](https://upgrowth.in/cac-benchmarks-indian-b2b-saas-arr-band-2026/)).
Those three ratios matter more than any feature on the roadmap.

### 5.4 The unpleasant sentence

The single largest risk to ₹100 Cr is not Devin, Atlassian, or missing features.
It is that **this platform has been in development for months, has ~13,000 lines
of well-governed backend, 137 tests, five agents, SSO, MCP, a marketplace, a VS
Code extension and now a full collaboration layer — and has never been deployed
where a stranger could sign up.**

Nothing in this document changes that. Only deploying does.

---

## 6. Feature gaps, ranked by revenue impact

Not by how interesting they are to build.

| # | Gap | Why it matters | Effort |
|---|---|---|---|
| **1** | **Deploy it.** Public URL, working signup, someone else's credit card | Every other row is worth $0 until this is done | days |
| **2** | INR + GST + Razorpay | Blocks the entire India motion (§4.2) | ~1 week |
| **3** | Mobile-responsive Workspace / PWA push | A WhatsApp replacement that does not work on a phone is not one | ~1 week |
| ~~4~~ | ~~Engineering Pulse dashboard (Rovo's "AI Pulse")~~ | **Built 25 Aug** — `/analytics/pulse`, `/pulse` | done |
| ~~5~~ | ~~Run concurrency cap + queue (Devin's "automations queueing")~~ | **Built 25 Aug** — `policy_service.check_concurrency` | done |
| **6** | No-training guarantee, stated in writing on `/security` | Factory ships this on every tier; Cognition does not. Free trust win | hours |
| **7** | Voice notes in Workspace | The single most-used WhatsApp feature not yet replicated | ~3 days |
| **8** | SAML + SCIM | Enterprise procurement blocker — but only at Y2 scale | ~2 weeks |
| 9 | Marketplace payouts | Two-sided market with no buyers yet. Not now | — |

Rows 1–3 are the ones that touch revenue in the next 90 days. Rows 4 and 5 were
built on 25 Aug alongside the Workspace layer; they are competitor-parity items,
not demand generators, and closing them changes nothing until row 1 is done.

---

## 7. Positioning, in one paragraph

> ADLC is where the work *and* the conversation about the work both live. Agents
> plan, code, test and review inside the same channels your team already talks
> in — and nothing reaches production without a human pressing approve, on a
> record your auditor can read. Model-agnostic, agent-agnostic, self-hostable,
> priced in rupees.

Never claim to be faster or better than Devin, Cursor or Copilot at writing code.
The `POSITIONING` rule in `CLAUDE.md` — compare design intent, never quality —
holds, and is more defensible than any benchmark claim would be.

---

## Sources

Market sizing: [MarketIntelo](https://marketintelo.com/report/agentic-sdlc-automation-platform-market) ·
[Straits Research](https://straitsresearch.com/report/generative-ai-in-software-development-lifecycle-market) ·
[Forrester ADP Landscape Q3 2026](https://www.forrester.com/blogs/launching-the-agentic-development-platforms-vendor-landscape-q3-2026/) ·
[arXiv 2604.26275](https://arxiv.org/abs/2604.26275)

Competitors: [Devin review](https://theaiagentindex.com/agents/devin) ·
[Factory vs Devin](https://theaiagentindex.com/compare/factory-ai-vs-devin) ·
[MarkTechPost 2026 roundup](https://www.marktechpost.com/2026/06/10/ai-coding-agents-development-platforms-2026/) ·
[Contrary Research: Cognition](https://research.contrary.com/company/cognition) ·
[Atlassian: Agents in Jira](https://www.businesswire.com/news/home/20260224033792/en/Atlassian-Introduces-Agents-in-Jira-to-Drive-Human-AI-Collaboration-at-Enterprise-Scale) ·
[Rovo Dev pricing](https://www.atlassian.com/software/rovo-dev/pricing) ·
[GitLab Duo FAQ](https://cursor-alternatives.com/blog/gitlab-duo-faq/)

Collaboration: [Slack vs Teams alternatives](https://slack.com/blog/compare/teams-alternatives) ·
[Zapier: Slack vs Teams 2026](https://zapier.com/blog/slack-vs-microsoft-teams/) ·
[Statista: India chat group types](https://www.statista.com/statistics/1388603/india-popular-types-of-messaging-app-chat-groups)

India: [MeitY DPDP Rules 2025](https://www.lexology.com/library/detail.aspx?g=b268c42c-af1f-449b-94e5-f46ab8ec6361) ·
[DPDP compliance checklist](https://myitmanager.in/dpdp-act-compliance-india/) ·
[Razorpay pricing](https://razorpay.com/blog/razorpay-payment-gateway-pricing-explained/) ·
[Razorpay international rates 2026](https://razorpay.com/blog/international-payment-processing-cost-in-india-2026-the-complete-rate-benchmark-for-indian-businesses) ·
[India SaaS trends](https://productgrowth.in/insights/india/india-saas-trends/) ·
[CAC benchmarks Indian B2B SaaS](https://upgrowth.in/cac-benchmarks-indian-b2b-saas-arr-band-2026/)

Valuation: [L40° SaaS multiples](https://www.l40.com/insights/saas-multiples) ·
[Aventis Advisors](https://aventis-advisors.com/saas-valuation-multiples/) ·
[ClearlyAcquired EBITDA multiples](https://www.clearlyacquired.com/blog/ebitda-multiples-for-saas-and-software-companies-2025-2026) ·
[wellows: SaaS startups 2026](https://wellows.com/blog/saas-startups/)
