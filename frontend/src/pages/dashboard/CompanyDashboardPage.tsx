/**
 * Company home dashboard — Company OS step 20.
 *
 * Deliberately separate from Desk (`/desk`, "what do I need to act on right
 * now") and from Pulse (`/pulse`, delivery-flow bottlenecks). This page
 * answers "how is the company doing" — activity, approvals in flight, agent
 * usage, workflow health, integration status, recent conversation, and
 * usage/billing — for whatever slice of the org the viewer is scoped to
 * (org-wide for owner/admin, one department for a department head, personal
 * for everyone else). Every number is a real aggregate from GET
 * /company-dashboard; there is no client-side invented fallback.
 */
import { Link } from 'react-router-dom'
import {
  Activity, AlertCircle, Building2, GitBranch, MessagesSquare,
  Plug, ShieldCheck,
} from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { useCompanyDashboard } from '@/hooks/useDashboard'
import { cn } from '@/lib/utils'

function Stat({ label, value, sub, icon: Icon }: {
  label: string; value: string | number; sub?: string; icon?: typeof Activity
}) {
  return (
    <div className="bg-card rounded-lg border border-border p-4">
      <div className="flex items-center justify-between mb-1.5">
        <p className="onto-label">{label}</p>
        {Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground" />}
      </div>
      <p className="app-metric text-2xl font-semibold tabular-nums">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  )
}

const SCOPE_LABEL: Record<string, string> = {
  org: 'Organization-wide',
  department: 'Your department',
  member: 'Your activity',
}

export default function CompanyDashboardPage() {
  const { data, isLoading } = useCompanyDashboard()

  if (isLoading) return <LoadingSkeleton rows={4} />
  if (!data) return null

  const {
    scope, work, workflow_executions, pending_approvals, agent_activity,
    workflow_health, integration_health, recent_conversations, usage,
  } = data

  return (
    <div className="space-y-6">
      <PageHeader
        title="Company"
        subtitle={`${SCOPE_LABEL[scope] ?? scope} — how the company is doing right now, not what's waiting on you (see Desk for that).`}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Work items" value={work.total}
              sub={Object.entries(work.by_status).map(([s, n]) => `${n} ${s}`).join(' · ') || 'none yet'}
              icon={Building2} />
        <Stat label="Workflow executions" value={workflow_executions.total}
              sub={Object.entries(workflow_executions.by_status).map(([s, n]) => `${n} ${s}`).join(' · ') || 'none yet'}
              icon={GitBranch} />
        <Stat label="Pending approvals" value={pending_approvals}
              sub={pending_approvals > 0 ? 'across work items and workflow gates' : 'nothing waiting'}
              icon={AlertCircle} />
        <Stat label="Agent runs (30d)" value={agent_activity.agent_task_runs_last_30d}
              sub="workflow agent_task nodes executed" icon={Activity} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-card rounded-lg border border-border p-4">
          <p className="onto-label mb-3">Workflow health</p>
          {workflow_health.length === 0 ? (
            <p className="text-sm text-muted-foreground">No workflow has run yet.</p>
          ) : (
            <div className="space-y-2">
              {workflow_health.map((w) => (
                <Link key={w.workflow_id} to={`/workflows/${w.workflow_id}`}
                      className="flex items-center justify-between text-sm hover:bg-muted rounded px-2 py-1.5 -mx-2">
                  <span className="text-foreground truncate">{w.name}</span>
                  <span className="text-xs text-muted-foreground tabular-nums flex items-center gap-2">
                    {w.completed}/{w.total_executions} completed
                    <span className={cn(
                      'px-1.5 py-0.5 rounded',
                      w.success_rate >= 90 ? 'text-emerald-600' :
                      w.success_rate >= 60 ? 'text-amber-600' : 'text-[#E8632A]',
                    )}>{w.success_rate}%</span>
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="bg-card rounded-lg border border-border p-4">
          <p className="onto-label mb-3 flex items-center gap-1.5"><Plug className="h-3.5 w-3.5" /> Integration health</p>
          {integration_health === null ? (
            <p className="text-sm text-muted-foreground">Not visible at your access level.</p>
          ) : Object.keys(integration_health).length === 0 ? (
            <p className="text-sm text-muted-foreground">No company APIs connected yet — see Plugins.</p>
          ) : (
            <div className="space-y-1.5">
              {Object.entries(integration_health).map(([status, n]) => (
                <div key={status} className="flex items-center justify-between text-sm">
                  <span className="capitalize text-foreground">{status}</span>
                  <span className="tabular-nums text-muted-foreground">{n}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-card rounded-lg border border-border p-4">
          <p className="onto-label mb-3 flex items-center gap-1.5"><MessagesSquare className="h-3.5 w-3.5" /> Recent conversations</p>
          {recent_conversations.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent messages.</p>
          ) : (
            <div className="space-y-2">
              {recent_conversations.map((m) => (
                <Link key={m.id} to={`/workspace/${m.channel_id}`}
                      className="block text-sm text-foreground hover:bg-muted rounded px-2 py-1.5 -mx-2 truncate">
                  {m.preview || <span className="text-muted-foreground italic">(empty)</span>}
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="bg-card rounded-lg border border-border p-4">
          <p className="onto-label mb-3 flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5" /> Usage &amp; billing</p>
          <div className="flex items-baseline gap-2 mb-1">
            <p className="app-metric text-2xl font-semibold">{usage.plan_name}</p>
            <span className="text-xs text-muted-foreground">plan</span>
          </div>
          <p className="text-sm text-muted-foreground">
            {usage.runs_included === 0
              ? `${usage.runs_used} runs used, unlimited plan`
              : `${usage.runs_used} / ${usage.runs_included} runs used this period`}
          </p>
          <p className="text-sm text-muted-foreground">${usage.spend_usd.toFixed(2)} spent this period</p>
          <Link to="/billing" className="text-xs text-[#E8632A] hover:underline mt-2 inline-block">Manage billing →</Link>
        </div>
      </div>
    </div>
  )
}
