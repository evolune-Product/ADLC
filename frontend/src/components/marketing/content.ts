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
  /** Raw USD/month, for deriving the INR+GST display. `null` for a
   *  custom/talk-to-us price with nothing to convert. */
  priceUsd: number | null
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

/**
 * The USD→INR rate this page's INR toggle converts at, and why it is a rate
 * rather than a live quote: a marketing page re-fetching FX on every load
 * would make the price the least stable thing on the page, and a rate that
 * drifts a few paise from the day's actual mid-market rate is not what loses
 * or wins a deal — being unable to say the same number twice is. Revisit this
 * constant by hand periodically rather than wiring in a live feed.
 * Matches the ₹87/USD assumption in `documents/MARKET_RESEARCH_2026-08-25.md` §5.1.
 */
export const USD_TO_INR = 87

/** 18% GST on SaaS, per `documents/MARKET_RESEARCH_2026-08-25.md` §4.2. Shown
 *  inclusive, the way a buyer here actually reads a price. */
export const INDIA_GST_RATE = 0.18

export function formatInrWithGst(usd: number): string {
  const inrExGst = usd * USD_TO_INR
  const inrInclGst = Math.round(inrExGst * (1 + INDIA_GST_RATE))
  return `₹${inrInclGst.toLocaleString('en-IN')}`
}

