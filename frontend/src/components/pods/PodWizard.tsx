import { useState } from 'react'
import { ChevronUp, ChevronDown, X, Plus, Check, ArrowDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAgents } from '@/hooks/useAgents'
import type { Pod } from '@/types'
import type { PodAgentInput } from '@/hooks/usePods'

const ROLE_LABEL: Record<string, string> = {
  sprint: 'Sprint', dev: 'Dev', qa: 'QA', devops: 'DevOps', custom: 'Custom',
}

const FAILURE_OPTIONS = [
  { value: 'retry',    label: 'Retry same agent' },
  { value: 'escalate', label: 'Escalate to next'  },
  { value: 'stop',     label: 'Stop run'          },
]

export interface PodFormData {
  name: string
  description: string
  agents: PodAgentInput[]
}

interface Props {
  initial?: Partial<Pod>
  onSave: (data: PodFormData) => void
  loading: boolean
}

const STEPS = ['Pod Info', 'Agent Builder']

export function PodWizard({ initial, onSave, loading }: Props) {
  const [step, setStep] = useState(0)

  const [name, setName]               = useState(initial?.name ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')

  const [podAgents, setPodAgents] = useState<PodAgentInput[]>(
    initial?.agents?.map((pa) => ({
      agent_id:        pa.agent_id,
      execution_order: pa.execution_order,
      count:           pa.count,
      on_failure:      pa.on_failure,
      max_retries:     pa.max_retries,
    })) ?? []
  )

  const [showPicker, setShowPicker] = useState(false)
  const { data: allAgents = [] } = useAgents()
  const addedIds = new Set(podAgents.map((pa) => pa.agent_id))

  // ── Agent builder helpers ──
  function addAgent(agentId: string) {
    setPodAgents((prev) => [
      ...prev,
      {
        agent_id:        agentId,
        execution_order: prev.length + 1,
        count:           1,
        on_failure:      'retry',
        max_retries:     3,
      },
    ])
    setShowPicker(false)
  }

  function removeAgent(index: number) {
    setPodAgents((prev) => {
      const next = prev.filter((_, i) => i !== index)
      return next.map((pa, i) => ({ ...pa, execution_order: i + 1 }))
    })
  }

  function moveUp(index: number) {
    if (index === 0) return
    setPodAgents((prev) => {
      const next = [...prev]
      ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
      return next.map((pa, i) => ({ ...pa, execution_order: i + 1 }))
    })
  }

  function moveDown(index: number) {
    setPodAgents((prev) => {
      if (index === prev.length - 1) return prev
      const next = [...prev]
      ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
      return next.map((pa, i) => ({ ...pa, execution_order: i + 1 }))
    })
  }

  function updateAgent(index: number, field: keyof PodAgentInput, value: string | number) {
    setPodAgents((prev) =>
      prev.map((pa, i) => (i === index ? { ...pa, [field]: value } : pa))
    )
  }

  return (
    <div className="space-y-6">
      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {STEPS.map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => i < step && setStep(i)}
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium transition-colors ${
                i < step
                  ? 'bg-primary text-primary-foreground cursor-pointer'
                  : i === step
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {i < step ? <Check className="h-3.5 w-3.5" /> : i + 1}
            </button>
            <span className={`text-sm ${i === step ? 'font-medium' : 'text-muted-foreground'}`}>{label}</span>
            {i < STEPS.length - 1 && <div className="h-px w-8 bg-border" />}
          </div>
        ))}
      </div>

      {/* ── Step 1: Pod Info ── */}
      {step === 0 && (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Pod Name *</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Full-Stack Dev Pod" />
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What does this pod do?" />
          </div>
          <div className="flex justify-end">
            <Button onClick={() => setStep(1)} disabled={!name.trim()}>
              Next: Agent Builder
            </Button>
          </div>
        </div>
      )}

      {/* ── Step 2: Agent Builder ── */}
      {step === 1 && (
        <div className="space-y-5">
          {/* Agent list */}
          {podAgents.length === 0 ? (
            <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              No agents added yet. Click "Add Agent" to build the workflow.
            </div>
          ) : (
            <div className="space-y-3">
              {podAgents.map((pa, index) => {
                const agent = allAgents.find((a) => a.id === pa.agent_id)
                return (
                  <div key={pa.agent_id} className="space-y-1">
                    <div className="rounded-lg border p-4 space-y-3">
                      {/* Header */}
                      <div className="flex items-center gap-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold shrink-0">
                          {index + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{agent?.name ?? pa.agent_id}</p>
                          <p className="text-xs text-muted-foreground">
                            {ROLE_LABEL[agent?.role ?? ''] ?? agent?.role}
                          </p>
                        </div>
                        <div className="flex gap-1 shrink-0">
                          <Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => moveUp(index)}>
                            <ChevronUp className="h-4 w-4" />
                          </Button>
                          <Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => moveDown(index)}>
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                          <Button type="button" variant="ghost" size="sm" className="h-7 w-7 p-0 text-destructive hover:text-destructive" onClick={() => removeAgent(index)}>
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      {/* Config row */}
                      <div className="grid grid-cols-3 gap-3">
                        <div className="space-y-1">
                          <Label className="text-xs">Count</Label>
                          <Input
                            type="number"
                            min={1}
                            value={pa.count}
                            onChange={(e) => updateAgent(index, 'count', Number(e.target.value))}
                            className="h-8 text-sm"
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">On Failure</Label>
                          <select
                            value={pa.on_failure}
                            onChange={(e) => updateAgent(index, 'on_failure', e.target.value)}
                            className="w-full h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                          >
                            {FAILURE_OPTIONS.map((o) => (
                              <option key={o.value} value={o.value}>{o.label}</option>
                            ))}
                          </select>
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Max Retries</Label>
                          <Input
                            type="number"
                            min={0}
                            max={10}
                            value={pa.max_retries}
                            onChange={(e) => updateAgent(index, 'max_retries', Number(e.target.value))}
                            className="h-8 text-sm"
                          />
                        </div>
                      </div>
                    </div>
                    {/* Arrow between agents */}
                    {index < podAgents.length - 1 && (
                      <div className="flex justify-center py-1">
                        <ArrowDown className="h-4 w-4 text-muted-foreground" />
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Add agent button / picker */}
          {showPicker ? (
            <div className="rounded-md border divide-y max-h-48 overflow-y-auto">
              {allAgents.filter((a) => !addedIds.has(a.id) && a.is_active).length === 0 ? (
                <p className="p-3 text-sm text-muted-foreground">
                  {allAgents.length === 0
                    ? 'No agents yet — create one in Agents first.'
                    : 'All active agents already added.'}
                </p>
              ) : (
                allAgents
                  .filter((a) => !addedIds.has(a.id) && a.is_active)
                  .map((agent) => (
                    <button
                      key={agent.id}
                      type="button"
                      onClick={() => addAgent(agent.id)}
                      className="w-full flex items-center justify-between px-3 py-2 text-sm text-left hover:bg-accent transition-colors"
                    >
                      <span>{agent.name}</span>
                      <span className="text-xs text-muted-foreground">{ROLE_LABEL[agent.role] ?? agent.role}</span>
                    </button>
                  ))
              )}
            </div>
          ) : (
            <Button type="button" variant="outline" className="w-full" onClick={() => setShowPicker(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Agent
            </Button>
          )}

          <div className="flex justify-between pt-2">
            <Button variant="outline" onClick={() => setStep(0)}>Back</Button>
            <Button
              onClick={() => onSave({ name, description, agents: podAgents })}
              disabled={loading || podAgents.length === 0}
            >
              {loading ? 'Saving…' : 'Save Pod'}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
