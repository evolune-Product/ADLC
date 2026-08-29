/**
 * useIntegrations — model providers, plus the read side of the plugin catalogue.
 *
 * Both catalogues are served annotated with what this workspace has already
 * connected, so each page is one query rather than a catalogue fetch plus a
 * credentials fetch stitched together on the client. That is not just fewer
 * requests: two independent queries guarantee a frame where every provider
 * renders as "not connected" before the second resolves.
 *
 * Connecting and re-verifying a plugin used to live here too
 * (useConnectPlugin / useVerifyConnection) — both moved to useConnections.ts
 * as useConnectCatalogItem / useTestConnection, since they write into the same
 * `connections` table the Connections page already owns. usePlugins() stays
 * here: it's a read of the catalogue for the connect-gallery UI, not a write.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api, { getApiError } from '@/lib/api'
import type {
  ModelCredential, PluginCatalog, ProviderCatalog,
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
