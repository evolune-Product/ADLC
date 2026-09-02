import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { usePersonas } from '@/hooks/usePersonas'
import { useCreateSimulation } from '@/hooks/useSimulations'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Pre-selected persona, e.g. arriving from a Persona's own "Simulate" button. */
  defaultPersonaId?: string
}

export function StartSimulationDialog({ open, onOpenChange, defaultPersonaId }: Props) {
  const navigate = useNavigate()
  const { data: personas = [] } = usePersonas()
  const createMutation = useCreateSimulation()

  const [personaId, setPersonaId] = useState(defaultPersonaId ?? '')
  const [targetUrl, setTargetUrl] = useState('')

  // Keep the picker in sync if a different persona's "Simulate" link opens this
  // dialog while it's already mounted, and default the URL to that persona's
  // own entry_url as a starting point the user can still override.
  useEffect(() => {
    if (!open) return
    setPersonaId(defaultPersonaId ?? '')
    const persona = personas.find((p) => p.id === defaultPersonaId)
    setTargetUrl(persona?.entry_url ?? '')
  }, [open, defaultPersonaId]) // eslint-disable-line react-hooks/exhaustive-deps

  function handlePersonaChange(id: string) {
    setPersonaId(id)
    if (!targetUrl) {
      const persona = personas.find((p) => p.id === id)
      if (persona) setTargetUrl(persona.entry_url)
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!personaId || !targetUrl.trim()) return
    createMutation.mutate(
      { persona_id: personaId, target_url: targetUrl.trim() },
      {
        onSuccess: (run) => {
          onOpenChange(false)
          navigate(`/simulations/${run.id}`)
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Start a Simulation</DialogTitle>
          <DialogDescription>
            A persona will drive a real headless browser against this URL and report anything broken or confusing.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label>Persona *</Label>
            <select
              value={personaId}
              onChange={(e) => handlePersonaChange(e.target.value)}
              required
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">-- Select a persona --</option>
              {personas.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            {personas.length === 0 && (
              <p className="text-xs text-muted-foreground">
                No personas yet — <a href="/personas/new" className="underline">create one first</a>.
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label>Target URL *</Label>
            <Input
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="https://app.example.com/signup"
              required
            />
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={createMutation.isPending || !personaId || !targetUrl.trim()}>
              {createMutation.isPending ? 'Starting…' : 'Start Simulation'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
