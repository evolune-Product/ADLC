import { useNavigate } from 'react-router-dom'
import { Plus, Bot, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatsGrid } from '@/components/ui/StatsGrid'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { useAgents, useDeleteAgent, useToggleAgent } from '@/hooks/useAgents'

const ROLE_LABEL: Record<string, string> = {
  sprint: 'Sprint', dev: 'Dev', qa: 'QA', devops: 'DevOps', custom: 'Custom',
}

export default function AgentsPage() {
  const navigate = useNavigate()
  const { data: agents = [], isLoading } = useAgents()
  const deleteMutation = useDeleteAgent()
  const toggleMutation = useToggleAgent()

  return (
    <div className="space-y-6">
      <PageHeader
        title="Agents"
        subtitle="AI agents built from skills that execute SDLC tasks."
        action={
          <Button onClick={() => navigate('/agents/new')}>
            <Plus className="h-4 w-4 mr-2" />
            New Agent
          </Button>
        }
      />

      <StatsGrid
        stats={[
          { label: 'Total',    value: agents.length },
          { label: 'Active',   value: agents.filter((a) => a.is_active).length },
          { label: 'Inactive', value: agents.filter((a) => !a.is_active).length },
        ]}
      />

      {isLoading ? (
        <LoadingSkeleton />
      ) : agents.length === 0 ? (
        <EmptyState
          icon={<Bot className="h-10 w-10" />}
          title="No agents yet"
          subtitle="Create an agent by combining skills."
          action={
            <Button variant="outline" onClick={() => navigate('/agents/new')}>
              <Plus className="h-4 w-4 mr-2" />
              New Agent
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {agents.map((agent) => (
            <Card
              key={agent.id}
              className="cursor-pointer hover:bg-accent/50 transition-colors"
              onClick={() => navigate(`/agents/${agent.id}`)}
            >
              <CardContent className="flex items-center gap-4 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted shrink-0">
                  <Bot className="h-5 w-5" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium truncate">{agent.name}</p>
                    <span className="shrink-0 rounded-full bg-secondary px-2 py-0.5 text-xs">
                      {ROLE_LABEL[agent.role] ?? agent.role}
                    </span>
                    {!agent.is_active && (
                      <span className="shrink-0 rounded-full bg-muted text-muted-foreground px-2 py-0.5 text-xs">
                        Inactive
                      </span>
                    )}
                  </div>
                  {agent.description && (
                    <p className="text-sm text-muted-foreground truncate mt-0.5">{agent.description}</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    {agent.skills.length} skill{agent.skills.length !== 1 ? 's' : ''} · {agent.llm_model}
                  </p>
                </div>

                <div className="flex gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => toggleMutation.mutate(agent.id)}
                    disabled={toggleMutation.isPending}
                  >
                    {agent.is_active ? 'Disable' : 'Enable'}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => deleteMutation.mutate(agent.id)}
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
