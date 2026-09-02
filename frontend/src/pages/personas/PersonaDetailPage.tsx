import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Trash2, PlayCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PersonaForm } from '@/components/personas/PersonaForm'
import { usePersona, useUpdatePersona, useDeletePersona } from '@/hooks/usePersonas'
import type { Persona } from '@/types/simulation'

export default function PersonaDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: persona, isLoading } = usePersona(id!)
  const updateMutation = useUpdatePersona(id!)
  const deleteMutation = useDeletePersona()

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 bg-muted animate-pulse rounded" />
        <div className="h-96 bg-muted animate-pulse rounded" />
      </div>
    )
  }

  if (!persona) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        Persona not found.{' '}
        <button className="underline" onClick={() => navigate('/personas')}>
          Go back
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/personas')}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-semibold">{persona.name}</h1>
            <p className="text-sm text-muted-foreground">{persona.entry_url}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => navigate(`/simulations?persona_id=${persona.id}`)}
          >
            <PlayCircle className="h-4 w-4 mr-1" />
            Simulate
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-destructive hover:text-destructive"
            disabled={deleteMutation.isPending}
            onClick={() =>
              deleteMutation.mutate(persona.id, {
                onSuccess: () => navigate('/personas'),
              })
            }
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Delete
          </Button>
        </div>
      </div>

      <PersonaForm
        initial={persona}
        loading={updateMutation.isPending}
        onSave={(data) => updateMutation.mutate(data as Partial<Persona>)}
      />
    </div>
  )
}
