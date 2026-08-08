import { useNavigate } from 'react-router-dom'
import { Plus, Activity } from 'lucide-react'
import { useDashboardStats } from '@/hooks/useDashboard'

const STATUS_STYLE: Record<string, { dot: string; label: string }> = {
  queued:            { dot: 'bg-muted-foreground', label: 'Queued' },
  running:           { dot: 'bg-blue-500',         label: 'Running' },
  awaiting_approval: { dot: 'bg-[#E8632A]',        label: 'Awaiting approval' },
  approved:          { dot: 'bg-emerald-500',       label: 'Approved' },
  completed:         { dot: 'bg-emerald-500',       label: 'Completed' },
  failed:            { dot: 'bg-red-500',           label: 'Failed' },
}

function duration(run: { started_at?: string; completed_at?: string }): string {
  if (!run.started_at) return '—'
  const end = run.completed_at ?? new Date().toISOString()
  const s   = Math.floor((new Date(end).getTime() - new Date(run.started_at).getTime()) / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useDashboardStats()

  const stats = [
    { label: 'Total Projects',    value: data?.total_projects    ?? 0 },
    { label: 'Active Runs',       value: data?.active_runs       ?? 0 },
    { label: 'Pending Approvals', value: data?.pending_approvals ?? 0, accent: true },
    { label: 'Skills Configured', value: data?.skills_configured ?? 0 },
  ]

  return (
    <div className="max-w-5xl mx-auto space-y-6">

      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="onto-label mb-1">Overview</p>
          <h1 className="text-xl font-bold text-foreground tracking-tight">Dashboard</h1>
        </div>
        <button
          onClick={() => navigate('/projects/new')}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-foreground text-background text-xs font-semibold rounded hover:opacity-85 transition-opacity"
        >
          <Plus className="h-3.5 w-3.5" />
          New Project
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {stats.map(({ label, value, accent }) => (
          <div key={label} className="bg-card rounded-lg border border-border p-4">
            <p className="onto-label mb-2">{label}</p>
            {isLoading
              ? <div className="h-8 w-12 rounded bg-muted animate-pulse" />
              : (
                <p className={`app-metric text-3xl ${accent && value > 0 ? 'text-[#E8632A]' : 'text-foreground'}`}>
                  {value}
                </p>
              )
            }
          </div>
        ))}
      </div>

      {/* Recent runs */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-foreground">Recent Runs</p>
          <button
            onClick={() => navigate('/runs')}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            View all →
          </button>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 rounded-lg border border-border bg-card animate-pulse opacity-60" />
            ))}
          </div>
        ) : !data?.recent_runs?.length ? (
          <div className="flex flex-col items-center justify-center bg-card rounded-lg border border-border border-dashed py-14 gap-2">
            <Activity className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">No runs yet</p>
            <p className="text-xs text-muted-foreground">Trigger a run from a project ticket.</p>
          </div>
        ) : (
          <div className="bg-card rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-2.5">
                    <span className="onto-label">Status</span>
                  </th>
                  <th className="text-left px-4 py-2.5">
                    <span className="onto-label">Step</span>
                  </th>
                  <th className="text-left px-4 py-2.5 hidden md:table-cell">
                    <span className="onto-label">Branch</span>
                  </th>
                  <th className="text-left px-4 py-2.5 hidden sm:table-cell">
                    <span className="onto-label">Duration</span>
                  </th>
                  <th className="text-left px-4 py-2.5 hidden lg:table-cell">
                    <span className="onto-label">Started</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.recent_runs.map((run, i) => {
                  const s = STATUS_STYLE[run.status] ?? { dot: 'bg-muted-foreground', label: run.status }
                  return (
                    <tr
                      key={run.id}
                      onClick={() => navigate(`/runs/${run.id}`)}
                      className={`cursor-pointer hover:bg-muted/40 transition-colors ${i < data.recent_runs.length - 1 ? 'border-b border-border' : ''}`}
                    >
                      <td className="px-4 py-3">
                        <span className="flex items-center gap-2">
                          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${s.dot}`} />
                          <span className="text-xs font-medium text-foreground capitalize">
                            {run.status.replace(/_/g, ' ')}
                          </span>
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground truncate max-w-[140px]">
                        {run.current_step ?? '—'}
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <span className="font-mono text-[11px] text-muted-foreground truncate block max-w-[130px]">
                          {run.branch_name ?? '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 hidden sm:table-cell text-xs text-muted-foreground">
                        {duration(run)}
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell text-xs text-muted-foreground">
                        {run.started_at ? new Date(run.started_at).toLocaleString() : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
