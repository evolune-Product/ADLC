import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type { Run } from '@/types'

interface DashboardStats {
  total_projects:    number
  active_runs:       number
  pending_approvals: number
  skills_configured: number
  recent_runs:       Run[]
}

export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => api.get('/dashboard/stats').then((r) => r.data),
    staleTime: 30_000,
  })
}

// ── Company OS step 20 ──────────────────────────────────────────────────────

export interface CompanyDashboard {
  scope: 'org' | 'department' | 'member'
  department_ids: string[] | null
  work: { by_status: Record<string, number>; total: number }
  workflow_executions: { by_status: Record<string, number>; total: number }
  pending_approvals: number
  pending_approvals_breakdown: { work: number; workflow: number }
  agent_activity: { agent_task_runs_last_30d: number }
  workflow_health: {
    workflow_id: string; name: string; total_executions: number
    completed: number; failed: number; success_rate: number
  }[]
  integration_health: Record<string, number> | null
  recent_conversations: {
    id: string; channel_id: string; preview: string; kind: string; created_at: string | null
  }[]
  usage: {
    plan: string; plan_name: string; allowed: boolean; reason: string | null
    runs_used: number; runs_included: number; runs_remaining: number
    overage_runs: number; overage_cents: number; spend_usd: number
    period_start: string; period_end: string
  }
  generated_at: string
}

export function useCompanyDashboard() {
  return useQuery<CompanyDashboard>({
    queryKey: ['company-dashboard'],
    queryFn: () => api.get('/company-dashboard').then((r) => r.data),
    staleTime: 30_000,
  })
}
