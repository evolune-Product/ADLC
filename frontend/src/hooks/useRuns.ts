import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '@/lib/api'
import type { Run } from '@/types'

const KEY = ['runs']

export function useRuns(params?: { status?: string; project_id?: string }) {
  const search = new URLSearchParams()
  if (params?.status)     search.set('run_status', params.status)
  if (params?.project_id) search.set('project_id', params.project_id)
  const qs = search.toString()

  return useQuery<Run[]>({
    queryKey: [...KEY, params],
    queryFn: () => api.get(`/runs${qs ? `?${qs}` : ''}`).then((r) => r.data),
  })
}

export function useProjectRuns(projectId: string) {
  return useQuery<Run[]>({
    queryKey: [...KEY, 'project', projectId],
    queryFn: () => api.get(`/projects/${projectId}/runs`).then((r) => r.data),
    enabled: !!projectId,
  })
}

export function useRun(runId: string) {
  return useQuery<Run>({
    queryKey: [...KEY, runId],
    queryFn: () => api.get(`/runs/${runId}`).then((r) => r.data),
    enabled: !!runId,
    refetchInterval: (query) => {
      const run = query.state.data as Run | undefined
      if (!run) return 5000
      // Keep polling while active
      if (['queued', 'running'].includes(run.status)) return 3000
      return false
    },
  })
}

export function useCreateRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { project_id: string; ticket_id?: string; pod_id: string }) =>
      api.post('/runs', data).then((r) => r.data),
    onSuccess: (run: Run) => {
      qc.invalidateQueries({ queryKey: KEY })
      toast.success('Run started')
      return run
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err.response?.data?.detail ?? 'Failed to start run')
    },
  })
}

export function useRunDiff(runId: string, enabled = true) {
  return useQuery<
    { filename: string; status: string; additions: number; deletions: number; patch: string }[]
  >({
    queryKey: [...KEY, runId, 'diff'],
    queryFn: () => api.get(`/runs/${runId}/diff`).then((r) => r.data),
    enabled: !!runId && enabled,
    staleTime: 5 * 60_000,
  })
}

export function useApproveRun(runId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { decision: string; comment?: string }) =>
      api.post(`/runs/${runId}/approve`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [...KEY, runId] })
      qc.invalidateQueries({ queryKey: KEY })
      toast.success('Decision submitted')
    },
    onError: () => toast.error('Failed to submit decision'),
  })
}

export function useRetryRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) => api.post(`/runs/${runId}/retry`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY })
      toast.success('Run retried')
    },
    onError: () => toast.error('Failed to retry run'),
  })
}

export function useCancelRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) => api.delete(`/runs/${runId}/cancel`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY })
      toast.success('Run cancelled')
    },
    onError: () => toast.error('Failed to cancel run'),
  })
}
