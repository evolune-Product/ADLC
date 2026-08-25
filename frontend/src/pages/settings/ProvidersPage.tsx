/**
 * Model providers — bring your own key.
 *
 * The framing of this page is the product position, not a settings screen.
 * This platform does not resell inference and never holds anyone's model
 * spend: you connect the vendor you already pay, on your own contract and your
 * own data-processing terms. That is the first thing the page says, because it
 * is the first thing a security review asks.
 *
 * The design consequence: nothing here is gated behind a plan, no provider is
 * "premium", and there is no platform key to fall back to in the copy. Twenty
 * vendors, all equal, pick whichever you already have.
 */
import { useState } from 'react'
import {
  ChevronDown, ExternalLink, KeyRound, Loader2, Server, Trash2, Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import {
  useDeleteCredential, useProviders, useSaveCredential, useTestCredential,
} from '@/hooks/useIntegrations'
import type { Provider } from '@/types/integrations'

const STATUS_DOT: Record<string, string> = {
  ok: 'bg-emerald-500',
  error: 'bg-red-500',
  unknown: 'bg-amber-500',
}

function ProviderRow({ provider }: { provider: Provider }) {
  const [open, setOpen] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState(provider.credential?.base_url ?? provider.base_url ?? '')
  const [model, setModel] = useState(
    provider.credential?.default_model ?? provider.suggested_models[0] ?? '',
  )

  const save = useSaveCredential()
  const test = useTestCredential()
  const remove = useDeleteCredential()

  const cred = provider.credential
  const needsKey = provider.auth !== 'url'
  const needsUrl = provider.auth === 'key+url' || provider.auth === 'url'
  // On an existing credential the key field may be left blank to keep the
  // stored one — the UI cannot show it back, so it cannot resend it.
  const canSave = (!needsKey || !!apiKey || !!cred) && (!needsUrl || !!baseUrl)

  return (
    <div className="border-b border-border last:border-b-0">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-foreground/[0.02] transition-colors"
      >
        <span
          className={cn(
            'h-2 w-2 rounded-full shrink-0',
            cred ? STATUS_DOT[cred.status] ?? STATUS_DOT.unknown : 'bg-border',
          )}
        />
        <span className="font-medium text-sm">{provider.label}</span>

        {cred?.masked_hint && (
          <span className="app-metric text-[0.7rem] text-muted-foreground">{cred.masked_hint}</span>
        )}
        {provider.pricing === 'free' && (
          <span className="onto-label text-emerald-600">no token cost</span>
        )}

        <span className="ml-auto flex items-center gap-2">
          {cred && (
            <span className={cn(
              'text-xs',
              cred.status === 'ok' ? 'text-emerald-600'
                : cred.status === 'error' ? 'text-red-600' : 'text-muted-foreground',
            )}>
              {cred.status === 'ok' ? 'Verified' : cred.status === 'error' ? 'Failed' : 'Not tested'}
            </span>
          )}
          <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform',
            open && 'rotate-180')} />
        </span>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-1 space-y-3">
          {provider.notes && (
            <p className="text-xs text-muted-foreground max-w-prose">{provider.notes}</p>
          )}

          {cred?.status === 'error' && cred.status_detail && (
            <p className="text-xs text-red-600 bg-red-500/5 border border-red-500/20 rounded p-2">
              {cred.status_detail}
            </p>
          )}
          {cred?.status === 'ok' && cred.status_detail && (
            <p className="text-xs text-emerald-700 dark:text-emerald-400">{cred.status_detail}</p>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            {needsKey && (
              <label className="block">
                <span className="onto-label block mb-1">
                  API key {cred && <span className="normal-case tracking-normal text-muted-foreground">— leave blank to keep the current one</span>}
                </span>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={provider.key_hint ?? 'Paste your key'}
                  autoComplete="off"
                  className="w-full text-sm rounded border border-border bg-background px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-foreground/20"
                />
              </label>
            )}

            {needsUrl && (
              <label className="block">
                <span className="onto-label block mb-1">Endpoint</span>
                <input
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder={provider.url_hint ?? provider.base_url ?? 'https://…'}
                  className="w-full text-sm rounded border border-border bg-background px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-foreground/20"
                />
              </label>
            )}

            <label className="block">
              <span className="onto-label block mb-1">Default model</span>
              <input
                value={model}
                onChange={(e) => setModel(e.target.value)}
                list={`models-${provider.key}`}
                placeholder="Any model id this provider serves"
                className="w-full text-sm rounded border border-border bg-background px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-foreground/20"
              />
              {/* Suggestions, not a closed set — model ids churn faster than any
                  hardcoded list survives, so anything you type is accepted. */}
              <datalist id={`models-${provider.key}`}>
                {provider.suggested_models.map((m) => <option key={m} value={m} />)}
              </datalist>
            </label>
          </div>

          {provider.pricing === 'unknown' && (
            <p className="text-xs text-muted-foreground">
              We don't carry published prices for this provider, so per-run cost will use a
              generic estimate until you enter your own rate. If you're on committed spend,
              your rate is the truer number anyway.
            </p>
          )}

          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Button
              size="sm"
              disabled={!canSave || save.isPending}
              onClick={() => save.mutate({
                provider: provider.key,
                api_key: apiKey || undefined,
                base_url: baseUrl || undefined,
                default_model: model || undefined,
              }, { onSuccess: () => setApiKey('') })}
            >
              {save.isPending ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : null}
              {cred ? 'Update' : 'Connect'}
            </Button>

            {cred && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={test.isPending}
                  onClick={() => test.mutate(provider.key)}
                >
                  {test.isPending
                    ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                    : <Zap className="h-3.5 w-3.5 mr-1.5" />}
                  Test
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-red-600"
                  onClick={() => {
                    if (window.confirm(`Remove the ${provider.label} key from this workspace?`)) {
                      remove.mutate(provider.key)
                    }
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </>
            )}

            <span className="ml-auto flex items-center gap-3">
              {provider.console_url && (
                <a
                  href={provider.console_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
                >
                  Get a key <ExternalLink className="h-3 w-3" />
                </a>
              )}
              <a
                href={provider.docs_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
              >
                API docs <ExternalLink className="h-3 w-3" />
              </a>
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ProvidersPage() {
  const { data, isLoading } = useProviders()
  const [showConnectedOnly, setShowConnectedOnly] = useState(false)

  if (isLoading) return <LoadingSkeleton />
  if (!data) return null

  const groups = showConnectedOnly
    ? data.groups
        .map((g) => ({ ...g, providers: g.providers.filter((p) => p.connected) }))
        .filter((g) => g.providers.length > 0)
    : data.groups

  return (
    <div className="space-y-6">
      <p className="onto-label mb-1">Govern</p>
      <PageHeader
        title="Model providers"
        subtitle="Connect the model vendors you already pay for. Your key, your contract, your terms."
        action={
          <button
            onClick={() => setShowConnectedOnly((v) => !v)}
            className={cn(
              'px-2.5 py-1 rounded text-xs transition-colors',
              showConnectedOnly
                ? 'bg-foreground text-background font-medium'
                : 'text-muted-foreground hover:text-foreground hover:bg-foreground/5',
            )}
          >
            {showConnectedOnly ? 'Showing connected' : 'Show all'}
          </button>
        }
      />

      {/* The position, stated once and plainly. */}
      <div className="bg-card rounded-lg border border-border p-4 flex items-start gap-3">
        <KeyRound className="h-4 w-4 text-[#E8632A] mt-0.5 shrink-0" />
        <div className="text-sm">
          <p className="font-medium mb-1">This platform doesn't sell you tokens.</p>
          <p className="text-muted-foreground max-w-prose">
            There is no bundled model quota and no markup on inference. You bring a key from
            a vendor you already have a relationship with — the tokens are billed by them, on
            your contract, under your data-processing agreement. We orchestrate, govern and
            audit the work; we never sit between you and your model vendor.
            {' '}Different agents can use different providers: Claude for the Dev agent, a
            local Ollama for QA, whatever fits.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-4 text-sm">
        <span className="text-muted-foreground">
          <strong className="app-metric text-foreground">{data.connected_count}</strong> connected
        </span>
        <span className="text-muted-foreground">
          <strong className="app-metric text-foreground">{data.total}</strong> available
        </span>
      </div>

      {groups.map((group) => (
        <section key={group.family}>
          <p className="onto-label mb-2 flex items-center gap-1.5">
            {group.family === 'self_hosted' && <Server className="h-3 w-3" />}
            {group.label}
          </p>
          <div className="bg-card rounded-lg border border-border overflow-hidden">
            {group.providers.map((p) => <ProviderRow key={p.key} provider={p} />)}
          </div>
        </section>
      ))}

      {groups.length === 0 && (
        <div className="bg-card rounded-lg border border-border p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No providers connected yet. Switch to <em>Show all</em> and connect the one you use.
          </p>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Keys are encrypted at rest and never returned by any endpoint — not even to the person
        who set them. The masked hint next to each provider is there so you can tell which key
        is installed without the platform ever handing it back.
      </p>
    </div>
  )
}
