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
