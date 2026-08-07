import { useState } from 'react'
import { Download, TrendingUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { useAgentScores, useAnalyticsSummary, useAnalyticsTimeseries, useDeployments } from '@/hooks/usePlatform'

const WINDOWS = [7, 30, 90]

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-card rounded-lg border border-border p-4">
      <p className="onto-label mb-1.5">{label}</p>
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  )
}

/** Dependency-free bar chart — runs stacked with completions, spend as a line of dots. */
function RunsChart({ data }: { data: { date: string; runs: number; completed: number; spend_usd: number }[] }) {
  if (!data.length) {
    return (
      <div className="bg-card rounded-lg border border-border p-8 text-center text-sm text-muted-foreground">
        No runs in this window yet.
      </div>
    )
  }
  const max = Math.max(...data.map((d) => d.runs), 1)
  return (
    <div className="bg-card rounded-lg border border-border p-5">
      <div className="flex items-end gap-1 h-40">
        {data.map((d) => (
          <div key={d.date} className="flex-1 flex flex-col justify-end group relative min-w-[4px]">
            <div
              className="w-full rounded-t-sm bg-muted"
              style={{ height: `${(d.runs / max) * 100}%` }}
            >
              <div
                className="w-full rounded-t-sm bg-foreground"
                style={{ height: `${d.runs ? (d.completed / d.runs) * 100 : 0}%`, marginTop: 'auto' }}
              />
            </div>
            <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover:block
                            whitespace-nowrap bg-foreground text-background text-[10px] px-2 py-1 rounded z-10">
              {d.date}: {d.completed}/{d.runs} completed · ${d.spend_usd.toFixed(2)}
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between mt-2 text-[10px] text-muted-foreground">
        <span>{data[0]?.date}</span>
        <span className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-foreground inline-block" /> completed
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-muted inline-block" /> started
          </span>
        </span>
        <span>{data[data.length - 1]?.date}</span>
      </div>
    </div>
  )
}

export default function AnalyticsPage() {
  const [days, setDays] = useState(30)
  const [manualHours, setManualHours] = useState(3.5)
  const [hourlyRate, setHourlyRate] = useState(75)

  const { data: summary, isLoading } = useAnalyticsSummary(days, manualHours, hourlyRate)
  const { data: series = [] } = useAnalyticsTimeseries(days)
  const { data: agents = [] } = useAgentScores(days)
  const { data: deployments = [] } = useDeployments()

  const exportUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/analytics/export.csv?days=${days}`

  if (isLoading || !summary) return <LoadingSkeleton />

  return (
    <div className="space-y-6">
      <p className="onto-label mb-1">Insights</p>
      <PageHeader
        title="ROI and delivery analytics"
        subtitle="Every figure is derived from real runs — no separate telemetry, nothing estimated that isn't labelled."
        action={
          <div className="flex gap-2">
            {WINDOWS.map((w) => (
              <Button key={w} size="sm" variant={days === w ? 'default' : 'outline'} onClick={() => setDays(w)}>
                {w}d
              </Button>
            ))}
            <a href={exportUrl} download>
              <Button size="sm" variant="outline">
                <Download className="h-3.5 w-3.5 mr-1.5" /> CSV
              </Button>
            </a>
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Hours saved" value={summary.hours_saved.toFixed(1)}
              sub={`≈ $${summary.money_saved_usd.toLocaleString()} at $${hourlyRate}/hr`} />
        <Stat label="Cost per merged run" value={`$${summary.cost_per_completed_run_usd.toFixed(3)}`}
              sub={`$${summary.spend_usd.toFixed(2)} total model spend`} />
        <Stat label="Median ticket → merged" value={`${summary.median_cycle_hours.toFixed(1)}h`}
              sub={`${summary.runs_completed} of ${summary.runs_total} runs completed`} />
        <Stat label="Approval latency" value={`${summary.median_approval_latency_hours.toFixed(1)}h`}
              sub={`${summary.runs_awaiting_approval} waiting now`} />
      </div>

      {summary.roi_multiple !== null && (
        <div className="bg-card rounded-lg border border-border p-5 flex items-start gap-3">
          <TrendingUp className="h-5 w-5 text-[#E8632A] mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">
              {summary.roi_multiple}× return over model spend in the last {days} days
            </p>
            <p className="text-sm text-muted-foreground mt-1">{summary.assumptions.note}</p>
            <div className="flex flex-wrap gap-3 mt-3 text-sm">
              <label className="flex items-center gap-2">
                <span className="text-muted-foreground">Manual hours / ticket</span>
                <input
                  type="number" step="0.5" min="0" max="80" value={manualHours}
                  onChange={(e) => setManualHours(Number(e.target.value))}
                  className="w-20 rounded-md border border-input bg-background px-2 py-1"
                />
              </label>
              <label className="flex items-center gap-2">
                <span className="text-muted-foreground">Engineer $/hour</span>
                <input
                  type="number" step="5" min="0" max="1000" value={hourlyRate}
                  onChange={(e) => setHourlyRate(Number(e.target.value))}
                  className="w-24 rounded-md border border-input bg-background px-2 py-1"
                />
              </label>
            </div>
          </div>
        </div>
      )}

      <div>
        <p className="onto-label mb-2">01 — Throughput</p>
        <RunsChart data={series} />
      </div>

      <div>
        <p className="onto-label mb-2">02 — Agent scorecard</p>
        {agents.length === 0 ? (
          <div className="bg-card rounded-lg border border-border p-8 text-center text-sm text-muted-foreground">
            No agent activity in this window.
          </div>
        ) : (
          <div className="bg-card border border-border rounded-lg overflow-hidden overflow-x-auto">
            <table className="w-full text-sm min-w-[640px]">
              <thead>
                <tr className="border-b border-border">
                  <th className="onto-label text-left px-4 py-2.5">Agent</th>
                  <th className="onto-label text-right px-4 py-2.5">Steps</th>
                  <th className="onto-label text-right px-4 py-2.5">Success</th>
                  <th className="onto-label text-right px-4 py-2.5">Avg time</th>
                  <th className="onto-label text-right px-4 py-2.5">Spend</th>
                  <th className="onto-label text-right px-4 py-2.5">Human rating</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((a) => (
                  <tr key={a.agent_role} className="border-b border-border last:border-0">
                    <td className="px-4 py-2.5 capitalize font-medium">{a.agent_role}</td>
                    <td className="px-4 py-2.5 text-right">{a.steps}</td>
                    <td className="px-4 py-2.5 text-right">
                      <span className={a.success_rate >= 70 ? '' : 'text-[#E8632A]'}>
                        {a.success_rate}%
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-muted-foreground">{a.avg_duration_sec}s</td>
                    <td className="px-4 py-2.5 text-right">${a.spend_usd.toFixed(3)}</td>
                    <td className="px-4 py-2.5 text-right">
                      {a.quality_score === null ? (
                        <span className="text-muted-foreground">—</span>
                      ) : (
                        <>👍 {a.thumbs_up} · 👎 {a.thumbs_down}</>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div>
        <p className="onto-label mb-2">03 — Deployment history</p>
        {deployments.length === 0 ? (
          <div className="bg-card rounded-lg border border-border p-8 text-center text-sm text-muted-foreground">
            No environment promotions recorded yet.
          </div>
        ) : (
          <div className="bg-card border border-border rounded-lg divide-y divide-border">
            {deployments.slice(0, 12).map((d) => (
              <div key={d.id} className="px-4 py-3 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <span
                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                      d.status === 'succeeded' ? 'bg-emerald-600'
                        : d.status === 'rolled_back' ? 'bg-[#E8632A]' : 'bg-red-600'
                    }`}
                  />
                  <span className="font-medium capitalize">{d.environment}</span>
                  <span className="text-sm text-muted-foreground truncate">{d.message}</span>
                </div>
                <span className="text-xs text-muted-foreground shrink-0">
                  {d.approver_count} approver{d.approver_count === 1 ? '' : 's'} ·{' '}
                  {new Date(d.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
