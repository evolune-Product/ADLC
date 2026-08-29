import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, Inbox, CheckCircle2, Building2, Clock } from 'lucide-react'
import { toast } from 'sonner'
import { useDesk, useCreateDeskRequest } from '@/hooks/useDesk'
import { getApiError } from '@/lib/api'

function timeAgo(iso: string | null): string {
  if (!iso) return '—'
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

export default function DeskPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useDesk()
  const createRequest = useCreateDeskRequest()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [lastRouting, setLastRouting] = useState<{ confidence: string; reasoning: string } | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    try {
      const work = await createRequest.mutateAsync({ title: title.trim(), description: description.trim() || undefined })
      setLastRouting({ confidence: work.routing_confidence ?? 'unmatched', reasoning: work.routing_reasoning ?? '' })
      setTitle('')
      setDescription('')
      toast.success('Request opened')
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  const pendingApprovalCount = (data?.pending_approvals.runs.length ?? 0) + (data?.pending_approvals.work.length ?? 0)

  return (
    <div className="max-w-5xl mx-auto space-y-6">

      {/* Page header */}
      <div>
        <p className="onto-label mb-1">Command Center</p>
        <h1 className="text-xl font-bold text-foreground tracking-tight">Desk</h1>
      </div>

      {/* Quick action */}
      <form onSubmit={submit} className="bg-card rounded-lg border border-border p-4 space-y-3">
        <p className="onto-label">Open a request</p>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder='What do you need? e.g. "Marketing needs new launch copy reviewed"'
          className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-foreground/20"
        />
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Any extra detail (optional)"
          rows={2}
          className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-foreground/20 resize-none"
        />
        <div className="flex items-center justify-between">
          <p className="text-[11px] text-muted-foreground">
            Routed automatically by a simple name match against your departments — no AI here yet.
          </p>
          <button
            type="submit"
            disabled={!title.trim() || createRequest.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-foreground text-background text-xs font-semibold rounded hover:opacity-85 transition-opacity disabled:opacity-40"
          >
            <Send className="h-3.5 w-3.5" />
            {createRequest.isPending ? 'Submitting…' : 'Submit'}
          </button>
        </div>
        {lastRouting && (
          <div className="text-xs rounded border border-border bg-muted/40 px-3 py-2">
            <span className="font-semibold text-foreground capitalize">{lastRouting.confidence}</span>
            <span className="text-muted-foreground"> — {lastRouting.reasoning}</span>
          </div>
        )}
      </form>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <div className="bg-card rounded-lg border border-border p-4">
          <p className="onto-label mb-2">Assigned to Me</p>
          {isLoading
            ? <div className="h-8 w-12 rounded bg-muted animate-pulse" />
            : <p className="app-metric text-3xl text-foreground">{data?.pending_work.length ?? 0}</p>}
        </div>
        <div className="bg-card rounded-lg border border-border p-4">
          <p className="onto-label mb-2">Pending Approvals</p>
          {isLoading
            ? <div className="h-8 w-12 rounded bg-muted animate-pulse" />
            : <p className={`app-metric text-3xl ${pendingApprovalCount > 0 ? 'text-[#E8632A]' : 'text-foreground'}`}>{pendingApprovalCount}</p>}
        </div>
        <div className="bg-card rounded-lg border border-border p-4">
          <p className="onto-label mb-2">Departments</p>
          {isLoading
            ? <div className="h-8 w-12 rounded bg-muted animate-pulse" />
            : <p className="app-metric text-3xl text-foreground">{data?.department_summary.length ?? 0}</p>}
        </div>
      </div>

      {/* Pending work assigned to me */}
      <div>
        <p className="text-sm font-semibold text-foreground mb-3">My Pending Work</p>
        {!isLoading && !data?.pending_work.length ? (
          <div className="flex flex-col items-center justify-center bg-card rounded-lg border border-border border-dashed py-10 gap-2">
            <Inbox className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">Nothing assigned to you</p>
          </div>
        ) : (
          <div className="bg-card rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-2.5"><span className="onto-label">Status</span></th>
                  <th className="text-left px-4 py-2.5"><span className="onto-label">Title</span></th>
                  <th className="text-left px-4 py-2.5 hidden sm:table-cell"><span className="onto-label">Opened</span></th>
                </tr>
              </thead>
              <tbody>
                {data?.pending_work.map((w, i) => (
                  <tr key={w.id} className={i < (data.pending_work.length - 1) ? 'border-b border-border' : ''}>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full shrink-0 bg-[#E8632A]" />
                        <span className="text-xs font-medium text-foreground capitalize">{w.status.replace(/_/g, ' ')}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-foreground truncate max-w-[300px]">{w.title}</td>
                    <td className="px-4 py-3 hidden sm:table-cell text-xs text-muted-foreground">{timeAgo(w.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pending approvals */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-foreground">Pending Approvals</p>
          <button onClick={() => navigate('/runs')} className="text-xs text-muted-foreground hover:text-foreground transition-colors">
            View runs →
          </button>
        </div>
        {!isLoading && pendingApprovalCount === 0 ? (
          <div className="flex flex-col items-center justify-center bg-card rounded-lg border border-border border-dashed py-10 gap-2">
            <CheckCircle2 className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">Nothing waiting on your approval</p>
          </div>
        ) : (
          <div className="space-y-2">
            {data?.pending_approvals.runs.map((r) => (
              <div key={r.id} onClick={() => navigate(`/runs/${r.id}`)}
                   className="flex items-center justify-between bg-card rounded-lg border border-border px-4 py-3 cursor-pointer hover:bg-muted/40 transition-colors">
                <span className="flex items-center gap-2 text-xs text-foreground">
                  <span className="w-1.5 h-1.5 rounded-full shrink-0 bg-[#E8632A]" />
                  Run — {r.current_step ?? 'awaiting approval'}
                </span>
                <span className="text-[11px] text-muted-foreground">{timeAgo(r.created_at)}</span>
              </div>
            ))}
            {data?.pending_approvals.work.map((w) => (
              <div key={w.id}
                   className="flex items-center justify-between bg-card rounded-lg border border-border px-4 py-3">
                <span className="flex items-center gap-2 text-xs text-foreground">
                  <span className="w-1.5 h-1.5 rounded-full shrink-0 bg-[#E8632A]" />
                  {w.title}
                </span>
                <span className="text-[11px] text-muted-foreground">{timeAgo(w.created_at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Department summary */}
      {!!data?.department_summary.length && (
        <div>
          <p className="text-sm font-semibold text-foreground mb-3">Departments</p>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
            {data.department_summary.map((d) => (
              <div key={d.id} className="bg-card rounded-lg border border-border p-4">
                <span className="flex items-center gap-1.5 mb-2">
                  <Building2 className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-sm font-medium text-foreground">{d.name}</span>
                </span>
                <p className="text-xs text-muted-foreground">{d.active_work_count} active · {d.member_count} members</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent activity */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-foreground">Recent Activity</p>
          <button onClick={() => navigate('/audit')} className="text-xs text-muted-foreground hover:text-foreground transition-colors">
            View all →
          </button>
        </div>
        {!isLoading && !data?.recent_activity.length ? (
          <div className="flex flex-col items-center justify-center bg-card rounded-lg border border-border border-dashed py-10 gap-2">
            <Clock className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">No activity yet</p>
          </div>
        ) : (
          <div className="bg-card rounded-lg border border-border divide-y divide-border">
            {data?.recent_activity.map((a) => (
              <div key={a.id} className="flex items-center justify-between px-4 py-2.5">
                <span className="text-xs text-foreground">{a.action}</span>
                <span className="text-[11px] text-muted-foreground">{timeAgo(a.created_at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
