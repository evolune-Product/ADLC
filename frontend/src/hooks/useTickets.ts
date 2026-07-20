import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '@/lib/api'
import type { Ticket } from '@/types'

export function useTickets(projectId: string) {
  return useQuery<Ticket[]>({
    queryKey: ['tickets', projectId],
    queryFn: () => api.get(`/projects/${projectId}/tickets`).then((r) => r.data),
    enabled: !!projectId,
  })
}

export function useTicket(projectId: string, ticketId: string) {
  return useQuery<Ticket>({
    queryKey: ['tickets', projectId, ticketId],
    queryFn: () => api.get(`/projects/${projectId}/tickets/${ticketId}`).then((r) => r.data),
    enabled: !!projectId && !!ticketId,
  })
}

export function useSyncTickets(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post(`/projects/${projectId}/tickets/sync`).then((r) => r.data),
    onSuccess: (data: Ticket[]) => {
      qc.setQueryData(['tickets', projectId], data)
      toast.success(`Synced ${data.length} tickets from Jira`)
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err.response?.data?.detail ?? 'Failed to sync tickets')
    },
  })
}
