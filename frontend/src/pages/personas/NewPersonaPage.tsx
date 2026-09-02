import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PersonaForm } from '@/components/personas/PersonaForm'
import { useCreatePersona } from '@/hooks/usePersonas'
import type { Persona } from '@/types/simulation'

export default function NewPersonaPage() {
  const navigate = useNavigate()
  const createMutation = useCreatePersona()

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/personas')}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <div>
          <h1 className="text-2xl font-semibold">New Persona</h1>
          <p className="text-sm text-muted-foreground">Describe a simulated user for the QA pipeline to drive.</p>
        </div>
      </div>

      <PersonaForm
        loading={createMutation.isPending}
        onSave={(data) =>
          createMutation.mutate(data as Partial<Persona>, {
            onSuccess: (persona) => navigate(`/personas/${persona.id}`),
          })
        }
      />
    </div>
  )
}
