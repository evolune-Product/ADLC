import { useNavigate } from 'react-router-dom'
import { Plus, UserCircle2, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatsGrid } from '@/components/ui/StatsGrid'
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { usePersonas, useDeletePersona } from '@/hooks/usePersonas'

export default function PersonasPage() {
  const navigate = useNavigate()
  const { data: personas = [], isLoading } = usePersonas()
  const deleteMutation = useDeletePersona()

  return (
    <div className="space-y-6">
      <PageHeader
        title="Personas"
        subtitle="Simulated users the QA pipeline can drive through your running app."
        action={
          <Button onClick={() => navigate('/personas/new')}>
            <Plus className="h-4 w-4 mr-2" />
            New Persona
          </Button>
        }
      />

      <StatsGrid stats={[{ label: 'Total', value: personas.length }]} />

      {isLoading ? (
        <LoadingSkeleton />
      ) : personas.length === 0 ? (
        <EmptyState
          icon={<UserCircle2 className="h-10 w-10" />}
          title="No personas yet"
          subtitle="Create one to describe who is using your product and what they are trying to do."
          action={
            <Button variant="outline" onClick={() => navigate('/personas/new')}>
              <Plus className="h-4 w-4 mr-2" />
              New Persona
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {personas.map((persona) => (
            <Card
              key={persona.id}
              className="cursor-pointer hover:bg-accent/50 transition-colors"
              onClick={() => navigate(`/personas/${persona.id}`)}
            >
              <CardContent className="flex items-center gap-4 p-4">
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{persona.name}</p>
                  <p className="text-sm text-muted-foreground truncate mt-0.5">{persona.description}</p>
                  <p className="text-xs text-muted-foreground mt-1 truncate">{persona.entry_url}</p>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  className="shrink-0 text-destructive hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteMutation.mutate(persona.id)
                  }}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
