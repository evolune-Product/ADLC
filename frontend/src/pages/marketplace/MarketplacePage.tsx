import { useState } from 'react'
import { BookOpen, Bot, Download, Layers, Search, ShieldCheck, Star } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { useInstallTemplate, useMarketplace } from '@/hooks/usePlatform'
import type { Template, TemplateKind } from '@/types/platform'

const KINDS: { value: TemplateKind | 'all'; label: string; icon: typeof BookOpen }[] = [
  { value: 'all', label: 'Everything', icon: Search },
  { value: 'skill', label: 'Skills', icon: BookOpen },
  { value: 'agent', label: 'Agents', icon: Bot },
  { value: 'pod', label: 'Pods', icon: Layers },
]

const KIND_ICON = { skill: BookOpen, agent: Bot, pod: Layers }

function TemplateCard({ template, onInstall, installing }: {
  template: Template
  onInstall: () => void
  installing: boolean
}) {
  const Icon = KIND_ICON[template.kind]
  const listing = template.listing
  return (
    <div className="bg-card rounded-lg border border-border p-4 flex flex-col">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
          <p className="font-medium truncate">{template.name}</p>
        </div>
        {listing?.is_verified && (
          <span title="First-party, reviewed" className="shrink-0">
            <ShieldCheck className="h-4 w-4 text-[#E8632A]" />
          </span>
        )}
      </div>

      <p className="text-sm text-muted-foreground mt-2 flex-1">{template.description}</p>

      <div className="flex flex-wrap gap-1.5 mt-3">
        {(template.tags ?? []).slice(0, 4).map((tag) => (
          <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
            {tag}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between mt-4 pt-3 border-t border-border">
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Download className="h-3 w-3" />
            {listing?.install_count ?? 0}
          </span>
          {(listing?.rating_count ?? 0) > 0 && (
            <span className="flex items-center gap-1">
              <Star className="h-3 w-3" />
              {listing?.rating} ({listing?.rating_count})
            </span>
          )}
          <span className="capitalize">{template.kind}</span>
        </div>
        <Button size="sm" onClick={onInstall} disabled={installing}>
          Install
        </Button>
      </div>
    </div>
  )
}

export default function MarketplacePage() {
  const [kind, setKind] = useState<TemplateKind | 'all'>('all')
  const [sort, setSort] = useState('installs')
  const [search, setSearch] = useState('')

  const { data: templates = [], isLoading } = useMarketplace(kind === 'all' ? undefined : kind, sort)
  const install = useInstallTemplate()

  const filtered = templates.filter((t) => {
    if (!search) return true
    const needle = search.toLowerCase()
    return (
      t.name.toLowerCase().includes(needle) ||
      (t.description ?? '').toLowerCase().includes(needle) ||
      (t.tags ?? []).some((tag) => tag.toLowerCase().includes(needle))
    )
  })

  return (
    <div className="space-y-6">
      <p className="onto-label mb-1">Marketplace</p>
      <PageHeader
        title="Skill and pod library"
        subtitle="Install a governed pipeline in one click, or publish your own team's standards for others."
      />

      <div className="flex flex-wrap gap-2 items-center">
        {KINDS.map(({ value, label, icon: Icon }) => (
          <Button
            key={value}
            size="sm"
            variant={kind === value ? 'default' : 'outline'}
            onClick={() => setKind(value)}
          >
            <Icon className="h-3.5 w-3.5 mr-1.5" />
            {label}
          </Button>
        ))}
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search the library…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm
                       placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="installs">Most installed</option>
          <option value="rating">Highest rated</option>
          <option value="newest">Newest</option>
        </select>
      </div>

      {isLoading ? (
        <LoadingSkeleton />
      ) : filtered.length === 0 ? (
        <div className="bg-card rounded-lg border border-dashed border-border p-12 text-center">
          <p className="font-medium">Nothing matches that search</p>
          <p className="text-sm text-muted-foreground mt-1">
            Try a different term, or publish one of your own skills from its detail page.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((t) => (
            <TemplateCard
              key={t.id}
              template={t}
              installing={install.isPending}
              onInstall={() => install.mutate(t.slug)}
            />
          ))}
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Installing copies the template into your workspace — later changes upstream never alter
        your agents' behaviour without you choosing them.
      </p>
    </div>
  )
}
