import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

export interface UsageLimit {
  used: number
  limit: number
}

export interface UsageLimits {
  projects: UsageLimit
  agents: UsageLimit
  pods: UsageLimit
  skills: UsageLimit
  github_connections: UsageLimit
  jira_connections: UsageLimit
  deployed_projects: UsageLimit
}

export function useUsageLimits() {
  return useQuery({
    queryKey: ['usage-limits'],
    queryFn: async () => {
      const { data } = await api.get<UsageLimits>('/dashboard/usage')
      return data
    },
  })
}
