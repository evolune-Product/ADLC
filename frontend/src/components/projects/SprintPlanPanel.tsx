import { useState } from 'react'
import { AlertTriangle, CheckCircle2, GanttChartSquare, RefreshCw, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  useGenerateSprintPlan, useSprintBacklog, useSprintPlan, useWriteBackSprintPlan,
} from '@/hooks/usePlatform'
import type { SprintHealth } from '@/types/platform'

const HEALTH_DOT: Record<SprintHealth, string> = {
  on_track: 'bg-emerald-600',
  at_risk: 'bg-[#E8632A]',
  blocked: 'bg-red-600',
}

const HEALTH_LABEL: Record<SprintHealth, string> = {
  on_track: 'On track', at_risk: 'At risk', blocked: 'Blocked',
}

const RISK_BADGE: Record<SprintHealth, string> = {
  on_track: 'bg-emerald-50 text-emerald-700',
  at_risk: 'bg-orange-50 text-[#E8632A]',
  blocked: 'bg-red-50 text-red-700',
}

/**
 * AI sprint planning — story-point estimation, dependency detection, and a
 * capacity-bound selection, all from one metered LLM call over the project's
 * never-started backlog. None of the execution-layer competitors (Devin,
 * Factory, GitHub Agent HQ, OpenHands) plan the sprint a ticket comes from —
 * they only execute it once scheduled. Atlassian's Rovo Sprint Planning Agent
 * does plan sprints, but stops at the Jira backlog; this feeds the same
 * estimate into a governed pipeline (policy gate, cost, audit) across Jira
 * *and* Linear. See documents/RESEARCH_TRIAGE_2026-08.md.
 */
export default function SprintPlanPanel({ projectId, writebackEnabled }: {
  projectId: string
  writebackEnabled: boolean
}) {
  const { data: plan, isLoading } = useSprintPlan(projectId)
  const { data: backlog } = useSprintBacklog(projectId)
  const generate = useGenerateSprintPlan(projectId)
  const writeBack = useWriteBackSprintPlan(projectId)

  const [capacity, setCapacity] = useState('20')

  const backlogCount = backlog?.count ?? 0

  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <GanttChartSquare className="h-4 w-4" />
          <p className="font-medium text-sm">Sprint planning</p>
          {plan && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className={`w-1.5 h-1.5 rounded-full ${HEALTH_DOT[plan.health]}`} />
              {HEALTH_LABEL[plan.health]}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Label className="text-xs text-muted-foreground shrink-0">Capacity</Label>
          <Input
            type="number"
            min={1}
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
            className="h-8 w-20 text-sm"
          />
          <Button
            size="sm"
            disabled={generate.isPending || backlogCount === 0}
            onClick={() => generate.mutate({ capacity_points: Number(capacity) || 20, write_back: false })}
            title={backlogCount === 0 ? 'No unstarted tickets to plan from' : undefined}
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${generate.isPending ? 'animate-spin' : ''}`} />
            {plan ? 'Re-plan' : 'Generate plan'}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="p-4 space-y-2">
          {[1, 2].map((i) => <div key={i} className="h-10 rounded bg-muted/40 animate-pulse" />)}
        </div>
      ) : !plan ? (
        <div className="px-4 py-8 text-center">
          <p className="text-sm text-muted-foreground">
            {backlogCount > 0
              ? `${backlogCount} unstarted ticket${backlogCount === 1 ? '' : 's'} in the backlog. Set a capacity and generate a plan.`
              : 'No unstarted tickets — sync from Jira/Linear, or start a run to see it move here.'}
          </p>
        </div>
      ) : (
        <>
          <div className="px-4 py-3 border-b border-border flex items-center justify-between text-sm">
            <p className="text-muted-foreground">{plan.summary}</p>
            <span className="font-medium shrink-0 ml-4">
              {plan.committed_points} / {plan.capacity_points} pts
            </span>
          </div>

          <div className="divide-y divide-border">
            {plan.estimates.map((e) => (
              <div key={e.id} className="flex items-start gap-3 px-4 py-3">
                <div className="mt-0.5 shrink-0">
                  {e.included_in_sprint ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <div className="h-4 w-4 rounded-full border border-border" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono text-muted-foreground">{e.jira_id}</span>
                    <span className="text-sm font-medium truncate">{e.title}</span>
                    <span className="onto-label !normal-case rounded bg-secondary px-1.5 py-0.5 text-[0.65rem]">
                      {e.story_points} pts
                    </span>
                    {e.risk !== 'on_track' && (
                      <span className={`rounded px-1.5 py-0.5 text-xs flex items-center gap-1 ${RISK_BADGE[e.risk]}`}>
                        <AlertTriangle className="h-3 w-3" /> {HEALTH_LABEL[e.risk]}
                      </span>
                    )}
                  </div>
                  {e.complexity_reasoning && (
                    <p className="text-xs text-muted-foreground mt-0.5">{e.complexity_reasoning}</p>
                  )}
                  {e.depends_on.length > 0 && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Depends on: <span className="font-mono">{e.depends_on.join(', ')}</span>
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {writebackEnabled && (
            <div className="px-4 py-3 border-t border-border flex justify-end">
              <Button
                size="sm"
                variant="outline"
                disabled={writeBack.isPending || plan.written_back}
                onClick={() => writeBack.mutate(plan.id)}
              >
                <Send className="h-3.5 w-3.5 mr-1.5" />
                {plan.written_back ? 'Estimates posted' : 'Write estimates to tracker'}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
