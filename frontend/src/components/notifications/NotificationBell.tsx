import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useMarkRead, useNotifications } from '@/hooks/usePlatform'

const DOT: Record<string, string> = {
  info: 'bg-muted-foreground',
  warning: 'bg-[#E8632A]',
  critical: 'bg-red-600',
}

/** Topbar bell — unread count plus the five most recent items. */
export default function NotificationBell() {
  const navigate = useNavigate()
  const { data } = useNotifications()
  const markRead = useMarkRead()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const unread = data?.unread_count ?? 0
  const recent = (data?.notifications ?? []).slice(0, 5)

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative p-1.5 rounded hover:bg-foreground/5 text-muted-foreground hover:text-foreground"
        aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}
      >
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[15px] h-[15px] px-1 rounded-full
                           bg-[#E8632A] text-white text-[9px] font-semibold flex items-center justify-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-card border border-border rounded-lg shadow-lg z-50 overflow-hidden">
          <div className="px-3 py-2 border-b border-border flex items-center justify-between">
            <p className="onto-label">Notifications</p>
            {unread > 0 && <span className="text-xs text-muted-foreground">{unread} unread</span>}
          </div>

          {recent.length === 0 ? (
            <p className="px-3 py-6 text-sm text-muted-foreground text-center">Nothing yet</p>
          ) : (
            <div className="divide-y divide-border max-h-80 overflow-y-auto">
              {recent.map((n) => (
                <button
                  key={n.id}
                  onClick={() => {
                    if (!n.read) markRead.mutate(n.id)
                    setOpen(false)
                    if (n.link) navigate(n.link)
                  }}
                  className={cn(
                    'w-full text-left px-3 py-2.5 flex items-start gap-2 hover:bg-foreground/[0.04]',
                    n.read && 'opacity-60',
                  )}
                >
                  <span className={cn('w-1.5 h-1.5 rounded-full mt-1.5 shrink-0', DOT[n.severity])} />
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{n.title}</p>
                    <p className="text-xs text-muted-foreground truncate">{n.body}</p>
                  </div>
                </button>
              ))}
            </div>
          )}

          <button
            onClick={() => { setOpen(false); navigate('/notifications') }}
            className="w-full px-3 py-2 text-sm border-t border-border text-muted-foreground hover:text-foreground"
          >
            View all
          </button>
        </div>
      )}
    </div>
  )
}
