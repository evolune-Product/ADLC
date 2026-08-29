import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { AuditLogEntry } from '@/hooks/useAudit'

export interface WorkItem {
  id:                  string
  organization_id:     string
  department_id:       string | null
  team_id:              string | null
  requester_user_id:    string
  type:                 string
  title:                string
  description:          string | null
  priority:             string | null
  context:              Record<string, unknown>
  status:               string
  assigned_user_id:     string | null
  assigned_agent_id:    string | null
  workflow_id:          string | null
  approval_state:       string | null
  routing_confidence:   string | null
  routing_reasoning:    string | null
  created_at:           string
  updated_at:           string
  completed_at:         string | null
}

interface RunSummary {
  id:            string
  project_id:    string
  status:        string
  pr_url:        string | null
  current_step:  string | null
  created_at:    string | null
}

export interface DepartmentSummary {
  id:                 string
  name:               string
  active_work_count:  number
  member_count:       number
}

export interface DeskData {
  pending_work:       WorkItem[]
  pending_approvals: {
    runs: RunSummary[]
    work: WorkItem[]
  }
  recent_activity:    AuditLogEntry[]
  department_summary: DepartmentSummary[]
}

const KEY = ['desk']

export function useDesk() {
  return useQuery<DeskData>({
    queryKey: KEY,
    queryFn: () => api.get('/desk').then((r) => r.data),
    staleTime: 15_000,
  })
}

export function useCreateDeskRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { title: string; description?: string }) =>
      api.post('/desk/request', body).then((r) => r.data as WorkItem),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  })
}
