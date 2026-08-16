# Research Triage — Gemini deep-research pass, 2026-08-16

Source: Gemini response to `DEEP_RESEARCH_PROMPT_2026-08.md`. Three of its
highest-stakes claims were spot-checked against live web search before
anything below was adopted into the codebase or docs; the rest are flagged by
confidence, not blindly trusted — a deep-research report is still one model's
synthesis, and this repo's own convention (`content.ts` in the marketing
surface) is that no figure ships without a source or a repo-derived count.

## Verified and adopted

**Atlassian Rovo ships a Sprint Planning Agent.** Capacity-based story
allocation + backlog dependency-conflict detection, confirmed independently
(not just via Gemini). **This falsifies the "no competitor plans sprints"
claim** that was in `sprint_planner_service.py`, `SprintPlanPanel.tsx`, and
`CLAUDE.md` — all three have been corrected in place rather than quietly
edited, per this repo's own rule for `SECURITY_POSTURE` ("move the row, don't
delete it"). The differentiation that survives: Rovo is Jira-only and stops at
the backlog; ADLC's estimate feeds a governed pipeline (policy gate, cost
attribution, audit trail) across Jira *and* Linear. **Action still open:**
`documents/MARKET_AND_COMPETITIVE_RESEARCH_2026.md` §3.2's competitive map
needs the same correction — not done in this pass, flagging for whoever
touches that file next.

**Claude Code "inference hooks" are real, but narrower than the report
implied.** Confirmed via search: launched 2026-08-05 (beta), an
organization-controlled allow/deny webhook in front of every prompt, covering
claude.ai, Cowork and Claude Code CLI. **Correction to Gemini's framing:**
this is inline **data-loss-prevention on prompt content** — an org's own DLP
platform gets a veto over what a user sends to the model — not an "agent
action approval gate" comparable to ADLC's deploy-approval policy engine.
There is no equivalent yet to "block this PR from merging without N
approvers." Real competitive signal (Anthropic is moving into the enterprise
control-plane conversation at all) without being the specific threat
Gemini's phrasing suggested.

**GitHub Agent HQ is real and shipped later than Gemini said.** Announced at
Universe 2025 (Oct 2025), public preview **4 February 2026**, not "Oct 2025"
as stated. Confirmed: a CodeQL-based review agent now scans agent-generated
PRs automatically before human review — a real second gate that narrows the
"nobody owns the pre-merge automated check" positioning. Premium-request
billing (1 credit ≈ $0.01, Pro+ 7,000 credits ≈ $70) confirmed as described.

**NewCore ($66M seed, Cyberstarts-led, $300M post-money) is real** — agent
*identity and permissions* infrastructure, confirmed via multiple
independent outlets (TechCrunch, Dealroom, others). **Not a direct
competitor**: NewCore is enterprise-wide agent IAM (any agent, any workflow),
not SDLC/coding-pipeline governance specifically. Useful as category
validation ("agent governance is fundable right now"), not as a named threat
in the competitive map.

## Plausible but NOT independently verified — do not cite as fact yet

The report's smaller funding figures were not spot-checked and should not be
repeated in an investor-facing doc until they are: **Sapiom** ($15M, agent
payments infra), **Meridian** ($17M, financial modeling agents), **Kana**
($15M, marketing agents), **Trase** ($107M), **Sycamore** ($65M, "agent
operating system"), **WitnessAI** ($58M, agent observability/security),
**Baseliner.ai** (story-point prediction startup). Directionally plausible —
2026 is genuinely a heavy-funding year for agent infra — but specific dollar
figures for lesser-known companies are exactly the pattern that turns out
wrong most often in LLM research synthesis. Spot-check before quoting any of
these in `PITCH.md`-equivalent material or to an investor.

**Design-partner target list (bank, healthcare, defense, YC SaaS startup) is
speculative by the report's own admission** — treated here as a reasonable
starting hypothesis for outreach, not a researched fact.

## High-confidence and actionable, not yet acted on

**CISO objections are well-grounded, not hallucinated** — AI-generated code
OWASP-violation rates, review-time increases, and prompt-injection CVEs are
consistent with what `MARKET_AND_COMPETITIVE_RESEARCH_2026.md` §2 already
found (review time +91%, 46% distrust). The sharpest new point: a CISO will
ask specifically whether ADLC can guarantee **no agent has unbounded deploy
rights without going through the policy gate** — worth a direct answer on
`/security` if it isn't unambiguous there already.

**VP Engineering objection worth taking seriously:** automation that
generates more PRs without also expanding review capacity makes the
review-time bottleneck worse, not better. ADLC's counter is that the Reviewer
agent *is* the added review capacity (bundled, not a separate cost) — but
this argument isn't made explicitly anywhere customer-facing yet. Candidate
addition to `/security` or the pitch deck, not done in this pass.

## Decision made from this report

**Extension before marketplace payouts**, when the choice comes up. The
report's two-sided-market reasoning is sound and matches this repo's own
`CLAUDE.md` note that these are the two remaining Phase-12 items: a paid
marketplace needs both sellers and buyers, and with zero live users there is
no buyer side yet for creators to sell into. A VS Code extension is
low-friction distribution into where developers already are and can start
generating usage before either side of a marketplace exists. Not built in
this pass — recorded as the answer to "which first" for whoever picks it up.
