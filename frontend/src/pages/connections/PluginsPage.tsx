/**
 * The plugin gallery.
 *
 * The one rule this page enforces: every card states how deeply the plugin is
 * actually wired in. A catalogue of forty logos is worth nothing if thirty-five
 * of them only store a token, and a buyer who discovers that in week two of a
 * trial loses more trust than the logo ever earned. So `depth` is a badge, it
 * is explained in a legend at the top, and "verified" says plainly what it does
 * — the credential is really checked against the vendor, and it is available to
 * agents and skills, but no bespoke pipeline behaviour exists for it yet.
 */
import { useMemo, useState } from 'react'
import {
  Bell, CheckCircle2, ExternalLink, Loader2, Plug, RefreshCw, Search, ShieldCheck, X, Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { useConnectPlugin, usePlugins, useVerifyConnection } from '@/hooks/useIntegrations'
import type { Plugin, PluginDepth } from '@/types/integrations'

const DEPTH: Record<PluginDepth, { label: string; blurb: string; className: string; icon: typeof Zap }> = {
  native: {
    label: 'Drives the pipeline',
    blurb: 'The agents read from and write to it — issues, pull requests, comments, reviewers.',
    className: 'text-[#E8632A] border-[#E8632A]',
    icon: Zap,
  },
  notify: {
    label: 'Receives events',
    blurb: 'Approval requests, run failures and deploys are delivered here.',
    className: 'text-emerald-600 border-emerald-600',
    icon: Bell,
  },
  verified: {
    label: 'Credential verified',
    blurb: 'The key is checked against the vendor and made available to agents and skills. '
         + 'No bespoke pipeline behaviour yet.',
    className: 'text-muted-foreground border-border',
    icon: ShieldCheck,
  },
}

function ConnectForm({ plugin, onDone }: { plugin: Plugin; onDone: () => void }) {
  const connect = useConnectPlugin()
  const [token, setToken] = useState('')
  const [url, setUrl] = useState('')
  const [user, setUser] = useState('')
  const [extra, setExtra] = useState('')

  const needsToken = !!plugin.token_label
  const needsUrl = !!plugin.url_label
  const needsUser = !!plugin.user_label
  const ready = (!needsToken || token) && (!needsUrl || url) && (!needsUser || user)

  return (
    <div className="mt-3 pt-3 border-t border-border space-y-3">
      {plugin.scopes && (
        <p className="text-xs text-muted-foreground">
          Scopes needed: {plugin.scopes.map((s) => (
            <code key={s} className="app-metric bg-muted rounded px-1 py-0.5 mr-1">{s}</code>
          ))}
        </p>
      )}

      <div className="grid gap-2.5 sm:grid-cols-2">
        {needsUser && (
          <label className="block">
            <span className="onto-label block mb-1">{plugin.user_label}</span>
            <input
              value={user}
              onChange={(e) => setUser(e.target.value)}
              className="w-full text-sm rounded border border-border bg-background px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-foreground/20"
            />
          </label>
        )}
        {needsUrl && (
          <label className="block">
            <span className="onto-label block mb-1">{plugin.url_label}</span>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={plugin.url_hint}
              className="w-full text-sm rounded border border-border bg-background px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-foreground/20"
            />
          </label>
        )}
        {needsToken && (
          <label className="block">
            <span className="onto-label block mb-1">{plugin.token_label}</span>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder={plugin.token_hint}
              autoComplete="off"
              className="w-full text-sm rounded border border-border bg-background px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-foreground/20"
            />
          </label>
        )}
        {plugin.extra_label && (
          <label className="block">
            <span className="onto-label block mb-1">{plugin.extra_label}</span>
            <input
              value={extra}
              onChange={(e) => setExtra(e.target.value)}
              className="w-full text-sm rounded border border-border bg-background px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-foreground/20"
            />
          </label>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          disabled={!ready || connect.isPending}
          onClick={() => connect.mutate(
            {
              key: plugin.key,
              token: token || undefined,
              url: url || undefined,
              user: user || undefined,
              extra: extra || undefined,
            },
            { onSuccess: onDone },
          )}
        >
          {connect.isPending && <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />}
          Connect and verify
        </Button>
        <Button size="sm" variant="ghost" onClick={onDone}>Cancel</Button>

        <span className="ml-auto flex items-center gap-3">
          {plugin.setup_url && (
            <a href={plugin.setup_url} target="_blank" rel="noreferrer"
               className="text-xs inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">
              Create a token <ExternalLink className="h-3 w-3" />
            </a>
          )}
          <a href={plugin.docs_url} target="_blank" rel="noreferrer"
             className="text-xs inline-flex items-center gap-1 text-muted-foreground hover:text-foreground">
            Docs <ExternalLink className="h-3 w-3" />
          </a>
        </span>
      </div>
    </div>
  )
}

function PluginCard({ plugin }: { plugin: Plugin }) {
  const [connecting, setConnecting] = useState(false)
  const verify = useVerifyConnection()
  const depth = DEPTH[plugin.depth]
  const DepthIcon = depth.icon

  return (
    <div className="bg-card rounded-lg border border-border p-4">
      <div className="flex items-start gap-2 mb-1.5">
        <p className="font-medium text-sm flex-1">{plugin.label}</p>
        {plugin.connected && <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />}
      </div>

      <span className={cn(
        'inline-flex items-center gap-1 text-[0.65rem] rounded-full border px-1.5 py-0.5 mb-2.5',
        depth.className,
      )}>
        <DepthIcon className="h-3 w-3" />
        {depth.label}
      </span>

      <ul className="text-xs text-muted-foreground space-y-0.5 mb-3">
        {plugin.capabilities.slice(0, 4).map((c) => (
          <li key={c} className="flex gap-1.5">
            <span className="text-border">·</span>{c}
          </li>
        ))}
      </ul>

      {plugin.notes && (
        <p className="text-xs text-muted-foreground/80 mb-3 italic">{plugin.notes}</p>
      )}

      {plugin.connections.map((c) => (
        <div key={c.id} className="flex items-center gap-2 text-xs mb-1.5">
          <span className={cn('h-1.5 w-1.5 rounded-full shrink-0',
            c.status === 'connected' ? 'bg-emerald-500' : 'bg-red-500')} />
          <span className="truncate flex-1">
            {(c.metadata?.display_name as string) || c.name}
          </span>
          <button
            onClick={() => verify.mutate(c.id)}
            disabled={verify.isPending}
            className="text-muted-foreground hover:text-foreground"
            title="Re-check this credential"
          >
            <RefreshCw className={cn('h-3 w-3', verify.isPending && 'animate-spin')} />
          </button>
        </div>
      ))}

      {connecting ? (
        <ConnectForm plugin={plugin} onDone={() => setConnecting(false)} />
      ) : (
        <Button
          size="sm"
          variant={plugin.connected ? 'outline' : 'default'}
          className="w-full mt-1"
          onClick={() => setConnecting(true)}
        >
          {plugin.connected ? 'Add another' : 'Connect'}
        </Button>
      )}
    </div>
  )
}

export default function PluginsPage() {
  const { data, isLoading } = usePlugins()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<string | null>(null)

  const groups = useMemo(() => {
    if (!data) return []
    const q = query.trim().toLowerCase()
    return data.groups
      .filter((g) => !category || g.category === category)
      .map((g) => ({
        ...g,
        plugins: g.plugins.filter((p) =>
          !q || p.label.toLowerCase().includes(q) ||
          p.capabilities.some((c) => c.toLowerCase().includes(q)),
        ),
      }))
      .filter((g) => g.plugins.length > 0)
  }, [data, query, category])

  if (isLoading) return <LoadingSkeleton />
  if (!data) return null

  return (
    <div className="space-y-6">
      <p className="onto-label mb-1">Build</p>
      <PageHeader
        title="Plugins"
        subtitle={`${data.counts.total} systems across ${data.counts.categories} categories. Connect the ones your team already runs.`}
      />

      {/* The legend is not decoration — it is the honesty contract for the
          badges below, and it belongs above the cards rather than in a tooltip. */}
      <div className="bg-card rounded-lg border border-border p-4 grid gap-2.5 sm:grid-cols-3">
        {(Object.keys(DEPTH) as PluginDepth[]).map((key) => {
          const d = DEPTH[key]
          const Icon = d.icon
          const count = data.counts[key]
          return (
            <div key={key} className="flex items-start gap-2">
              <Icon className={cn('h-4 w-4 mt-0.5 shrink-0', d.className.split(' ')[0])} />
              <div>
                <p className="text-sm font-medium">
                  {d.label} <span className="app-metric text-muted-foreground">({count})</span>
                </p>
                <p className="text-xs text-muted-foreground">{d.blurb}</p>
              </div>
            </div>
          )
        })}
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search plugins and capabilities…"
            className="w-full text-sm rounded border border-border bg-background pl-8 pr-8 py-1.5 focus:outline-none focus:ring-1 focus:ring-foreground/20"
          />
          {query && (
            <button onClick={() => setQuery('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        <button
          onClick={() => setCategory(null)}
          className={cn('px-2.5 py-1 rounded text-xs transition-colors',
            category === null
              ? 'bg-foreground text-background font-medium'
              : 'text-muted-foreground hover:text-foreground hover:bg-foreground/5')}
        >
          All
        </button>
        {data.groups.map((g) => (
          <button
            key={g.category}
            onClick={() => setCategory(g.category)}
            className={cn('px-2.5 py-1 rounded text-xs transition-colors',
              category === g.category
                ? 'bg-foreground text-background font-medium'
                : 'text-muted-foreground hover:text-foreground hover:bg-foreground/5')}
          >
            {g.label}
          </button>
        ))}
      </div>

      {groups.map((group) => (
        <section key={group.category}>
          <p className="onto-label mb-2">{group.label}</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {group.plugins.map((p) => <PluginCard key={p.key} plugin={p} />)}
          </div>
        </section>
      ))}

      {groups.length === 0 && (
        <div className="bg-card rounded-lg border border-border p-8 text-center">
          <Plug className="h-5 w-5 mx-auto mb-2 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Nothing matches “{query}”. Anything not listed can still be reached with a
            custom webhook.
          </p>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Every credential is verified against the vendor when you connect it, encrypted at rest,
        and never returned by any endpoint. Tokens expire and get revoked — use the refresh
        icon on a connection to re-check one rather than trusting a status from months ago.
      </p>
    </div>
  )
}
