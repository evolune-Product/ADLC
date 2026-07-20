import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity } from 'lucide-react'
import { useRuns } from '@/hooks/useRuns'
import type { Run } from '@/types'

const STATUS_COLOR: Record<string, string> = {
  queued:            'bg-muted text-muted-foreground',
  running:           'bg-blue-100 text-blue-700',
  awaiting_approval: 'bg-yellow-100 text-yellow-700',
  approved:          'bg-green-100 text-green-700',
  completed:         'bg-green-100 text-green-700',
  failed:            'bg-red-100 text-red-700',
}

const ALL_STATUSES = ['queued', 'running', 'awaiting_approval', 'completed', 'failed']

function duration(run: Run): string {
  if (!run.started_at) return '—'
  const end = run.completed_at ?? new Date().toISOString()
  const ms  = new Date(end).getTime() - new Date(run.started_at).getTime()
  const s   = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
}

export default function RunsPage() {
  const navigate = useNavigate()
  const [filterStatus, setFilterStatus] = useState('')
  const { data: runs = [], isLoading } = useRuns({ status: filterStatus || undefined })

  const stats = {
    total:            runs.length,
    running:          runs.filter((r) => r.status === 'running').length,
    awaiting:         runs.filter((r) => r.status === 'awaiting_approval').length,
    completed:        runs.filter((r) => r.status === 'completed').length,
    failed:           runs.filter((r) => r.status === 'failed').length,
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Runs</h1>
        <p className="text-sm text-muted-foreground mt-1">All agent runs across your projects.</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: 'Total',    value: stats.total },
          { label: 'Running',  value: stats.running },
          { label: 'Awaiting', value: stats.awaiting },
          { label: 'Done',     value: stats.completed },
          { label: 'Failed',   value: stats.failed },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg border p-3">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-xl font-semibold mt-0.5">{value}</p>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setFilterStatus('')}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            filterStatus === '' ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
          }`}
        >
          All
        </button>
        {ALL_STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              filterStatus === s ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
            }`}
          >
            {s.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => <div key={i} className="h-14 rounded-lg border bg-muted/40 animate-pulse" />)}
        </div>
      ) : runs.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 gap-2">
          <Activity className="h-8 w-8 text-muted-foreground" />
          <p className="font-medium">No runs yet</p>
          <p className="text-sm text-muted-foreground">Trigger a run from a project ticket.</p>
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/30">
              <tr>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Status</th>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Current Step</th>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Branch</th>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Duration</th>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {runs.map((run) => (
                <tr
                  key={run.id}
                  className="hover:bg-accent/50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/runs/${run.id}`)}
                >
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[run.status] ?? 'bg-secondary'}`}>
                      {run.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground truncate max-w-[180px]">
                    {run.current_step ?? '—'}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs truncate max-w-[160px]">
                    {run.branch_name ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{duration(run)}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {run.started_at ? new Date(run.started_at).toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
