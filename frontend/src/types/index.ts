// ─── Organizations ───────────────────────────────────────────────────────────
export type OrgRole = 'owner' | 'admin' | 'member' | 'viewer'
export type InviteRole = 'admin' | 'member' | 'viewer'
export type InviteStatus = 'pending' | 'accepted' | 'expired' | 'revoked'

export interface Organization {
  id: string
  name: string
  slug: string
  avatar_url?: string
  created_by: string
  created_at: string
  updated_at: string
  role?: OrgRole
}

export interface OrgMember {
  id: string
  org_id: string
  user_id: string
  user_name?: string
  user_email?: string
  user_avatar?: string
  role: OrgRole
  joined_at: string
}

export interface OrgInvitation {
  id: string
  org_id: string
  invited_by: string
  email: string
  role: InviteRole
  token: string
  status: InviteStatus
  expires_at?: string
  created_at: string
  accepted_at?: string
  invite_url?: string
}

// ─── Auth ────────────────────────────────────────────────────────────────────
export interface User {
  id: string
  email: string
  name: string
  avatar_url?: string
  org_name?: string
  created_at: string
}

// ─── Connections ─────────────────────────────────────────────────────────────
export type ConnectionType = 'github' | 'gitlab' | 'jira' | 'github_actions'
export type ConnectionStatus = 'pending' | 'connected' | 'error'

export interface Connection {
  id: string
  name: string
  type: ConnectionType
  status: ConnectionStatus
  workspace_url?: string
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

// ─── Skills ──────────────────────────────────────────────────────────────────
export type SkillCategory = 'dev' | 'qa' | 'devops' | 'planning' | 'custom'

export interface Skill {
  id: string
  name: string
  description?: string
  category: SkillCategory
  md_content: string
  version: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// ─── Agents ──────────────────────────────────────────────────────────────────
export type AgentRole = 'sprint' | 'dev' | 'qa' | 'devops' | 'custom'

export interface AgentSkillBinding {
  id: string        // AgentSkill record ID
  skill_id: string  // Skill ID
  skill_name: string
  priority: number
}

export interface Agent {
  id: string
  name: string
  role: AgentRole
  description?: string
  repo_connection_id?: string
  default_branch: string
  branch_prefix: string
  llm_model: string
  max_iterations: number
  is_active: boolean
  skills: AgentSkillBinding[]
  created_at: string
  updated_at: string
}

// ─── Pods ────────────────────────────────────────────────────────────────────
export interface PodAgent {
  id: string
  agent_id: string
  agent_name: string
  agent_role: string
  execution_order: number
  count: number
  on_failure: 'retry' | 'escalate' | 'stop'
  max_retries: number
}

export interface Pod {
  id: string
  name: string
  description?: string
  is_active: boolean
  agents: PodAgent[]
  created_at: string
  updated_at: string
}

// ─── Projects ────────────────────────────────────────────────────────────────
export type ProjectType = 'backend' | 'frontend' | 'fullstack' | 'mobile' | 'data' | 'other'

export interface DeployTarget {
  env: string
  branch: string
}

export interface Project {
  id: string
  name: string
  description?: string
  type: ProjectType
  repo_connection_id?: string
  repo_name?: string
  jira_connection_id?: string
  jira_project_key?: string
  pod_id?: string
  pod_name?: string
  context_md?: string
  deploy_targets: DeployTarget[]
  /** Ticket write-back config — see backend services/writeback_service.py. */
  writeback?: { enabled?: boolean; status_map?: Record<string, string> }
  status: 'active' | 'archived'
  created_at: string
  updated_at: string
}

// ─── Tickets ─────────────────────────────────────────────────────────────────
export type TicketType = 'bug' | 'feature' | 'task' | 'story'
export type TicketPriority = 'highest' | 'high' | 'medium' | 'low'

export interface Ticket {
  id: string
  project_id: string
  jira_id: string
  title: string
  description?: string
  type: TicketType
  priority: TicketPriority
  status: string
  assignee?: string
  jira_url?: string
  synced_at: string
}

// ─── Runs ────────────────────────────────────────────────────────────────────
export type RunStatus = 'queued' | 'running' | 'awaiting_approval' | 'approved' | 'failed' | 'completed'

export interface RunStep {
  id: string
  agent_role: string
  step_name: string
  status: 'running' | 'success' | 'failed' | 'skipped'
  input: Record<string, unknown>
  output: Record<string, unknown>
  log?: string
  duration_ms?: number
  created_at: string
}

export interface Run {
  id: string
  project_id: string
  ticket_id?: string
  ticket?: Ticket
  pod_id: string
  status: RunStatus
  branch_name?: string
  pr_url?: string
  pr_number?: number
  current_step?: string
  error_message?: string
  retry_count: number
  current_env_index: number   // -1 = awaiting PR review, N = awaiting deploy to env[N]
  deploy_targets: DeployTarget[]
  steps: RunStep[]
  started_at?: string
  completed_at?: string
  created_at: string
}

// ─── Audit ───────────────────────────────────────────────────────────────────
export interface AuditLog {
  id: string
  user_id: string
  user?: User
  action: string
  entity_type?: string
  entity_id?: string
  metadata: Record<string, unknown>
  created_at: string
}

// ─── API ─────────────────────────────────────────────────────────────────────
export interface ApiError {
  detail: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}
