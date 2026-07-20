import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { Organization } from '@/types'

const KEY = ['orgs']

export function useOrgs() {
  return useQuery<Organization[]>({
    queryKey: KEY,
    queryFn: () => api.get('/orgs/').then((r) => r.data),
  })
}

export function useCreateOrg() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string }) => api.post('/orgs/', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

export function useUpdateOrg() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; name?: string; avatar_url?: string }) =>
      api.put(`/orgs/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}

export function useDeleteOrg() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/orgs/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  })
}
