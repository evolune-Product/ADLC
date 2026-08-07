import { useState } from 'react'
import { Copy, KeyRound, Plus, Trash2, Webhook } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import {
  useApiKeys, useCreateApiKey, useCreateWebhook, useDeleteWebhook,
  useRevokeApiKey, useTestWebhook, useWebhooks,
} from '@/hooks/usePlatform'

function CodeLine({ value }: { value: string }) {
  return (
    <div className="flex items-center gap-2 bg-muted rounded px-3 py-2 font-mono text-xs">
      <span className="truncate flex-1">{value}</span>
      <button
        onClick={() => {
          navigator.clipboard.writeText(value)
          toast.success('Copied')
        }}
        className="shrink-0 text-muted-foreground hover:text-foreground"
      >
        <Copy className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

export default function DeveloperPage() {
  const { data: keyData, isLoading } = useApiKeys()
  const { data: hookData } = useWebhooks()
  const createKey = useCreateApiKey()
  const revokeKey = useRevokeApiKey()
  const createHook = useCreateWebhook()
  const deleteHook = useDeleteWebhook()
  const testHook = useTestWebhook()

  const [keyName, setKeyName] = useState('')
  const [scopes, setScopes] = useState<string[]>(['runs:read'])
  const [freshKey, setFreshKey] = useState<string | null>(null)

  const [hookUrl, setHookUrl] = useState('')
  const [hookEvents, setHookEvents] = useState<string[]>([
    'run.awaiting_approval', 'run.completed', 'run.failed',
  ])
  const [freshSecret, setFreshSecret] = useState<string | null>(null)

  if (isLoading) return <LoadingSkeleton />

  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  return (
    <div className="space-y-6">
      <p className="onto-label mb-1">Developer</p>
      <PageHeader
        title="API keys and webhooks"
        subtitle="Trigger runs from CI, approve from ChatOps, and stream governed events into your own systems."
      />

      {/* ── API keys ─────────────────────────────────────────────────────── */}
      <div className="bg-card rounded-lg border border-border p-5 space-y-4">
        <div className="flex items-center gap-2">
          <KeyRound className="h-4 w-4" />
          <p className="font-medium">API keys</p>
        </div>

        <div className="flex flex-wrap gap-2 items-end">
          <label className="space-y-1 flex-1 min-w-[200px]">
            <span className="onto-label">Key name</span>
            <input
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
              placeholder="CI pipeline"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </label>
          <Button
            disabled={!keyName || createKey.isPending}
            onClick={() =>
              createKey.mutate(
                { name: keyName, scopes },
                {
                  onSuccess: (k) => {
                    setFreshKey(k.api_key ?? null)
                    setKeyName('')
                  },
                },
              )
            }
          >
            <Plus className="h-4 w-4 mr-2" /> Create key
          </Button>
        </div>

        <div className="flex flex-wrap gap-3">
          {(keyData?.available_scopes ?? []).map((scope) => (
            <label key={scope} className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={scopes.includes(scope)}
                onChange={(e) =>
                  setScopes((s) => (e.target.checked ? [...s, scope] : s.filter((x) => x !== scope)))
                }
              />
              <code className="text-xs">{scope}</code>
            </label>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          <code>runs:approve</code> is deliberately separate from <code>runs:write</code> — a CI
          token that starts work should not be able to wave its own work through the gate.
        </p>

        {freshKey && (
          <div className="rounded-md border border-[#E8632A] bg-[#E8632A]/5 p-3 space-y-2">
            <p className="text-sm font-medium">Copy this key now — it is not retrievable later.</p>
            <CodeLine value={freshKey} />
            <Button size="sm" variant="outline" onClick={() => setFreshKey(null)}>Done</Button>
          </div>
        )}

        {(keyData?.keys ?? []).length > 0 && (
          <div className="divide-y divide-border border border-border rounded-md">
            {keyData!.keys.map((k) => (
              <div key={k.id} className="px-3 py-2.5 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium">
                    {k.name}{' '}
                    {k.revoked && <span className="text-xs text-muted-foreground">(revoked)</span>}
                  </p>
                  <p className="text-xs text-muted-foreground font-mono truncate">
                    {k.prefix}… · {k.scopes.join(', ')}
                    {k.last_used_at && ` · last used ${new Date(k.last_used_at).toLocaleDateString()}`}
                  </p>
                </div>
                {!k.revoked && (
                  <Button size="sm" variant="outline" onClick={() => revokeKey.mutate(k.id)}>
                    Revoke
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}

        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground">Usage example</summary>
          <pre className="mt-2 bg-muted rounded p-3 text-xs overflow-x-auto">{`# Trigger a run from CI
curl -X POST ${apiBase}/v1/runs \\
  -H "Authorization: Bearer adlc_live_…" \\
  -H "Content-Type: application/json" \\
  -d '{"project_id":"<uuid>","ticket_id":"<uuid>"}'

# Poll it
curl ${apiBase}/v1/runs/<run_id> -H "Authorization: Bearer adlc_live_…"`}</pre>
        </details>
      </div>

      {/* ── Webhooks ─────────────────────────────────────────────────────── */}
      <div className="bg-card rounded-lg border border-border p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Webhook className="h-4 w-4" />
          <p className="font-medium">Outbound webhooks</p>
        </div>

        <div className="flex flex-wrap gap-2 items-end">
          <label className="space-y-1 flex-1 min-w-[240px]">
            <span className="onto-label">Endpoint URL</span>
            <input
              value={hookUrl}
              onChange={(e) => setHookUrl(e.target.value)}
              placeholder="https://hooks.example.com/adlc"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </label>
          <Button
            disabled={!hookUrl || createHook.isPending}
            onClick={() =>
              createHook.mutate(
                { url: hookUrl, events: hookEvents },
                {
                  onSuccess: (h) => {
                    setFreshSecret(h.secret ?? null)
                    setHookUrl('')
                  },
                },
              )
            }
          >
            <Plus className="h-4 w-4 mr-2" /> Add webhook
          </Button>
        </div>

        <div className="flex flex-wrap gap-3">
          {(hookData?.available_events ?? []).map((ev) => (
            <label key={ev} className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={hookEvents.includes(ev)}
                onChange={(e) =>
                  setHookEvents((s) => (e.target.checked ? [...s, ev] : s.filter((x) => x !== ev)))
                }
              />
              <code className="text-xs">{ev}</code>
            </label>
          ))}
        </div>

        {freshSecret && (
          <div className="rounded-md border border-[#E8632A] bg-[#E8632A]/5 p-3 space-y-2">
            <p className="text-sm font-medium">Signing secret — verify every delivery with this.</p>
            <CodeLine value={freshSecret} />
            <p className="text-xs text-muted-foreground">
              Signature: <code>X-ADLC-Signature: sha256=HMAC(secret, "{'{timestamp}'}.{'{body}'}")</code>,
              timestamp in <code>X-ADLC-Timestamp</code>.
            </p>
            <Button size="sm" variant="outline" onClick={() => setFreshSecret(null)}>Done</Button>
          </div>
        )}

        {(hookData?.webhooks ?? []).length > 0 && (
          <div className="divide-y divide-border border border-border rounded-md">
            {hookData!.webhooks.map((h) => (
              <div key={h.id} className="px-3 py-2.5 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{h.url}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {h.events.join(', ')}
                    {!h.is_active && ' · disabled after repeated failures'}
                    {h.failure_count > 0 && ` · ${h.failure_count} recent failure(s)`}
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button size="sm" variant="outline" onClick={() => testHook.mutate(h.id)}>
                    Test
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => deleteHook.mutate(h.id)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
