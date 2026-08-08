/**
 * usePlatform — data hooks for the commercial, governance and intelligence layer.
 *
 * Grouped in one file because these surfaces share cache keys (a plan change
 * invalidates quota, a run approval invalidates analytics) and splitting them
 * would mean re-declaring the same invalidation graph six times.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api, { getApiError } from '@/lib/api'
import type {
  AgentScore, AnalyticsPoint, AnalyticsSummary, ApiKeyRecord, ApprovalPolicy,
  BillingState, DeploymentRecord, MemoryHit, MemoryStatus, Notification,
  NotificationSettings, Plan, ReviewResult, SourceReadResult, Template, WebhookDelivery, WebhookRecord,
  ComplianceControl,
} from '@/types/platform'

const err = (fallback: string) => (e: unknown) => toast.error(getApiError(e, fallback))

// ═══ Billing ══════════════════════════════════════════════════════════════════

export function useBilling() {
  return useQuery<BillingState>({
    queryKey: ['billing'],
    queryFn: () => api.get('/billing').then((r) => r.data),
  })
}

export function usePlans() {
  return useQuery<Plan[]>({
    queryKey: ['billing', 'plans'],
    queryFn: () => api.get('/billing/plans').then((r) => r.data),
    staleTime: 5 * 60_000,
  })
}

export function useCheckout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (plan: string) =>
      api.post('/billing/checkout', { plan }).then((r) => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['billing'] })
      if (data.simulated) toast.success('Plan updated (Stripe not configured — applied directly)')
      else window.location.href = data.url
    },
    onError: err('Could not start checkout'),
  })
}

export function useBillingPortal() {
  return useMutation({
    mutationFn: () => api.post('/billing/portal').then((r) => r.data),
    onSuccess: (data) => {
      if (data.url && !data.simulated) window.location.href = data.url
      else toast.info('Billing portal is unavailable without Stripe configured')
    },
    onError: err('Could not open the billing portal'),
  })
}

export function useSetLlmKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { provider: string; api_key: string }) =>
      api.put('/billing/llm-key', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['billing'] })
      toast.success('Model provider key saved — runs will use your key from now on')
    },
    onError: err('Could not save the provider key'),
  })
}

export function useClearLlmKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.delete('/billing/llm-key'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['billing'] })
      toast.success('Reverted to the platform model key')
    },
  })
}

// ═══ Notifications ════════════════════════════════════════════════════════════

export function useNotifications(unreadOnly = false) {
  return useQuery<{ notifications: Notification[]; unread_count: number }>({
    queryKey: ['notifications', unreadOnly],
    queryFn: () =>
      api.get('/notifications', { params: { unread_only: unreadOnly } }).then((r) => r.data),
    refetchInterval: 60_000,
  })
}

export function useMarkRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/notifications/${id}/read`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })
}

export function useMarkAllRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post('/notifications/read-all'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })
}

export function useNotificationSettings() {
  return useQuery<NotificationSettings>({
    queryKey: ['notifications', 'settings'],
    queryFn: () => api.get('/notifications/settings').then((r) => r.data),
  })
}

export function useUpdateNotificationSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<NotificationSettings>) =>
      api.put('/notifications/settings', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications', 'settings'] })
      toast.success('Notification preferences saved')
    },
    onError: err('Could not save preferences'),
  })
}

export function useTestSlack() {
  return useMutation({
    mutationFn: (webhook_url: string) =>
      api.post('/notifications/test-slack', { webhook_url }).then((r) => r.data),
    onSuccess: () => toast.success('Test message delivered to Slack'),
    onError: err('Slack rejected the test message'),
  })
}

// ═══ Analytics ════════════════════════════════════════════════════════════════

export function useAnalyticsSummary(days = 30, manualHours?: number, hourlyRate?: number) {
  return useQuery<AnalyticsSummary>({
    queryKey: ['analytics', 'summary', days, manualHours, hourlyRate],
    queryFn: () =>
      api
        .get('/analytics/summary', {
          params: { days, manual_hours: manualHours, hourly_rate: hourlyRate },
        })
        .then((r) => r.data),
  })
}

export function useAnalyticsTimeseries(days = 30) {
  return useQuery<AnalyticsPoint[]>({
    queryKey: ['analytics', 'timeseries', days],
    queryFn: () => api.get('/analytics/timeseries', { params: { days } }).then((r) => r.data),
  })
}

export function useAgentScores(days = 30) {
  return useQuery<AgentScore[]>({
    queryKey: ['analytics', 'agents', days],
    queryFn: () => api.get('/analytics/agents', { params: { days } }).then((r) => r.data),
  })
}

export function useDeployments(projectId?: string) {
  return useQuery<DeploymentRecord[]>({
    queryKey: ['deployments', projectId],
    queryFn: () =>
      api.get('/deployments', { params: { project_id: projectId } }).then((r) => r.data),
  })
}

// ═══ Review findings + feedback ═══════════════════════════════════════════════

export function useRunFindings(runId: string) {
  return useQuery<ReviewResult>({
    queryKey: ['runs', runId, 'findings'],
    queryFn: () => api.get(`/runs/${runId}/findings`).then((r) => r.data),
    enabled: !!runId,
  })
}

export function useRunSources(runId: string) {
  return useQuery<SourceReadResult>({
    queryKey: ['runs', runId, 'sources'],
    queryFn: () => api.get(`/runs/${runId}/sources`).then((r) => r.data),
    enabled: !!runId,
  })
}

export function useSubmitFeedback(runId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { rating: number; agent_role?: string; category?: string; comment?: string }) =>
      api.post(`/runs/${runId}/feedback`, body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['runs', runId, 'feedback'] })
      qc.invalidateQueries({ queryKey: ['analytics', 'agents'] })
      toast.success('Thanks — this tunes your agent scorecards')
    },
    onError: err('Could not record feedback'),
  })
}

// ═══ Governance ═══════════════════════════════════════════════════════════════

export function usePolicies() {
  return useQuery<{ policies: ApprovalPolicy[]; default: Record<string, unknown> }>({
    queryKey: ['policies'],
    queryFn: () => api.get('/policies').then((r) => r.data),
  })
}

export function useSavePolicy() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<ApprovalPolicy> & { id?: string }) =>
      (id ? api.put(`/policies/${id}`, body) : api.post('/policies', body)).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['policies'] })
      toast.success('Policy saved')
    },
    onError: err('Could not save the policy'),
  })
}

export function useDeletePolicy() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/policies/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['policies'] })
      toast.success('Policy deleted')
    },
  })
}

export function useApiKeys() {
  return useQuery<{ keys: ApiKeyRecord[]; available_scopes: string[] }>({
    queryKey: ['apikeys'],
    queryFn: () => api.get('/apikeys').then((r) => r.data),
  })
}

export function useCreateApiKey() {
  const qc = useQueryClient()
  return useMutation<ApiKeyRecord, unknown, { name: string; scopes: string[] }>({
    mutationFn: (body) => api.post('/apikeys', body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['apikeys'] }),
    onError: err('Could not create the API key'),
  })
}

export function useRevokeApiKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/apikeys/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['apikeys'] })
      toast.success('API key revoked')
    },
  })
}

export function useWebhooks() {
  return useQuery<{ webhooks: WebhookRecord[]; available_events: string[]; signature_header: string }>({
    queryKey: ['webhooks'],
    queryFn: () => api.get('/webhooks').then((r) => r.data),
  })
}

export function useCreateWebhook() {
  const qc = useQueryClient()
  return useMutation<WebhookRecord, unknown, { url: string; events: string[] }>({
    mutationFn: (body) => api.post('/webhooks', body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webhooks'] }),
    onError: err('Could not create the webhook'),
  })
}

export function useDeleteWebhook() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/webhooks/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webhooks'] }),
  })
}

export function useTestWebhook() {
  return useMutation({
    mutationFn: (id: string) => api.post(`/webhooks/${id}/test`).then((r) => r.data),
    onSuccess: (d) =>
      d.delivered ? toast.success('Webhook delivered') : toast.error('Endpoint did not accept the delivery'),
    onError: err('Delivery failed'),
  })
}

export function useWebhookDeliveries(id: string) {
  return useQuery<WebhookDelivery[]>({
    queryKey: ['webhooks', id, 'deliveries'],
    queryFn: () => api.get(`/webhooks/${id}/deliveries`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCompliance() {
  return useQuery<{ controls: ComplianceControl[]; deployment_mode: string; audit_retention_days: number }>({
    queryKey: ['compliance'],
    queryFn: () => api.get('/compliance/posture').then((r) => r.data),
  })
}

// ═══ Catalog / marketplace ════════════════════════════════════════════════════

export function useTemplates(kind?: string) {
  return useQuery<{ templates: Template[]; categories: string[] }>({
    queryKey: ['templates', kind],
    queryFn: () => api.get('/templates', { params: { kind } }).then((r) => r.data),
  })
}

export function useMarketplace(kind?: string, sort = 'installs') {
  return useQuery<Template[]>({
    queryKey: ['marketplace', kind, sort],
    queryFn: () => api.get('/marketplace', { params: { kind, sort } }).then((r) => r.data),
  })
}

export function useInstallTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (slug: string) => api.post(`/templates/${slug}/install`).then((r) => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['skills'] })
      qc.invalidateQueries({ queryKey: ['agents'] })
      qc.invalidateQueries({ queryKey: ['pods'] })
      qc.invalidateQueries({ queryKey: ['marketplace'] })
      toast.success(data.message ?? 'Installed')
    },
    onError: err('Install failed'),
  })
}

export function usePublishTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { kind: string; resource_id: string; visibility?: string; readme_md?: string }) =>
      api.post('/marketplace/publish', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['marketplace'] })
      toast.success('Published to the marketplace')
    },
    onError: err('Could not publish'),
  })
}

// ═══ Memory ═══════════════════════════════════════════════════════════════════

export function useMemoryStatus(projectId: string) {
  return useQuery<MemoryStatus>({
    queryKey: ['memory', projectId],
    queryFn: () => api.get(`/projects/${projectId}/memory`).then((r) => r.data),
    enabled: !!projectId,
    // Poll while an index is building so the panel reflects progress.
    refetchInterval: (q) => (q.state.data?.status === 'indexing' ? 5_000 : false),
  })
}

export function useIndexMemory(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post(`/projects/${projectId}/memory/index`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['memory', projectId] })
      toast.success('Indexing started — agents will use this memory on the next run')
    },
    onError: err('Could not start indexing'),
  })
}

export function useSearchMemory(projectId: string) {
  return useMutation<MemoryHit[], unknown, string>({
    mutationFn: (query) =>
      api.post(`/projects/${projectId}/memory/search`, { query, k: 8 }).then((r) => r.data),
    onError: err('Search failed'),
  })
}

export function useAddMemoryNote(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { title: string; content: string; kind?: string }) =>
      api.post(`/projects/${projectId}/memory/notes`, body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['memory', projectId] })
      toast.success('Note added to project memory')
    },
    onError: err('Could not add the note'),
  })
}
