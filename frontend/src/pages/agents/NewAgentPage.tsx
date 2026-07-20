import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { AgentWizard } from '@/components/agents/AgentWizard'
import { useCreateAgent } from '@/hooks/useAgents'

export default function NewAgentPage() {
  const navigate = useNavigate()
  const createMutation = useCreateAgent()

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/agents')}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <div>
          <h1 className="text-2xl font-semibold">New Agent</h1>
          <p className="text-sm text-muted-foreground">Configure an AI agent in 3 steps.</p>
        </div>
      </div>

      <AgentWizard
        loading={createMutation.isPending}
        onSave={(data) =>
          createMutation.mutate(data, {
            onSuccess: (agent) => navigate(`/agents/${agent.id}`),
          })
        }
      />
    </div>
  )
}
