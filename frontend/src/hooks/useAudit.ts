import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

export interface AuditLogEntry {
  id:          string
  user_id:     string | null
  action:      string
  entity_type: string | null
  entity_id:   string | null
  metadata:    Record<string, unknown>
  created_at:  string
}

interface AuditListResponse {
  total: number
  skip:  number
  limit: number
  items: AuditLogEntry[]
}

interface AuditParams {
  action?:      string
  entity_type?: string
  skip?:        number
  limit?:       number
}

export function useAuditLogs(params: AuditParams = {}) {
  const search = new URLSearchParams()
  if (params.action)      search.set('action',      params.action)
  if (params.entity_type) search.set('entity_type', params.entity_type)
  if (params.skip)        search.set('skip',        String(params.skip))
  if (params.limit)       search.set('limit',       String(params.limit ?? 50))
  const qs = search.toString()

  return useQuery<AuditListResponse>({
    queryKey: ['audit', params],
    queryFn: () => api.get(`/audit${qs ? `?${qs}` : ''}`).then((r) => r.data),
    staleTime: 10_000,
  })
}

export function auditExportUrl(params: { action?: string; entity_type?: string } = {}): string {
  const search = new URLSearchParams()
  if (params.action)      search.set('action',      params.action)
  if (params.entity_type) search.set('entity_type', params.entity_type)
  const qs = search.toString()
  const base = (import.meta.env.VITE_API_URL || 'http://localhost:8000')
  return `${base}/audit/export${qs ? `?${qs}` : ''}`
}
