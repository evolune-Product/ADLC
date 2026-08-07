/**
 * Every word and every number on the marketing surface lives here.
 *
 * Two rules, and they are the reason this file exists rather than the copy
 * being scattered through the components:
 *
 *  1. **No invented metrics.** A figure is either counted from this repository
 *     (`PLATFORM_FACTS`), taken from the pricing model in
 *     `documents/BUSINESS_PLAN_2026.md`, or cited to a named third party with
 *     the source rendered next to it (`MARKET_FACTS`). There is no fourth
 *     category, and in particular there are no customer counts, no "10x
 *     faster", and no logos we do not have.
 *  2. **No claims the product cannot honour.** Anything not yet built is
 *     either absent or explicitly marked as not built. The limitations list in
 *     `documents/IMPLEMENTATION_REPORT.md` is the check on this file.
 */

/* ────────────────────────────────────────────────────────────── the product */

/** Counted from this repository. Update them when the repository changes. */
export const PLATFORM_FACTS = {
  agentRoles: 5,
  builtinSkills: 14,
  agentTemplates: 6,
  podTemplates: 3,
  get templates() {
    return this.builtinSkills + this.agentTemplates + this.podTemplates
  },
  apiEndpoints: 97,
  modelProviders: 5,
  environments: 3,
} as const

export const PIPELINE_STEPS = [
  {
    n: '01',
    role: 'Planner',
    title: 'A ticket becomes a file-level plan',
    body: 'The Planner reads the ticket from Jira or Linear, reads the codebase memory for this project, and writes an explicit plan naming the files it intends to touch. Nothing is generated until the plan exists.',
  },
  {
    n: '02',
    role: 'Coder',
    title: 'The plan becomes a branch',
    body: 'The Coder works to your skills — markdown files you write that define how your team builds. It opens a real pull request on GitHub or GitLab, not a patch in a chat window.',
  },
  {
    n: '03',
    role: 'QA',
    title: 'The branch has to prove itself',
    body: 'The QA agent verifies that tests exist, that they run, and that they actually cover the change. A failure sends the work back to the Coder with the output attached, not to you.',
  },
  {
    n: '04',
    role: 'Reviewer',
    title: 'The diff is scored against your rubric',
    body: 'The Reviewer posts structured findings with severities and a score. It never fails a run on its own — advisory and enforcement stay separate, and only a policy turns a finding into a block.',
  },
  {
    n: '05',
    role: 'Human',
    title: 'Everything stops here',
    body: 'The run holds at the approval gate. A policy decides whether the approval in front of it is even sufficient: how many approvers, what reviewer score, which paths the agent was allowed to touch, how much the run was allowed to cost.',
    isGate: true,
  },
  {
    n: '06',
    role: 'DevOps',
    title: 'Then, and only then, it ships',
    body: 'The DevOps agent merges and promotes across dev, qa and prod, pausing for a fresh approval at every environment you have marked as gated. Every step is written to an immutable audit log.',
  },
] as const

export const CAPABILITIES = [
  {
    title: 'Skills',
    tag: 'Behaviour as markdown',
    body: 'Your standards live in version-controlled markdown, not in a prompt box. Attach them to agents; agents inherit them; changing a skill changes every agent that uses it. This is the artefact that compounds — and it belongs to you.',
  },
  {
    title: 'Pods',
    tag: 'Ordered multi-agent pipelines',
    body: 'Compose agents into an execution order with per-step configuration. A review-only pod for incoming PRs; a full pod for greenfield work; a frontend pod that enforces the accessibility baseline.',
  },
  {
    title: 'Policies',
    tag: 'The gate with teeth',
    body: 'N-approver rules, minimum reviewer scores, blocking severities, protected paths and branches, file-count ceilings, per-run cost caps — scoped per environment. A blocked deploy returns to the gate rather than failing the run.',
  },
  {
    title: 'Codebase memory',
    tag: 'Agents that stop starting cold',
    body: 'Repositories are indexed and retrieved into agent prompts. Merged runs write back what worked. Human-authored notes rank alongside indexed code, so a convention you cannot infer from the source is still available to the agent.',
  },
  {
    title: 'Cost attribution',
    tag: 'Per run, per agent, per model',
    body: 'Every model call is metered with its token counts and costed in integer millicents. You can answer "what did this feature cost" — and cap it before it runs away.',
  },
  {
    title: 'Evidence',
    tag: 'Built for the procurement question',
    body: 'Immutable audit log, retention enforcement, compliance posture, and a CSV evidence export. Who approved what, on which policy, against which reviewer score, at what time.',
  },
] as const

