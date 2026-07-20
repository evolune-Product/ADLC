import { useState } from 'react'
import { ChevronUp, ChevronDown, X, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useSkills } from '@/hooks/useSkills'
import { useConnections } from '@/hooks/useConnections'
import type { Agent } from '@/types'

const ROLES = [
  { value: 'sprint',  label: 'Sprint Agent'  },
  { value: 'dev',     label: 'Dev Agent'     },
  { value: 'qa',      label: 'QA Agent'      },
  { value: 'devops',  label: 'DevOps Agent'  },
  { value: 'custom',  label: 'Custom'        },
]

const MODELS = [
  { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
  { value: 'claude-opus-4-5',   label: 'Claude Opus 4.5'   },
]

export interface AgentFormData {
  name: string
  role: string
  description: string
  repo_connection_id: string
  default_branch: string
  branch_prefix: string
  llm_model: string
  max_iterations: number
  skill_ids: string[]
}

interface Props {
  initial?: Partial<Agent>
  onSave: (data: AgentFormData) => void
  loading: boolean
}

const STEPS = ['Basic Info', 'Skill Bindings', 'Repo & Config']

export function AgentWizard({ initial, onSave, loading }: Props) {
  const [step, setStep] = useState(0)

  // Step 1 fields
  const [name, setName]               = useState(initial?.name ?? '')
  const [role, setRole]               = useState(initial?.role ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')

  // Step 2 fields — ordered skill IDs
  const [skillIds, setSkillIds] = useState<string[]>(
    initial?.skills?.sort((a, b) => a.priority - b.priority).map((s) => s.skill_id) ?? []
  )

  // Step 3 fields
  const [repoConnectionId, setRepoConnectionId] = useState(initial?.repo_connection_id ?? '')
  const [defaultBranch, setDefaultBranch]       = useState(initial?.default_branch ?? 'main')
  const [branchPrefix, setBranchPrefix]         = useState(initial?.branch_prefix ?? 'agent/')
  const [llmModel, setLlmModel]                 = useState(initial?.llm_model ?? 'claude-sonnet-4-6')
  const [maxIterations, setMaxIterations]       = useState(initial?.max_iterations ?? 10)

  const { data: allSkills = [] } = useSkills()
  const { data: connections = [] } = useConnections()
  const repoConnections = connections.filter((c) => ['github', 'gitlab'].includes(c.type) && c.status === 'connected')

  // ── Step 2 helpers ──
  function toggleSkill(id: string) {
    setSkillIds((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    )
  }
  function moveUp(index: number) {
    if (index === 0) return
    setSkillIds((prev) => {
      const next = [...prev]
      ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
      return next
    })
  }
  function moveDown(index: number) {
    setSkillIds((prev) => {
      if (index === prev.length - 1) return prev
      const next = [...prev]
      ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
      return next
    })
  }

  // ── Submit ──
  function handleSave() {
    onSave({
      name,
      role,
      description,
      repo_connection_id: repoConnectionId,
      default_branch: defaultBranch,
      branch_prefix: branchPrefix,
      llm_model: llmModel,
      max_iterations: maxIterations,
      skill_ids: skillIds,
    })
  }

  const step1Valid = name.trim() && role

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
            <span className={`text-sm ${i === step ? 'font-medium' : 'text-muted-foreground'}`}>
              {label}
            </span>
            {i < STEPS.length - 1 && <div className="h-px w-8 bg-border" />}
          </div>
        ))}
      </div>

      {/* ── Step 1: Basic Info ── */}
      {step === 0 && (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Agent Name *</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Backend Dev Agent" />
          </div>

          <div className="space-y-1.5">
            <Label>Role *</Label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">-- Select role --</option>
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <Label>Description</Label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What does this agent do?" />
          </div>

          <div className="flex justify-end">
            <Button onClick={() => setStep(1)} disabled={!step1Valid}>
              Next: Skill Bindings
            </Button>
          </div>
        </div>
      )}

      {/* ── Step 2: Skill Bindings ── */}
      {step === 1 && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Select skills and order them — they're injected into the agent's context in priority order (top = first).
          </p>

          {/* Available skills */}
          <div className="space-y-1.5">
            <Label>Available Skills</Label>
            <div className="rounded-md border divide-y max-h-48 overflow-y-auto">
              {allSkills.length === 0 ? (
                <p className="p-3 text-sm text-muted-foreground">No skills created yet.</p>
              ) : (
                allSkills.map((skill) => {
                  const selected = skillIds.includes(skill.id)
                  return (
                    <button
                      key={skill.id}
                      type="button"
                      onClick={() => toggleSkill(skill.id)}
                      className={`w-full flex items-center justify-between px-3 py-2 text-sm text-left hover:bg-accent transition-colors ${selected ? 'bg-accent/50' : ''}`}
                    >
                      <span>{skill.name}</span>
                      {selected && <Check className="h-4 w-4 text-primary shrink-0" />}
                    </button>
                  )
                })
              )}
            </div>
          </div>

          {/* Selected skills (ordered) */}
          {skillIds.length > 0 && (
            <div className="space-y-1.5">
              <Label>Execution Order (drag to reorder)</Label>
              <div className="rounded-md border divide-y">
                {skillIds.map((id, index) => {
                  const skill = allSkills.find((s) => s.id === id)
                  if (!skill) return null
                  return (
                    <div key={id} className="flex items-center gap-2 px-3 py-2">
                      <span className="w-5 text-xs text-muted-foreground">{index + 1}.</span>
                      <span className="flex-1 text-sm">{skill.name}</span>
                      <div className="flex gap-1">
                        <Button type="button" variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => moveUp(index)}>
                          <ChevronUp className="h-3.5 w-3.5" />
                        </Button>
                        <Button type="button" variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => moveDown(index)}>
                          <ChevronDown className="h-3.5 w-3.5" />
                        </Button>
                        <Button type="button" variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => toggleSkill(id)}>
                          <X className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(0)}>Back</Button>
            <Button onClick={() => setStep(2)}>Next: Repo & Config</Button>
          </div>
        </div>
      )}

      {/* ── Step 3: Repo & Config ── */}
      {step === 2 && (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>GitHub / GitLab Connection</Label>
            <select
              value={repoConnectionId}
              onChange={(e) => setRepoConnectionId(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">-- None --</option>
              {repoConnections.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            {repoConnections.length === 0 && (
              <p className="text-xs text-muted-foreground">No connected GitHub/GitLab connections. Add one in Connections.</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>Default Branch</Label>
              <Input value={defaultBranch} onChange={(e) => setDefaultBranch(e.target.value)} placeholder="main" />
            </div>
            <div className="space-y-1.5">
              <Label>Branch Prefix</Label>
              <Input value={branchPrefix} onChange={(e) => setBranchPrefix(e.target.value)} placeholder="agent/" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>LLM Model</Label>
              <select
                value={llmModel}
                onChange={(e) => setLlmModel(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {MODELS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Max Iterations</Label>
              <Input
                type="number"
                min={1}
                max={50}
                value={maxIterations}
                onChange={(e) => setMaxIterations(Number(e.target.value))}
              />
            </div>
          </div>

          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
            <Button onClick={handleSave} disabled={loading}>
              {loading ? 'Saving…' : 'Save Agent'}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
