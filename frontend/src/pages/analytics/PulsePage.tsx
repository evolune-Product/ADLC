/**
 * Engineering Pulse — delivery health for the person accountable for it.
 *
 * Deliberately a separate page from Insights. Insights answers "was this worth
 * the money", which is a quarterly finance conversation. This answers "where is
 * my pipeline stuck this week and does the team trust what came out of it",
 * which is a Monday-morning one. A single page trying to do both serves neither.
 *
 * The framing choice that matters: the headline is not "agents did N things".
 * It is **where the time went** — because on almost every real team the agents
 * finish in minutes and the change then waits hours for a human, and no other
 * screen in this product makes that visible.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowRight, ArrowUpRight,
  Clock, GitCommitHorizontal, ShieldCheck, ThumbsDown, ThumbsUp,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { usePulse } from '@/hooks/usePlatform'

const WINDOWS = [7, 30, 90]

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'] as const

const SEVERITY_TINT: Record<string, string> = {
  critical: 'bg-red-600',
  high: 'bg-[#E8632A]',
  medium: 'bg-amber-500',
  low: 'bg-muted-foreground/50',
  info: 'bg-muted-foreground/30',
}

function Trend({ trend, invert }: {
  trend: { direction: string; change_pct: number | null }
  /** For findings, "up" is bad. For throughput, "up" is good. */
  invert?: boolean
}) {
  if (trend.change_pct === null || trend.direction === 'flat') {
    return <span className="text-xs text-muted-foreground">no change</span>
  }
  const up = trend.direction === 'up'
  const good = invert ? !up : up
  const Icon = up ? ArrowUpRight : ArrowDownRight
  return (
    <span className={cn('text-xs inline-flex items-center gap-0.5',
      good ? 'text-emerald-600' : 'text-[#E8632A]')}>
      <Icon className="h-3 w-3" />
      {Math.abs(trend.change_pct)}%
    </span>
  )
}