export const MODEL_PROVIDERS = [
  { name: 'Anthropic', detail: 'Claude — the default' },
  { name: 'OpenAI', detail: 'GPT models' },
  { name: 'Azure OpenAI', detail: 'Enterprise tenancy' },
  { name: 'OpenAI-compatible', detail: 'Any /v1 endpoint' },
  { name: 'Ollama', detail: 'Local, air-gapped' },
] as const

export const INTEGRATIONS = [
  { name: 'GitHub', kind: 'Repository', detail: 'OAuth, PRs, reviews, merges' },
  { name: 'GitLab', kind: 'Repository', detail: 'Merge requests and promotion' },
  { name: 'Jira', kind: 'Tickets', detail: 'Ticket sync into runs' },
  { name: 'Linear', kind: 'Tickets', detail: 'Token-auth ticket sync' },
  { name: 'Slack', kind: 'Notifications', detail: 'Approval alerts in channel' },
  { name: 'Webhooks', kind: 'Automation', detail: 'HMAC-signed, replay-safe' },
] as const

/* ──────────────────────────────────────────────────────── the market, cited */

/**
 * Third-party figures. Each carries its own attribution, and each is rendered
 * with that attribution visible — an uncited number on a pricing page is a
 * decoration, not an argument.
 */
export const MARKET_FACTS = [
  {
    value: '97%',
    label: 'Enterprise AI-coding adoption',
    note: 'Governance is framed as the multiplier on returns, not the brake on them.',
    source: 'Black Duck, 2026',
  },
  {
    value: '+91%',
    label: 'Increase in review time',
    note: 'Measured on teams with high AI-coding adoption. Writing code stopped being the constraint.',
    source: 'Faros AI',
  },
  {
    value: '25',
    label: 'Vendors in the new analyst category',
    note: 'Forrester says differentiation has moved off code generation and onto orchestration, governance, model agility and human oversight.',
    source: 'Forrester ADP Landscape, Q3 2026',
  },
  {
    value: '21%→15%',
    label: 'Per-seat pricing, in twelve months',
    note: 'Hybrid base-plus-usage reached 41% adoption. We price accordingly.',
    source: 'Monetizely, 2026',
  },
] as const

/* ──────────────────────────────────────────────────────────────── pricing */

export type Plan = {
  id: string
  name: string
  price: string
  cadence: string
  summary: string
  runs: string
  overage: string
  seats: string
  features: string[]
  cta: string
  ctaTo: string
  featured?: boolean
}

/** Mirrors §2 of `documents/BUSINESS_PLAN_2026.md`. */
export const PLANS: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    price: '$0',
    cadence: 'forever',
    summary: 'Bring your own model key and run a real pipeline end to end.',
    runs: '25 runs / month',
    overage: 'Hard stop — no surprise bill',
    seats: '1 seat',
    features: [
      '1 project',
      'Community skills and templates',
      'Full agent pipeline with approval gate',
      'GitHub or GitLab connection',
      'Bring-your-own LLM key (required)',
    ],
    cta: 'Start free',
    ctaTo: '/register',
  },
  {
    id: 'team',
    name: 'Team',
    price: '$199',
    cadence: 'per month',
    summary: 'For a team that wants the gate to actually mean something.',
    runs: '250 runs included',
    overage: '$0.60 per additional run',
    seats: '10 seats, then $12 each',
    features: [
      'Everything in Free, unlimited projects',
      'Approval policies and the Reviewer agent',
      'Slack, email and in-app approval alerts',
      'ROI analytics and agent scorecards',
      'Jira and Linear ticket sync',
      'Audit log with retention controls',
    ],
    cta: 'Start free, upgrade later',
    ctaTo: '/register',
    featured: true,
  },
  {
    id: 'growth',
    name: 'Growth',
    price: '$699',
    cadence: 'per month',
    summary: 'For several teams sharing one governed pipeline.',
    runs: '1,000 runs included',
    overage: '$0.45 per additional run',
    seats: '30 seats, then $10 each',
    features: [
      'Everything in Team',
      'Codebase memory and retrieval',
      'Template marketplace, publish and install',
      'Multi-environment promotion pipelines',
      'Public API v1 and signed webhooks',
      'Per-environment policy scoping',
    ],
    cta: 'Start free, upgrade later',
    ctaTo: '/register',
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    // "$3,500+" rather than "from $3,500": the longer string wrapped the price
    // onto two lines in the card, which pushed this column's whole meta plate
    // out of alignment with the other three.
    price: '$3,500+',
    cadence: 'per month',
    summary: 'For the org where a bad deploy is a board-level event.',
    runs: 'Custom volume',
    overage: 'Committed use',
    seats: 'Unlimited',
    features: [
      'Everything in Growth',
      'Self-hosted or VPC deployment',
      'Bring your own model provider, zero markup',
      'Two-approver policies and RBAC',
      'Compliance evidence export',
      'SLA and a named contact',
    ],
    cta: 'Talk to us',
    ctaTo: '/register',
  },
]

