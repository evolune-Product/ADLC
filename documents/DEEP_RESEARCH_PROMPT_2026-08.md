# ADLC — Deep Research Prompt (run this through GPT/Gemini deep research)

Paste this whole thing into a deep-research-capable model. Bring back whatever it returns — I'll triage it against what's already built.

---

I'm building **ADLC**, an "Agentic SDLC" platform — engineering leaders define AI agent behavior via markdown skills, group agents into pods, connect GitHub/GitLab + Jira/Linear, and run tickets through an automated pipeline: sprint plan → code → QA → review → **human approval gate** → multi-environment deploy. The product thesis is: **don't compete on code-generation quality (commoditized) — compete as the governed execution layer**: policy-as-config approval gates, per-run cost attribution, audit trail, multi-model support, self-hosted/BYO-LLM.

It already has (as of August 2026): a Reviewer agent that scores PRs and gates deploys, an approval-policy engine (N-approvers, severity blocking, protected branches/paths), metered billing with Stripe, a template/skill/pod marketplace, OIDC SSO per-org, an MCP server exposing runs/approvals as tools, GitHub+GitLab+Jira+Linear connectors with two-way ticket write-back, codebase memory (embeddings + retrieval), a source-reader that extracts linked docs efficiently, and — newest — an AI sprint planner that estimates story points and detects ticket dependencies from the backlog. **It has zero live users and has never been deployed** — this is 100% a go-to-market question at this point, not an engineering one, and I want research that reflects that honestly.

Known competitors as of my last research pass (August 2026): **Devin/Cognition**, **Factory.ai** ($150M Series C @ $1.5B), **GitHub Agent HQ / Mission Control**, **OpenHands** ($23.8M raised, MIT OSS + enterprise), **Cursor** (~$4B ARR, acquired by SpaceX), **Claude Code**. Adjacent: CodeRabbit/Greptile/Qodo (review-only), Sourcegraph Cody/Tabnine/Augment (context/enterprise assistants), Faros AI/Jellyfish/LinearB/DX-Atlassian (engineering intelligence — measure but don't execute). Platform risk: Atlassian's "Agents in Jira" and Rovo MCP, GitHub's Agent HQ commoditizing the ticket→PR loop within 12–18 months.

**What I need from you:**

1. **What changed since August 2026?** New entrants, funding rounds, pricing changes, or feature launches from any vendor above — especially anything that closes the "approval gate + skill-defined behavior + audit trail" gap I'm claiming nobody owns. Has anyone shipped AI-driven sprint planning or story-point estimation? I believe as of my last check nobody in this category does — verify or correct that.

2. **Real pricing and packaging benchmarks, current.** I'm using a hybrid platform-fee + metered-run model, anchored against Devin's ~$9/agent-hour and GitHub's $6–12/agent-session, targeting a governed run at $2–4 marginal price. Sanity-check this against what's actually converting in the market right now — is hybrid pricing still winning, or has something else taken over?

3. **Design-partner / early-traction playbook specific to this category.** Given zero users today, what's the fastest credible path to the "$300K ARR / 15–25 paying teams" seed bar for an agentic-dev-tools company in this exact wedge (governance layer, not the agent itself)? Who should the first 5 design partners be — company size, team shape, existing tool stack? Concrete outreach channels that have worked for comparable OSS/dev-tool infra products in 2026 (not generic startup advice).

4. **Funding environment check.** Current pre-seed/seed benchmarks for agentic-AI infra specifically (not generic SaaS) — typical check size, what investors are asking for as proof points in Q3/Q4 2026, and whether the "governance layer" positioning (vs. "another coding agent") is landing with investors or getting waved off as too narrow.

5. **Anything I'm structurally missing.** Given the feature set above, what would make you, as a VP Engineering or a CISO evaluating this category in 2026, say no? Be specific and skeptical — I'd rather hear it from you than from a lost deal.

6. **VS Code extension vs. marketplace creator payouts — which first?** Both are unbuilt. The extension is a distribution play (meets developers where they work); creator payouts unlock the marketplace's network effect (people won't publish paid skills/pods without a way to get paid). Given the zero-users state, which one plausibly moves the needle first, or is this the wrong pair of options entirely?

Cite sources with dates. Flag anything you're inferring vs. anything you found directly. I'll cross-check convergence between you and a second model before I act on anything here.
