import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { toast } from 'sonner'

interface PlatformStats {
  total_users: number
  total_organizations: number
  free_users: number
  teams_users: number
  enterprise_users: number
  teams_orgs: number
  enterprise_orgs: number
  legacy_orgs: number
}

interface SetPlanRequest {
  plan_type: string
}

export function usePlatformStats() {
  return useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: async () => {
      const { data } = await api.get<PlatformStats>('/admin/stats')
      return data
    },
  })
}

export function useSetUserPlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ userId, planType }: { userId: string; planType: string }) => {
      const { data } = await api.post(`/admin/users/${userId}/set-plan`, { plan_type: planType })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] })
      toast.success('User plan updated successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update user plan')
    },
  })
}

export function useSetOrgPlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ orgId, planType }: { orgId: string; planType: string }) => {
      const { data } = await api.post(`/admin/orgs/${orgId}/set-plan`, { plan_type: planType })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] })
      toast.success('Organization plan updated successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update organization plan')
    },
  })
}
