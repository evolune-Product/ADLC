import { useNavigate } from 'react-router-dom'
import { PodWizard } from '@/components/pods/PodWizard'
import { useCreatePod } from '@/hooks/usePods'
import type { PodFormData } from '@/components/pods/PodWizard'
import type { PodAgent } from '@/types'

export default function NewPodPage() {
  const navigate = useNavigate()
  const createMutation = useCreatePod()

  function handleSave(data: PodFormData) {
    createMutation.mutate(
      { name: data.name, description: data.description, agents: data.agents as unknown as PodAgent[] },
      { onSuccess: (pod) => navigate(`/pods/${pod.id}`) }
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">New Pod</h1>
        <p className="text-sm text-muted-foreground mt-1">Configure a pod by naming it and assembling an agent workflow.</p>
      </div>
      <PodWizard onSave={handleSave} loading={createMutation.isPending} />
    </div>
  )
}
