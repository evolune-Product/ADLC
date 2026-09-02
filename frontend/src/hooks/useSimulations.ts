import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api from '@/lib/api'
import type { SimulationRun } from '@/types/simulation'

const KEY = ['simulations']

export function useSimulations(params?: { persona_id?: string; status?: string }) {
  const search = new URLSearchParams()
  if (params?.persona_id) search.set('persona_id', params.persona_id)
  if (params?.status)     search.set('run_status', params.status)
  const qs = search.toString()

  return useQuery<SimulationRun[]>({
    queryKey: [...KEY, params],
    queryFn: () => api.get(`/simulations/${qs ? `?${qs}` : ''}`).then((r) => r.data),
  })
}

export function useSimulation(id: string | undefined) {
  return useQuery<SimulationRun>({
    queryKey: [...KEY, id],
    queryFn: () => api.get(`/simulations/${id}`).then((r) => r.data),
    enabled: !!id,
    refetchInterval: (query) => {
      const run = query.state.data as SimulationRun | undefined
      if (!run) return 3000
      return ['pending', 'running'].includes(run.status) ? 2500 : false
    },
  })
}

export function useCreateSimulation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { persona_id: string; target_url: string; ticket_id?: string; max_steps?: number }) =>
      api.post('/simulations/', data).then((r) => r.data as SimulationRun),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY })
      toast.success('Simulation started')
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err.response?.data?.detail ?? 'Failed to start simulation')
    },
  })
}
