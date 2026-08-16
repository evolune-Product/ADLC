// ─── Billing ─────────────────────────────────────────────────────────────────
export type PlanKey = 'free' | 'team' | 'growth' | 'enterprise'

export interface Plan {
  key: PlanKey
  name: string
  price_cents: number
  included_runs: number
  overage_cents_per_run: number
  seats: number
  max_projects: number
  run_budget_cents: number
  features: string[]
  requires_byo_key?: boolean
}

export interface Quota {
  plan: PlanKey
  plan_name: string
  allowed: boolean
  reason: string | null
  runs_used: number
  runs_included: number
  runs_remaining: number
  overage_runs: number
  overage_cents: number
  spend_usd: number
  period_start: string
  period_end: string
}

export interface BillingState {
  subscription: {
    plan: PlanKey
    plan_name: string
    status: string
    seats: number
    included_runs: number
    overage_cents_per_run: number
    run_budget_cents: number
    cancel_at_period_end: boolean
    current_period_end: string | null
    byo_llm_provider: string | null
    byo_llm_configured: boolean
    stripe_customer_id: string | null
  }
  quota: Quota
  usage_by_model: {
    model: string
    calls: number
    input_tokens: number
    output_tokens: number
    cost_usd: number
  }[]
  stripe_enabled: boolean
}

// ─── Notifications ───────────────────────────────────────────────────────────
export interface Notification {
  id: string
  type: string
  title: string
  body?: string
  link?: string
  severity: 'info' | 'warning' | 'critical'
  payload: Record<string, unknown>
  read: boolean
  created_at: string
}

export interface NotificationSettings {
  email_enabled: boolean
  slack_enabled: boolean
  slack_webhook_configured: boolean
  slack_webhook_url: string | null
  digest_enabled: boolean
  events: string[]
  available_events: string[]
}

// ─── Analytics ───────────────────────────────────────────────────────────────
export interface AnalyticsSummary {
  window_days: number
  runs_total: number
  runs_completed: number
  runs_failed: number
  runs_awaiting_approval: number
  success_rate: number
  median_cycle_hours: number
  median_approval_latency_hours: number
  spend_usd: number
  cost_per_completed_run_usd: number
  hours_saved: number
  money_saved_usd: number
  roi_multiple: number | null
  assumptions: { manual_hours_per_ticket: number; engineer_hourly_usd: number; note?: string }
}

export interface AnalyticsPoint {
  date: string
  runs: number
  completed: number
  failed: number
  spend_usd: number
}

export interface AgentScore {
  agent_role: string
  steps: number
  success_rate: number
  avg_duration_sec: number
  spend_usd: number
  thumbs_up: number
  thumbs_down: number
  quality_score: number | null
}

export interface DeploymentRecord {
  id: string
  run_id: string | null
  project_id: string
  environment: string
  branch: string | null
  sha: string | null
  status: 'succeeded' | 'failed' | 'rolled_back'
  approver_count: number
  message: string | null
  created_at: string
}

// ─── Review + feedback ───────────────────────────────────────────────────────
export type Severity = 'info' | 'low' | 'medium' | 'high' | 'critical'

export interface ReviewFinding {
  id: string
  severity: Severity
  category: string
  file_path: string | null
  line: number | null
  message: string
  suggestion: string | null
  posted_to_vcs: boolean
}

export interface ReviewResult {
  score: number | null
  count: number
  findings: ReviewFinding[]
}

// ─── Source reads ────────────────────────────────────────────────────────────
// What the agents read from outside the repository, and how well that read went.
// The sibling of ReviewFinding: findings ask whether the code is any good, this
// asks whether the brief it was written from was any good.

export interface SourceRead {
  id: string
  url: string
  title: string | null
  agent_role: string | null
  status: 'ok' | 'failed' | 'skipped'
  error: string | null
  read_score: number | null
  hallucination_risk: 'low' | 'medium' | 'high' | null
  html_bytes: number
  markdown_bytes: number
  tokens_before: number
  tokens_after: number
  flags: Array<{ severity: 'high' | 'medium' | 'low' | 'ok'; text: string }>
  latency_ms: number
  cached: boolean
}

export interface SourceReadResult {
  count: number
  failed: number
  /** The weakest read on the run — an average would hide one bad page behind four good ones. */
  worst_score: number | null
  tokens_before: number
  tokens_after: number
  tokens_saved: number
  sources: SourceRead[]
}

// ─── Governance ──────────────────────────────────────────────────────────────
export interface ApprovalPolicy {
  id: string
  name: string
  environment: string
  project_id: string | null
  min_approvers: number
  approver_roles: string[]
  require_review_pass: boolean
  min_review_score: number
  block_on_severity: Severity | null
  protected_paths: string[]
  protected_branches: string[]
  max_files_changed: number
  max_run_cost_cents: number
  is_active: boolean
  created_at: string
}

export interface ApiKeyRecord {
  id: string
  name: string
  prefix: string
  scopes: string[]
  last_used_at: string | null
  expires_at: string | null
  revoked: boolean
  created_at: string
  api_key?: string
}

export interface WebhookRecord {
  id: string
  url: string
  events: string[]
  is_active: boolean
  failure_count: number
  created_at: string
  secret?: string
}

export interface WebhookDelivery {
  id: string
  event: string
  ok: boolean
  status_code: number | null
  error: string | null
  duration_ms: number | null
  created_at: string
}

export interface ComplianceControl {
  id: string
  name: string
  status: string
  evidence: string
}

// ─── Sprint planning ──────────────────────────────────────────────────────────
export type SprintHealth = 'on_track' | 'at_risk' | 'blocked'

export interface BacklogTicket {
  id: string
  jira_id: string
  title: string
  type: string | null
  priority: string | null
}

export interface TicketEstimate {
  id: string
  ticket_id: string
  jira_id: string
  title: string
  story_points: number
  complexity_reasoning: string | null
  depends_on: string[]
  included_in_sprint: boolean
  risk: SprintHealth
}

export interface SprintPlan {
  id: string
  project_id: string
  capacity_points: number
  committed_points: number
  health: SprintHealth
  summary: string | null
  written_back: boolean
  created_at: string
  estimates: TicketEstimate[]
}

// ─── Catalog / marketplace ───────────────────────────────────────────────────
export type TemplateKind = 'skill' | 'agent' | 'pod'

export interface TemplateListing {
  id: string
  publisher_name: string | null
  visibility: string
  price_cents: number
  install_count: number
  rating: number
  rating_count: number
  is_verified: boolean
  readme_md: string | null
}

export interface Template {
  id: string
  slug: string
  kind: TemplateKind
  name: string
  description: string | null
  category: string | null
  tags: string[]
  version: string
  is_builtin: boolean
  payload: Record<string, unknown>
  listing: TemplateListing | null
}

// ─── Memory ──────────────────────────────────────────────────────────────────
export interface MemoryStatus {
  status: 'pending' | 'indexing' | 'ready' | 'failed'
  chunk_count: number
  file_count: number
  embedding_model: string
  embedding_backend: 'provider' | 'hashed'
  auto_update: boolean
  last_indexed_at: string | null
  error: string | null
  chunks_by_kind: Record<string, number>
}

export interface MemoryHit {
  id: string
  kind: string
  path: string | null
  title: string | null
  tokens: number
  excerpt: string
}
