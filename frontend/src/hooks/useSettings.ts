import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '@/lib/api'
import type { User } from '@/types'

export interface SettingsData {
  user:               User
  llm_model:          string
  api_key_configured: boolean
  api_key_hint:       string | null
}

const KEY = ['settings']

export function useSettings() {
  return useQuery<SettingsData>({
    queryKey: KEY,
    queryFn: () => api.get('/settings').then((r) => r.data),
    staleTime: 60_000,
  })
}

export function useUpdateProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name?: string; org_name?: string }) =>
      api.put('/settings', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY })
      qc.invalidateQueries({ queryKey: ['auth', 'me'] })
      toast.success('Profile updated')
    },
    onError: () => toast.error('Failed to update profile'),
  })
}
