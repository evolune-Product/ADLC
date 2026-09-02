import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { Persona } from '@/types/simulation'

interface PersonaFormData {
  name: string
  description: string
  entry_url: string
}

interface Props {
  initial?: Partial<Persona>
  onSave: (data: PersonaFormData) => void
  loading: boolean
}

export function PersonaForm({ initial, onSave, loading }: Props) {
  const [name, setName]             = useState(initial?.name ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [entryUrl, setEntryUrl]     = useState(initial?.entry_url ?? '')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim() || !description.trim() || !entryUrl.trim()) return
    onSave({ name, description, entry_url: entryUrl })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-1.5">
        <Label>Name *</Label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. First-time free trial signup"
          required
        />
      </div>

      <div className="space-y-1.5">
        <Label>Entry URL *</Label>
        <Input
          value={entryUrl}
          onChange={(e) => setEntryUrl(e.target.value)}
          placeholder="https://app.example.com/signup"
          required
        />
        <p className="text-xs text-muted-foreground">Where this persona lands first when a simulation starts.</p>
      </div>

      <div className="space-y-1.5">
        <Label>Goal / behavior *</Label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="A first-time user trying to sign up and hit the free trial. They are impatient, skim rather than read, and will bounce at the first confusing step."
          rows={6}
          required
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        />
        <p className="text-xs text-muted-foreground">
          Free-text natural-language description of who this persona is and what they are trying to do. Handed
          to the simulation agent verbatim on every step.
        </p>
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={loading || !name.trim() || !description.trim() || !entryUrl.trim()}>
          {loading ? 'Saving…' : 'Save Persona'}
        </Button>
      </div>
    </form>
  )
}
