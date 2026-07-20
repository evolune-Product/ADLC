import { useNavigate } from 'react-router-dom'
import { Plus, Layers, Trash2, Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatsGrid } from '@/components/ui/StatsGrid'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { usePods, useDeletePod, useDuplicatePod } from '@/hooks/usePods'

const ROLE_LABEL: Record<string, string> = {
  sprint: 'Sprint', dev: 'Dev', qa: 'QA', devops: 'DevOps', custom: 'Custom',
}

export default function PodsPage() {
  const navigate = useNavigate()
  const { data: pods = [], isLoading } = usePods()
  const deleteMutation    = useDeletePod()
  const duplicateMutation = useDuplicatePod()

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pods"
        subtitle="Groups of agents that execute SDLC workflows."
        action={
          <Button onClick={() => navigate('/pods/new')}>
            <Plus className="h-4 w-4 mr-2" />
            New Pod
          </Button>
        }
      />

      <StatsGrid
        stats={[
          { label: 'Total',    value: pods.length },
          { label: 'Active',   value: pods.filter((p) => p.is_active).length },
          { label: 'Inactive', value: pods.filter((p) => !p.is_active).length },
        ]}
      />

      {isLoading ? (
        <LoadingSkeleton height="h-28" />
      ) : pods.length === 0 ? (
        <EmptyState
          icon={<Layers className="h-10 w-10" />}
          title="No pods yet"
          subtitle="Create a pod by grouping agents into a workflow."
          action={
            <Button variant="outline" onClick={() => navigate('/pods/new')}>
              <Plus className="h-4 w-4 mr-2" />
              New Pod
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {pods.map((pod) => (
            <Card
              key={pod.id}
              className="cursor-pointer hover:bg-accent/50 transition-colors"
              onClick={() => navigate(`/pods/${pod.id}`)}
            >
              <CardContent className="flex items-center gap-4 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted shrink-0">
                  <Layers className="h-5 w-5" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium truncate">{pod.name}</p>
                    {!pod.is_active && (
                      <span className="shrink-0 rounded-full bg-muted text-muted-foreground px-2 py-0.5 text-xs">
                        Inactive
                      </span>
                    )}
                  </div>
                  {pod.description && (
                    <p className="text-sm text-muted-foreground truncate mt-0.5">{pod.description}</p>
                  )}
                  {/* Mini workflow preview */}
                  <div className="flex items-center gap-1 mt-1.5 flex-wrap">
                    {pod.agents.map((pa, i) => (
                      <span key={pa.id} className="flex items-center gap-1">
                        <span className="rounded bg-secondary px-1.5 py-0.5 text-xs">
                          {ROLE_LABEL[pa.agent_role] ?? pa.agent_role}: {pa.agent_name}
                        </span>
                        {i < pod.agents.length - 1 && (
                          <span className="text-muted-foreground text-xs">→</span>
                        )}
                      </span>
                    ))}
                    {pod.agents.length === 0 && (
                      <span className="text-xs text-muted-foreground">No agents configured</span>
                    )}
                  </div>
                </div>

                <div className="flex gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => duplicateMutation.mutate(pod.id)}
                    disabled={duplicateMutation.isPending}
                  >
                    <Copy className="h-3.5 w-3.5 mr-1" />
                    Duplicate
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => deleteMutation.mutate(pod.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
