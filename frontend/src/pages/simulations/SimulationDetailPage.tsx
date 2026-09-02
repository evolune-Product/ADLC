import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ExternalLink, Bell, TicketCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { SeverityBadge, StatusDot } from '@/components/simulations/SeverityBadge'
import { FindingScreenshot } from '@/components/simulations/FindingScreenshot'
import { useSimulation } from '@/hooks/useSimulations'

export default function SimulationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: run, isLoading } = useSimulation(id)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 bg-muted animate-pulse rounded" />
        <div className="h-40 bg-muted animate-pulse rounded" />
      </div>
    )
  }

  if (!run) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        Simulation run not found.{' '}
        <button className="underline" onClick={() => navigate('/simulations')}>
          Go back
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/simulations')}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <div className="flex-1 min-w-0">
          <p className="onto-label mb-1">Simulation Run</p>
          <h1 className="text-xl font-bold text-foreground tracking-tight truncate">
            {run.persona_name ?? '(deleted persona)'} — {run.target_url}
          </h1>
        </div>
        <StatusDot status={run.status} />
      </div>

      <Card>
        <CardContent className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="onto-label mb-1">Steps</p>
            <p className="font-medium">{run.steps_taken} / {run.max_steps}</p>
          </div>
          <div>
            <p className="onto-label mb-1">Findings</p>
            <p className="font-medium">{run.findings?.length ?? 0}</p>
          </div>
          <div>
            <p className="onto-label mb-1">Started</p>
            <p className="font-medium">{run.started_at ? new Date(run.started_at).toLocaleString() : '—'}</p>
          </div>
          <div>
            <p className="onto-label mb-1">Completed</p>
            <p className="font-medium">{run.completed_at ? new Date(run.completed_at).toLocaleString() : '—'}</p>
          </div>
          {run.ticket_jira_id && (
            <div className="col-span-2 sm:col-span-4">
              <p className="onto-label mb-1">Testing ticket</p>
              {run.ticket_url ? (
                <a href={run.ticket_url} target="_blank" rel="noreferrer" className="text-sm font-medium underline inline-flex items-center gap-1">
                  {run.ticket_jira_id} <ExternalLink className="h-3 w-3" />
                </a>
              ) : (
                <p className="font-medium">{run.ticket_jira_id}</p>
              )}
            </div>
          )}
          {run.summary && (
            <div className="col-span-2 sm:col-span-4">
              <p className="onto-label mb-1">Summary</p>
              <p className="text-sm">{run.summary}</p>
            </div>
          )}
          {run.error_message && (
            <div className="col-span-2 sm:col-span-4">
              <p className="onto-label mb-1 text-destructive">Error</p>
              <p className="text-sm text-destructive">{run.error_message}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-foreground">Findings</h2>

        {!run.findings || run.findings.length === 0 ? (
          <div className="flex flex-col items-center justify-center bg-card rounded-lg border border-border border-dashed py-12 gap-2">
            <p className="text-sm font-medium text-foreground">
              {run.status === 'completed' || run.status === 'failed' ? 'No issues flagged' : 'Waiting for the agent…'}
            </p>
            <p className="text-xs text-muted-foreground">
              {run.status === 'completed' || run.status === 'failed'
                ? 'The persona did not flag anything broken or confusing during this run.'
                : 'Findings will appear here as the simulation progresses.'}
            </p>
          </div>
        ) : (
          run.findings.map((finding) => (
            <Card key={finding.id}>
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <SeverityBadge severity={finding.severity} />
                      {finding.step_number != null && (
                        <span className="text-xs text-muted-foreground">step {finding.step_number}</span>
                      )}
                    </div>
                    <p className="font-medium mt-1.5">{finding.title}</p>
                    <p className="text-sm text-muted-foreground mt-0.5">{finding.description}</p>
                  </div>
                </div>

                {finding.reproduction_steps.length > 0 && (
                  <details className="text-xs text-muted-foreground">
                    <summary className="cursor-pointer select-none font-medium text-foreground">
                      Reproduction steps ({finding.reproduction_steps.length})
                    </summary>
                    <ol className="list-decimal list-inside mt-2 space-y-1">
                      {finding.reproduction_steps.map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </details>
                )}

                {finding.screenshot_path && (
                  <FindingScreenshot simulationId={run.id} findingId={finding.id} />
                )}

                <div className="flex items-center gap-4 text-xs text-muted-foreground pt-1 border-t border-border">
                  <span className="inline-flex items-center gap-1">
                    <Bell className="h-3 w-3" />
                    {finding.notified ? 'Notified' : 'Not notified'}
                  </span>
                  {run.ticket_url ? (
                    finding.posted_to_tracker ? (
                      <a href={run.ticket_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline">
                        <TicketCheck className="h-3 w-3" />
                        Filed to {run.ticket_jira_id}
                      </a>
                    ) : (
                      <span className="inline-flex items-center gap-1">
                        <TicketCheck className="h-3 w-3" />
                        Not filed to tracker
                      </span>
                    )
                  ) : (
                    <span className="inline-flex items-center gap-1">
                      <TicketCheck className="h-3 w-3" />
                      No ticket linked to this run
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}
