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

/**
 * A human confirms the work is done and closes the ticket themselves — the
 * platform never does this automatically (see writeback_service.close_ticket
 * on the backend). Posts a comment naming who closed it and attempts a
 * transition to the target status (default "Done").
 */
export function useCloseTicket(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ ticketId, note, status }: { ticketId: string; note?: string; status?: string }) =>
      api.post(`/projects/${projectId}/tickets/${ticketId}/close`, { note, status })
        .then((r) => r.data as Ticket & { commented: boolean; moved: boolean }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['tickets', projectId] })
      qc.setQueryData(['tickets', projectId, data.id], data)
      if (data.moved) {
        toast.success(`Marked as ${data.status}`)
      } else {
        toast.warning('Comment posted, but the ticket could not be moved — check that a matching transition exists.')
      }
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err.response?.data?.detail ?? 'Could not close this ticket')
    },
  })
}
