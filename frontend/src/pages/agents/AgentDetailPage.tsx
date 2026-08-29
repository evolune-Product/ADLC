import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { AgentWizard } from '@/components/agents/AgentWizard'
import { useAgent, useUpdateAgent, useDeleteAgent } from '@/hooks/useAgents'
import type { Agent } from '@/types'

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: agent, isLoading } = useAgent(id!)
  const updateMutation = useUpdateAgent(id!)
  const deleteMutation = useDeleteAgent()

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-4xl">
        <div className="h-8 w-48 bg-muted animate-pulse rounded" />
        <div className="h-64 bg-muted animate-pulse rounded" />
      </div>
    )
  }

  if (!agent) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        Agent not found.{' '}
        <button className="underline" onClick={() => navigate('/agents')}>Go back</button>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/agents')}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-semibold">{agent.name}</h1>
            <p className="text-sm text-muted-foreground capitalize">{agent.role} agent · {agent.llm_model}</p>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="text-destructive hover:text-destructive"
          disabled={deleteMutation.isPending}
          onClick={() => deleteMutation.mutate(agent.id, { onSuccess: () => navigate('/agents') })}
        >
          <Trash2 className="h-4 w-4 mr-1" />
          Delete
        </Button>
      </div>

      <AgentWizard
        initial={agent}
        loading={updateMutation.isPending}
        onSave={(data) => updateMutation.mutate(data as Partial<Agent>)}
      />
    </div>
  )
}