function Stat({ label, value, sub, trend, invert, icon: Icon }: {
  label: string; value: string; sub?: string
  trend?: { direction: string; change_pct: number | null }
  invert?: boolean
  icon?: typeof Activity
}) {
  return (
    <div className="bg-card rounded-lg border border-border p-4">
      <div className="flex items-center justify-between mb-1.5">
        <p className="onto-label">{label}</p>
        {Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground" />}
      </div>
      <div className="flex items-baseline gap-2">
        <p className="app-metric text-2xl font-semibold tabular-nums">{value}</p>
        {trend && <Trend trend={trend} invert={invert} />}
      </div>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  )
}

export default function PulsePage() {
  const [days, setDays] = useState(30)
  const { data, isLoading } = usePulse(days)

  if (isLoading) return <LoadingSkeleton />
  if (!data) return null

  const { flow, bottleneck, quality, trust } = data
  const slowestStage = bottleneck.stages[0]
  const maxStage = Math.max(...bottleneck.stages.map((s) => s.median_minutes), 1)
  const maxSeverity = Math.max(...Object.values(quality.by_severity), 1)

  return (
    <div className="space-y-6">
      <p className="onto-label mb-1">Observe</p>
      <PageHeader
        title="Engineering Pulse"
        subtitle="Where delivery time actually goes, and whether the team trusts the output."
        action={
          <div className="flex gap-1">
            {WINDOWS.map((w) => (
              <button
                key={w}
                onClick={() => setDays(w)}
                className={cn(
                  'px-2.5 py-1 rounded text-xs transition-colors',
                  w === days
                    ? 'bg-foreground text-background font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-foreground/5',
                )}
              >
                {w}d
              </button>
            ))}
          </div>
        }
      />

      {/* ── Flow: the DORA-shaped four ─────────────────────────────────────── */}
      <section>
        <p className="onto-label mb-2">01 — Flow</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            label="Deploy frequency"
            value={`${flow.deploys_per_week}/wk`}
            sub={`${flow.deploys} deploys in ${days} days`}
            icon={GitCommitHorizontal}
          />
          <Stat
            label="Lead time"
            value={flow.median_lead_time_hours ? `${flow.median_lead_time_hours}h` : '—'}
            sub="Median, ticket picked up → deployed"
            icon={Clock}
          />
          <Stat
            label="Change failure rate"
            value={`${flow.change_failure_rate}%`}
            sub="Deploys that failed or were rolled back"
            icon={AlertTriangle}
          />
          <Stat
            label="Throughput"
            value={String(flow.runs_completed)}
            sub="Runs completed"
            trend={flow.throughput_trend}
            icon={Activity}
          />
        </div>
      </section>

      {/* ── Bottleneck: the honest one ─────────────────────────────────────── */}
      <section>
        <p className="onto-label mb-2">02 — Where the time goes</p>

        {bottleneck.awaiting_approval > 0 && (
          <div className="mb-3 rounded-lg border border-[#E8632A]/30 bg-[#E8632A]/5 p-4 flex items-start gap-3">
            <Clock className="h-4 w-4 text-[#E8632A] mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium">
                {bottleneck.awaiting_approval} run{bottleneck.awaiting_approval === 1 ? '' : 's'} waiting on a human
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                The oldest has been waiting {bottleneck.oldest_wait_hours}h. The pipeline
                is not the constraint here — the queue in front of a person is.
              </p>
            </div>
            <Link to="/runs" className="text-xs inline-flex items-center gap-1 text-[#E8632A] hover:underline shrink-0">
              Review <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        )}

        <div className="grid gap-3 lg:grid-cols-2">
          {/* Stage durations */}
          <div className="bg-card rounded-lg border border-border p-5">
            <p className="text-sm font-medium mb-1">Pipeline stages</p>
            <p className="text-xs text-muted-foreground mb-4">
              {slowestStage
                ? `${slowestStage.stage} is the slowest stage at ${slowestStage.median_minutes} min median.`
                : 'No completed steps in this window yet.'}
            </p>
            <div className="space-y-2.5">
              {bottleneck.stages.map((s) => (
                <div key={s.stage}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="capitalize">{s.stage}</span>
                    <span className="app-metric text-muted-foreground">
                      {s.median_minutes} min · {s.runs} steps
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-foreground"
                      style={{ width: `${(s.median_minutes / maxStage) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
              {bottleneck.stages.length === 0 && (
                <p className="text-sm text-muted-foreground">Nothing measured yet.</p>
              )}
            </div>
          </div>

          {/* Reviewer latency */}
          <div className="bg-card rounded-lg border border-border p-5">
            <p className="text-sm font-medium mb-1">Approval wait, by reviewer</p>
            <p className="text-xs text-muted-foreground mb-4">
              Time from the Dev agent finishing to a decision being recorded.
            </p>
            {bottleneck.reviewers.length === 0 ? (
              <p className="text-sm text-muted-foreground">No approvals recorded yet.</p>
            ) : (
              <div className="space-y-2">
                {bottleneck.reviewers.map((r) => (
                  <div key={r.reviewer_id} className="flex items-center justify-between text-sm">
                    <span className="app-metric text-xs text-muted-foreground truncate">
                      {r.reviewer_id.slice(0, 8)}
                    </span>
                    <span className="flex items-center gap-3">
                      <span className="text-xs text-muted-foreground">{r.decisions} decisions</span>
                      <span className="app-metric tabular-nums">{r.median_wait_hours}h</span>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Quality ────────────────────────────────────────────────────────── */}
      <section>
        <p className="onto-label mb-2">03 — What review keeps finding</p>
        <div className="grid gap-3 lg:grid-cols-3">
          <Stat
            label="Findings"
            value={String(quality.findings_total)}
            sub={`${quality.findings_per_run} per completed run`}
            trend={quality.trend}
            invert
          />
          <Stat
            label="Blocking findings"
            value={String(quality.blocking_findings)}
            sub="Critical + high severity"
            icon={ShieldCheck}
          />
          <div className="bg-card rounded-lg border border-border p-4">
            <p className="onto-label mb-2.5">By severity</p>
            <div className="space-y-1.5">
              {SEVERITY_ORDER.filter((s) => quality.by_severity[s]).map((s) => (
                <div key={s} className="flex items-center gap-2">
                  <span className="text-xs w-14 capitalize text-muted-foreground">{s}</span>
                  <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className={cn('h-full rounded-full', SEVERITY_TINT[s])}
                      style={{ width: `${(quality.by_severity[s] / maxSeverity) * 100}%` }}
                    />
                  </div>
                  <span className="app-metric text-xs tabular-nums w-6 text-right">
                    {quality.by_severity[s]}
                  </span>
                </div>
              ))}
              {quality.findings_total === 0 && (
                <p className="text-sm text-muted-foreground">Nothing found yet.</p>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust ──────────────────────────────────────────────────────────── */}
      <section>
        <p className="onto-label mb-2">04 — Whether the team trusts it</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            label="First-pass approval"
            value={trust.approval_rate_first_pass !== null ? `${trust.approval_rate_first_pass}%` : '—'}
            sub={`${trust.changes_requested} sent back for changes`}
          />
          <Stat
            label="Human rewrite"
            value={trust.median_human_edits_loc ? `${trust.median_human_edits_loc} LOC` : '—'}
            sub="Median lines a person changed afterwards"
          />
          <Stat
            label="Rated good"
            value={String(trust.positive)}
            sub={`of ${trust.feedback_count} rated runs`}
            icon={ThumbsUp}
          />
          <Stat
            label="Rated bad"
            value={String(trust.negative)}
            sub={trust.top_complaints[0]
              ? `Most common: ${trust.top_complaints[0].category.replace(/_/g, ' ')}`
              : 'No complaints logged'}
            icon={ThumbsDown}
          />
        </div>

        {trust.feedback_count === 0 && (
          <p className="mt-3 text-xs text-muted-foreground">
            Nobody has rated a run yet. The trust numbers stay empty until they do —
            an assumed satisfaction score would be worse than an honest blank.
          </p>
        )}
      </section>
    </div>
  )
}
