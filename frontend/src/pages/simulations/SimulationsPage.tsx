import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Plus, TestTube2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatsGrid } from '@/components/ui/StatsGrid'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { StatusDot } from '@/components/simulations/SeverityBadge'
import { StartSimulationDialog } from '@/components/simulations/StartSimulationDialog'
import { useSimulations } from '@/hooks/useSimulations'

export default function SimulationsPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const defaultPersonaId = searchParams.get('persona_id') ?? undefined
  const [dialogOpen, setDialogOpen] = useState(!!defaultPersonaId)

  const { data: runs = [], isLoading } = useSimulations()
  const running = runs.filter((r) => r.status === 'running' || r.status === 'pending').length
  const totalFindings = runs.reduce((sum, r) => sum + (r.finding_count ?? 0), 0)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Simulations"
        subtitle="Drive a persona through the running app and see what it finds."
        action={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Start Simulation
          </Button>
        }
      />

      <StatsGrid
        stats={[
          { label: 'Total runs', value: runs.length },
          { label: 'In progress', value: running },
          { label: 'Findings', value: totalFindings },
        ]}
      />

      {isLoading ? (
        <LoadingSkeleton />
      ) : runs.length === 0 ? (
        <EmptyState
          icon={<TestTube2 className="h-10 w-10" />}
          title="No simulations yet"
          subtitle="Pick a persona and a URL — the agent drives a real browser and reports what it finds."
          action={
            <Button variant="outline" onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Start Simulation
            </Button>
          }
        />
      ) : (
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left px-4 py-2.5"><span className="onto-label">Persona</span></th>
                <th className="text-left px-4 py-2.5 hidden sm:table-cell"><span className="onto-label">Target URL</span></th>
                <th className="text-left px-4 py-2.5"><span className="onto-label">Status</span></th>
                <th className="text-left px-4 py-2.5 hidden md:table-cell"><span className="onto-label">Steps</span></th>
                <th className="text-left px-4 py-2.5"><span className="onto-label">Findings</span></th>
                <th className="text-left px-4 py-2.5 hidden lg:table-cell"><span className="onto-label">Started</span></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run, i) => (
                <tr
                  key={run.id}
                  onClick={() => navigate(`/simulations/${run.id}`)}
                  className={`cursor-pointer hover:bg-muted/40 transition-colors ${i < runs.length - 1 ? 'border-b border-border' : ''}`}
                >
                  <td className="px-4 py-3">
                    <p className="text-xs font-medium text-foreground">{run.persona_name ?? '(deleted persona)'}</p>
                    {run.ticket_jira_id && (
                      <p className="text-[11px] text-muted-foreground">testing {run.ticket_jira_id}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell text-xs text-muted-foreground truncate max-w-[240px]">
                    {run.target_url}
                  </td>
                  <td className="px-4 py-3"><StatusDot status={run.status} /></td>
                  <td className="px-4 py-3 hidden md:table-cell text-xs text-muted-foreground">
                    {run.steps_taken} / {run.max_steps}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{run.finding_count ?? 0}</td>
                  <td className="px-4 py-3 hidden lg:table-cell text-xs text-muted-foreground">
                    {run.started_at ? new Date(run.started_at).toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <StartSimulationDialog open={dialogOpen} onOpenChange={setDialogOpen} defaultPersonaId={defaultPersonaId} />
    </div>
  )
}
