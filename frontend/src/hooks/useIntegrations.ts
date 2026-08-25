/**
 * useIntegrations — model providers and plugins.
 *
 * Both catalogues are served annotated with what this workspace has already
 * connected, so each page is one query rather than a catalogue fetch plus a
 * credentials fetch stitched together on the client. That is not just fewer
 * requests: two independent queries guarantee a frame where every provider
 * renders as "not connected" before the second resolves.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api, { getApiError } from '@/lib/api'
import type {
  ConnectResult, ModelCredential, PluginCatalog, ProviderCatalog,
} from '@/types/integrations'

const err = (fallback: string) => (e: unknown) => toast.error(getApiError(e, fallback))

export const intKeys = {
  providers: ['integrations', 'providers'] as const,
  plugins: ['integrations', 'plugins'] as const,
}

// ═══ Model providers ══════════════════════════════════════════════════════════

export function useProviders() {
  return useQuery<ProviderCatalog>({
    queryKey: intKeys.providers,
    queryFn: () => api.get('/providers').then((r) => r.data),
  })
}

export function useSaveCredential() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ provider, ...body }: {
      provider: string
      api_key?: string
      base_url?: string
      label?: string
      default_model?: string
      price_overrides?: Record<string, { input: number; output: number }>
    }) => api.put(`/providers/credentials/${provider}`, body).then((r) => r.data as ModelCredential),
    onSuccess: (cred) => {
      qc.invalidateQueries({ queryKey: intKeys.providers })
      toast.success(`${cred.label ?? cred.provider} saved — test it to confirm the key works`)
    },
    onError: err('Could not save that credential'),
  })
}

export function useDeleteCredential() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (provider: string) => api.delete(`/providers/credentials/${provider}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: intKeys.providers })
      toast.success('Credential removed')
    },
    onError: err('Could not remove that credential'),
  })
}

export function useTestCredential() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (provider: string) =>
      api.post(`/providers/credentials/${provider}/test`)
        .then((r) => r.data as ModelCredential & { ok: boolean }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: intKeys.providers })
      // The vendor's own message is far more actionable than ours — it says
      // "insufficient_quota" or "model not found", so it is surfaced verbatim.
      if (data.ok) toast.success(data.status_detail ?? 'Key works')
      else toast.error(data.status_detail ?? 'The provider rejected that key')
    },
    onError: err('Could not reach that provider'),
  })
}

// ═══ Plugins ══════════════════════════════════════════════════════════════════

export function usePlugins() {
  return useQuery<PluginCatalog>({
    queryKey: intKeys.plugins,
    queryFn: () => api.get('/plugins').then((r) => r.data),
  })
}

export function useConnectPlugin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ key, ...body }: {
      key: string; name?: string; token?: string; url?: string; user?: string; extra?: string
    }) => api.post(`/plugins/${key}/connect`, body).then((r) => r.data as ConnectResult),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: intKeys.plugins })
      qc.invalidateQueries({ queryKey: ['connections'] })
      // A failed verification still created the connection, so this is a
      // warning rather than an error — the token is saved and can be fixed in
      // place instead of retyping the whole form.
      if (data.verified) toast.success(`${data.name} connected${data.display_name ? ` as ${data.display_name}` : ''}`)
      else toast.warning(`Saved, but not verified — ${data.detail}`)
    },
    onError: err('Could not connect that plugin'),
  })
}

export function useVerifyConnection() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (connectionId: string) =>
      api.post(`/plugins/connections/${connectionId}/verify`).then((r) => r.data),
    onSuccess: (data: { verified: boolean; detail: string }) => {
      qc.invalidateQueries({ queryKey: intKeys.plugins })
      if (data.verified) toast.success(data.detail || 'Still connected')
      else toast.error(data.detail || 'Verification failed')
    },
    onError: err('Could not verify that connection'),
  })
}