/** Mirrors §2 of `documents/BUSINESS_PLAN_2026.md`. */
export const PLANS: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    price: '$0',
    priceUsd: 0,
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
    id: 'pro',
    name: 'Pro',
    price: '$100',
    priceUsd: 100,
    cadence: 'per month',
    // Honest, not a sales pitch: there is no real differentiation from Free
    // yet. Do not add a claim here that isn't built — see the plan's own
    // comment in metering_service.py.
    summary: 'Same limits as Free today — expanded capacity is coming.',
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
    cta: 'Start Pro',
    ctaTo: '/register',
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: '$5,000',
    priceUsd: 5000,
    cadence: 'per month',
    summary: 'For the org where a bad deploy is a board-level event.',
    runs: 'Unlimited',
    overage: 'Committed use',
    seats: '25 seats',
    features: [
      'Everything in Free, unlimited projects',
      '25 seats',
      'Approval policies, the Reviewer agent, and two-approver gates',
      'Slack, email and in-app alerts; audit log with retention controls',
      'ROI analytics, agent scorecards, Jira and Linear ticket sync',
      'Codebase memory, marketplace, multi-environment pipelines',
      'Public API v1, signed webhooks, SSO',
      'Self-hosted or VPC deployment, bring your own model provider (zero markup)',
      'Compliance evidence export, SLA and a named contact',
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
    title: 'Enterprise volume is committed, not metered per unit',
    body: 'A complex run with retries costs us roughly $1.15 in inference at list model prices. Enterprise pricing is quoted against a committed monthly volume rather than a per-run overage fee, so heavy usage is accretive rather than something we quietly have to discourage.',
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

/* ─────────────────────────────────────────────────────────────── positioning */

/**
 * Where Evolune OS sits against the two categories buyers are already using.
 *
 * Written to survive being read by someone who uses those products daily. The
 * claims are category-level and about *design intent*, never about quality or
 * benchmarks — we have not run a comparison and will not imply we have. The
 * honest position is that Evolune OS is complementary to both: it does not want to
 * be your editor, and it does not want to be the thing writing the code so
 * much as the thing deciding whether that code is allowed to ship.
 */
export const POSITIONING = {
  columns: [
    { key: 'ide', label: 'IDE assistants', note: 'Copilot, Cursor, Claude Code' },
    { key: 'agent', label: 'Autonomous agents', note: 'Devin, Factory droids' },
    { key: 'adlc', label: 'Evolune OS', note: 'This' },
  ],
  rows: [
    {
      question: 'Optimised for',
      ide: 'One developer, going faster',
      agent: 'One ticket, finished unattended',
      adlc: 'One organisation, shipping under control',
    },
    {
      question: 'Where the work happens',
      ide: 'In your editor, beside you',
      agent: 'In a sandbox, on its own',
      adlc: 'In your repo, as branches and pull requests',
    },
    {
      question: 'What stops a production deploy',
      ide: 'Your existing review process',
      agent: 'Whatever your CI already enforced',
      adlc: 'A named human, plus a policy that can override them',
    },
    {
      question: 'Where your standards live',
      ide: 'Rules files, per developer',
      agent: 'Prompts and configuration',
      adlc: 'Version-controlled skill markdown, shared by every agent',
    },
    {
      question: 'What you have afterwards',
      ide: 'A commit history',
      agent: 'A session transcript',
      adlc: 'An audit log: who approved what, on which policy, at what cost',
    },
    {
      question: 'Model choice',
      ide: 'The vendor’s',
      agent: 'The vendor’s',
      adlc: 'Per agent, across five providers, or your own local endpoint',
    },
  ],
  /** The claim we are not making, said out loud. */
  disclaimer:
    'These are design differences, not benchmarks. We have not run a head-to-head evaluation and this table does not imply one. Most teams that would use Evolune OS are already using something in the first column, and should keep it — Evolune OS governs what reaches production, it does not replace the editor you write in.',
} as const

/* ───────────────────────────────────────────────────────────────── security */

/**
 * The security posture, as it actually is in the repository today.
 *
 * `state: 'built'` means it is in the codebase and you can read it. `state:
 * 'absent'` means it is not, and it is listed anyway — a security page that
 * only lists what you have is how a procurement conversation ends badly six
 * weeks later.
 */
export type PostureItem = {
  title: string
  body: string
  state: 'built' | 'absent'
  /** Where to read it in the repository. */
  where?: string
}

export const SECURITY_POSTURE: ReadonlyArray<{
  group: string
  items: ReadonlyArray<PostureItem>
}> = [
  {
    group: 'Credentials and data',
    items: [
      {
        title: 'OAuth tokens encrypted at rest',
        body: 'GitHub, GitLab, Jira and Linear access and refresh tokens are Fernet-encrypted before they reach the database and decrypted only in the service layer at the moment of the call. Raw tokens are never returned by any endpoint.',
        state: 'built',
        where: 'backend/app/services/encryption.py',
      },
      {
        title: 'Bring your own model key',
        body: 'Point any plan at your own Anthropic, OpenAI, Azure or OpenAI-compatible credentials. Your prompts and your code then go to your tenancy, on your contract, under your data-processing terms — not ours.',
        state: 'built',
        where: 'backend/app/services/llm_service.py',
      },
      {
        title: 'We do not train on your code or prompts',
        body: 'There is no fine-tuning or training pipeline anywhere in this codebase — not for our own use, not for a vendor’s. On the BYO-key path your prompts and code go straight to the model provider you configured, governed by your contract with them, not ours. This is a written commitment, not a checkbox: audit the repository yourself rather than take our word for it.',
        state: 'built',
        where: 'backend/app/services/llm_service.py',
      },
      {
        title: 'Local inference for air-gapped installs',
        body: 'Ollama is a first-class provider, so a deployment can run with no outbound model traffic at all. Embeddings fall back to a local deterministic embedder rather than a hosted API, and the web fonts are bundled instead of fetched from a CDN.',
        state: 'built',
        where: 'backend/app/services/embedding_service.py',
      },
      {
        title: 'Retention enforcement',
        body: 'Indexed repository memory is pruned on a schedule against the configured retention window rather than accumulating indefinitely.',
        state: 'built',
        where: 'backend/app/tasks/memory_tasks.py',
      },
    ],
  },
  {
    group: 'Control and enforcement',
    items: [
      {
        title: 'Human approval before every production deploy',
        body: 'The orchestration graph halts at the gate and the Celery worker exits rather than blocking. Nothing merges or promotes until an approval is recorded against a named user.',
        state: 'built',
        where: 'backend/app/tasks/run_tasks.py',
      },
      {
        title: 'Policies that can overrule an approval',
        body: 'N-approver rules, minimum reviewer score, blocking severities, protected paths and branches, changed-file ceilings and per-run cost caps — scoped per environment. A violation returns the run to the gate; it never silently proceeds and never fails the run outright.',
        state: 'built',
        where: 'backend/app/services/policy_service.py',
      },
      {
        title: 'Scoped API keys and signed webhooks',
        body: 'Public API keys carry explicit scopes. Outbound webhooks are HMAC-signed with a per-endpoint secret and every delivery attempt is recorded, so a receiver can verify origin and detect replay.',
        state: 'built',
        where: 'backend/app/services/webhook_service.py',
      },
      {
        title: 'Single sign-on, with enforcement',
        body: 'Per-organisation OpenID Connect: authorization code flow with PKCE, the ID token verified against the provider’s published signing keys, nonce replay protection, and a domain re-check so a permissive identity provider cannot become a route into another tenant. Turning on enforcement refuses password sign-in for the claimed domains outright rather than offering SSO alongside it.',
        state: 'built',
        where: 'backend/app/services/sso_service.py',
      },
      {
        title: 'Per-run budget cap',
        body: 'A run that exceeds its configured cost ceiling is aborted mid-flight. An agent that loops is a stopped run and a notification rather than an invoice.',
        state: 'built',
        where: 'backend/app/services/metering_service.py',
      },
    ],
  },
  {
    group: 'Evidence',
    items: [
      {
        title: 'Every mutating request is audited',
        body: 'Middleware records the actor, action, entity and timestamp for every successful POST, PUT, PATCH and DELETE across the whole API — not only the endpoints someone remembered to instrument.',
        state: 'built',
        where: 'backend/app/middleware/audit_middleware.py',
      },
      {
        title: 'Compliance posture and evidence export',
        body: 'A posture endpoint and a CSV evidence export exist so the answer to “show me who approved last Tuesday’s deploy, under which policy, against which reviewer score” is a download rather than an afternoon of log archaeology.',
        state: 'built',
        where: 'backend/app/routers/governance.py',
      },
      {
        title: 'Cost attribution per run, per agent, per model',
        body: 'Every model call is metered with token counts and costed in integer millicents — no floating point anywhere in the billing path.',
        state: 'built',
        where: 'backend/app/services/metering_service.py',
      },
    ],
  },
  {
    group: 'Not in place yet',
    items: [
      {
        title: 'SOC 2 / ISO 27001',
        body: 'No certification and no audit in progress. We are not going to display a badge we have not earned. If a certification is a hard requirement for your procurement process today, Evolune OS will not clear it today.',
        state: 'absent',
      },
      {
        title: 'SAML, and SCIM directory provisioning',
        body: 'OIDC single sign-on is built (see “Control and enforcement”), which covers Okta, Entra ID, Google Workspace, Auth0, Keycloak and PingFederate. SAML-only identity providers are not supported, and there is no SCIM endpoint — users are provisioned when they first sign in, and de-provisioning means removing them from the organisation here as well as in your directory.',
        state: 'absent',
      },
      {
        title: 'Penetration test report',
        body: 'No third-party penetration test has been commissioned. The platform has 53 backend unit tests; that is a correctness check, not a security assessment, and it would be dishonest to present it as one.',
        state: 'absent',
      },
    ],
  },
]
