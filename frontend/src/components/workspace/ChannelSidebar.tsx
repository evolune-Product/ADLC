/**
 * The channel rail.
 *
 * Ordering is by section, then by recent activity — not alphabetical. A team's
 * attention follows what just moved, and an alphabetical list buries the
 * channel that is on fire under the one called #announcements.
 *
 * Unread is bold; a mention count is an orange pill. Those are different
 * urgencies and collapsing them into one number is why people stop trusting
 * badges and mute everything.
 */
import { useMemo, useState } from 'react'
import { Bell, BellOff, Hash, Lock, MessageSquare, Megaphone, Plus, Search, Star } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Channel } from '@/types/workspace'

const KIND_ICON = {
  channel: Hash,
  private: Lock,
  broadcast: Megaphone,
  dm: MessageSquare,
  group_dm: MessageSquare,
} as const

interface Props {
  channels: Channel[]
  activeId?: string
  onSelect: (channel: Channel) => void
  onCreate: () => void
  onBrowse: () => void
  totalMentions: number
}

export default function ChannelSidebar({
  channels, activeId, onSelect, onCreate, onBrowse, totalMentions,
}: Props) {
  const [filter, setFilter] = useState('')

  const groups = useMemo(() => {
    const q = filter.trim().toLowerCase()
    const visible = channels.filter((c) =>
      !q || (c.name ?? '').toLowerCase().includes(q) || (c.slug ?? '').includes(q),
    )
    const byActivity = (a: Channel, b: Channel) =>
      (b.last_message_at ?? '').localeCompare(a.last_message_at ?? '')

    return {
      starred: visible.filter((c) => c.is_starred).sort(byActivity),
      channels: visible
        .filter((c) => !c.is_starred && ['channel', 'private', 'broadcast'].includes(c.kind))
        .sort(byActivity),
      dms: visible
        .filter((c) => !c.is_starred && ['dm', 'group_dm'].includes(c.kind))
        .sort(byActivity),
    }
  }, [channels, filter])

  function Row({ channel }: { channel: Channel }) {
    const Icon = KIND_ICON[channel.kind] ?? Hash
    const active = channel.id === activeId
    // A channel you have never opened has no read marker, so everything in it
    // counts as unread — but only bold it if there is actually something there.
    const unread = channel.is_member ? channel.unread : 0
    const bold = unread > 0 && !active

    return (
      <button
        onClick={() => onSelect(channel)}
        className={cn(
          'w-full flex items-center gap-2 px-2.5 py-1.5 rounded text-sm transition-colors text-left',
          active
            ? 'bg-foreground text-background font-medium'
            : bold
              ? 'text-foreground font-medium hover:bg-foreground/5'
              : 'text-muted-foreground hover:text-foreground hover:bg-foreground/5',
        )}
      >
        <Icon className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate flex-1">{channel.name ?? 'Direct message'}</span>

        {channel.is_muted && !active && <BellOff className="h-3 w-3 shrink-0 opacity-50" />}

        {channel.unread_mentions > 0 && (
          <span className="app-metric shrink-0 text-[0.65rem] rounded-full bg-[#E8632A] text-white px-1.5 min-w-[1.1rem] text-center">
            {channel.unread_mentions}
          </span>
        )}
        {channel.unread_mentions === 0 && unread > 0 && !active && (
          <span className="app-metric shrink-0 text-[0.65rem] text-muted-foreground">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>
    )
  }

  function Section({ label, items, icon: Icon }: {
    label: string; items: Channel[]; icon?: typeof Star
  }) {
    if (items.length === 0) return null
    return (
      <div>
        <p className="onto-label px-2 mb-1.5 flex items-center gap-1.5">
          {Icon && <Icon className="h-3 w-3" />}
          {label}
        </p>
        <div className="space-y-0.5">
          {items.map((c) => <Row key={c.id} channel={c} />)}
        </div>
      </div>
    )
  }

  return (
    <aside className="w-56 shrink-0 border-r border-border flex flex-col bg-background">
      <div className="px-3 h-12 flex items-center justify-between border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <span className="app-display text-sm">Workspace</span>
          {totalMentions > 0 && (
            <span className="app-metric text-[0.65rem] rounded-full bg-[#E8632A] text-white px-1.5">
              {totalMentions}
            </span>
          )}
        </div>
        <button
          onClick={onCreate}
          className="h-6 w-6 rounded grid place-items-center hover:bg-foreground/5 text-muted-foreground hover:text-foreground"
          title="New channel"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      <div className="px-2 py-2 shrink-0">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter channels"
            className="w-full text-sm rounded border border-border bg-background pl-7 pr-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-foreground/20"
          />
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 pb-3 space-y-4">
        <Section label="Starred" items={groups.starred} icon={Star} />
        <Section label="Channels" items={groups.channels} />
        <Section label="Direct messages" items={groups.dms} icon={Bell} />

        <button
          onClick={onBrowse}
          className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded text-sm text-muted-foreground hover:text-foreground hover:bg-foreground/5"
        >
          <Plus className="h-3.5 w-3.5" /> Browse people and channels
        </button>
      </nav>
    </aside>
  )
}