/** Why the numbers are what they are. Stated openly, because a buyer who
 *  reverse-engineers your margin and finds it hidden stops trusting the rest. */
export const PRICING_NOTES = [
  {
    title: 'Runs are the meter, seats are the governance',
    body: 'Seats decide who can approve and who can see the audit log — which is what an organisation is actually buying. Consumption decides the bill. Per-seat-only pricing fell from 21% to 15% of SaaS in a year for this reason.',
  },
  {
    title: 'Overage is priced above worst-case token cost',
    body: 'A complex run with retries costs us roughly $1.15 in inference at list model prices. Included runs work out at $0.80 on Team and $0.70 on Growth, and overage is set so that heavy usage is accretive rather than something we quietly have to discourage.',
  },
  {
    title: 'Bring your own key and the inference bill is yours',
    body: 'Every plan can point at your own Anthropic, OpenAI, Azure or Ollama credentials. On Free it is required — which is why the free tier can be genuinely free rather than a seven-day trial wearing a costume.',
  },
  {
    title: 'A run has a budget, and it is enforced',
    body: 'Set a per-run cost cap and the orchestrator aborts a run that exceeds it mid-flight. An agent that loops is a billing incident on most platforms; here it is a stopped run and a notification.',
  },
] as const

export const FAQS = [
  {
    q: 'What exactly is a "run"?',
    a: 'One ticket taken through one pod: plan, code, QA, review, approval, deploy. Retries inside a run are not billed as new runs — if the QA agent sends work back to the Coder twice, that is still one run.',
  },
  {
    q: 'Do the agents get write access to my repository?',
    a: 'They open branches and pull requests through the connection you authorise, and they merge only after the gate clears. OAuth tokens are encrypted at rest with Fernet. You can scope the connection to specific repositories, and protected paths in a policy stop an agent touching files you have fenced off regardless of what the ticket said.',
  },
  {
    q: 'What happens when a policy blocks a deploy?',
    a: 'The run returns to the approval gate — it is not failed. Failing it would destroy work that may be perfectly good and would teach people to route around the gate, which is the opposite of the point. The block, its reason, and the policy that produced it are all written to the audit log.',
  },
  {
    q: 'Can I self-host it?',
    a: 'Yes, on the Enterprise plan. The platform ships with Dockerfiles, an nginx config and a compose profile, runs against stock PostgreSQL 15, and needs no external vendor to function: embeddings fall back to a local deterministic embedder, and with no Stripe key configured, plan changes simply apply directly.',
  },
  {
    q: 'Which models can it use?',
    a: 'Anthropic by default, plus OpenAI, Azure OpenAI, any OpenAI-compatible endpoint, and local Ollama. Model choice is per agent, so your Planner and your Reviewer do not have to be the same model, and every call is metered and costed either way.',
  },
  {
    q: 'How honest is this page?',
    a: 'Every figure here is either counted from the codebase, taken from our published pricing model, or attributed to a named third party. The product is new: we are not going to show you a customer count we do not have. The known limitations are written down in the repository rather than left for you to discover.',
  },
] as const
