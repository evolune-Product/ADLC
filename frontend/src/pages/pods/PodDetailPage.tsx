import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PodWizard } from '@/components/pods/PodWizard'
import { usePod, useUpdatePod, useDeletePod } from '@/hooks/usePods'
import type { PodFormData } from '@/components/pods/PodWizard'

export default function PodDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: pod, isLoading } = usePod(id!)
  const updateMutation = useUpdatePod(id!)
  const deleteMutation = useDeletePod()

  function handleSave(data: PodFormData) {
    updateMutation.mutate(
      { name: data.name, description: data.description, agents: data.agents },
      { onSuccess: () => {} }
    )
  }

  function handleDelete() {
    if (!confirm('Delete this pod? This cannot be undone.')) return
    deleteMutation.mutate(id!, { onSuccess: () => navigate('/pods') })
  }

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="h-8 w-48 rounded bg-muted animate-pulse" />
        <div className="h-64 rounded-lg border bg-muted/40 animate-pulse" />
      </div>
    )
  }

  if (!pod) {
    return (
      <div className="max-w-2xl mx-auto">
        <p className="text-muted-foreground">Pod not found.</p>
        <Button variant="link" className="px-0 mt-2" onClick={() => navigate('/pods')}>
          Back to Pods
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => navigate('/pods')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-semibold">{pod.name}</h1>
            {pod.description && (
              <p className="text-sm text-muted-foreground mt-0.5">{pod.description}</p>
            )}
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="text-destructive hover:text-destructive"
          onClick={handleDelete}
          disabled={deleteMutation.isPending}
        >
          <Trash2 className="h-4 w-4 mr-1.5" />
          Delete
        </Button>
      </div>

      <PodWizard
        initial={pod}
        onSave={handleSave}
        loading={updateMutation.isPending}
      />
    </div>
  )
}
