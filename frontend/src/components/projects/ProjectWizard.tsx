import { useState } from 'react'
import { Check, Plus, X, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useConnections } from '@/hooks/useConnections'
import { usePods } from '@/hooks/usePods'
import {
  useConnectionRepos,
  useConnectionJiraProjects,
  type ProjectFormData,
  type DeployTargetInput,
} from '@/hooks/useProjects'
import type { Project } from '@/types'

const STEPS = ['Project Info', 'Source Control', 'Issue Tracker', 'Pod & Context']

const PROJECT_TYPES = [
  { value: 'backend', label: 'Backend' },
  { value: 'frontend', label: 'Frontend' },
  { value: 'fullstack', label: 'Fullstack' },
  { value: 'mobile', label: 'Mobile' },
  { value: 'data', label: 'Data' },
  { value: 'other', label: 'Other' },
]

interface Props {
  initial?: Partial<Project>
  onSave: (data: ProjectFormData) => void
  loading: boolean
}

export function ProjectWizard({ initial, onSave, loading }: Props) {
  const [step, setStep] = useState(0)

  // Step 1
  const [name, setName]               = useState(initial?.name ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [type, setType]               = useState(initial?.type ?? '')

  // Step 2
  const [repoConnectionId, setRepoConnectionId] = useState<string>(initial?.repo_connection_id ?? '')
  const [repoName, setRepoName]                 = useState(initial?.repo_name ?? '')
  const [deployTargets, setDeployTargets]       = useState<DeployTargetInput[]>(
    (initial?.deploy_targets as DeployTargetInput[]) ?? []
  )

  // Step 3
  const [jiraConnectionId, setJiraConnectionId] = useState<string>(initial?.jira_connection_id ?? '')
  const [jiraProjectKey, setJiraProjectKey]     = useState(initial?.jira_project_key ?? '')

  // Step 4
  const [podId, setPodId]           = useState(initial?.pod_id ?? '')
  const [contextMd, setContextMd]   = useState(initial?.context_md ?? '')

  // Data
  const { data: connections = [] } = useConnections()
  const { data: pods = [] }        = usePods()

  const repoConnections  = connections.filter((c) => ['github', 'gitlab'].includes(c.type) && c.status === 'connected')
  const jiraConnections  = connections.filter((c) => c.type === 'jira' && c.status === 'connected')

  const { data: repos = [], isFetching: fetchingRepos }               = useConnectionRepos(repoConnectionId || null)
  const { data: jiraProjects = [], isFetching: fetchingJiraProjects } = useConnectionJiraProjects(jiraConnectionId || null)

  // Deploy targets helpers
  function addDeployTarget() {
    setDeployTargets((prev) => [...prev, { env: '', branch: '' }])
  }
  function updateDeployTarget(i: number, field: 'env' | 'branch', value: string) {
    setDeployTargets((prev) => prev.map((dt, idx) => idx === i ? { ...dt, [field]: value } : dt))
  }
  function removeDeployTarget(i: number) {
    setDeployTargets((prev) => prev.filter((_, idx) => idx !== i))
  }

  function handleSave() {
    onSave({
      name,
      description: description || undefined,
      type: type || undefined,
      repo_connection_id: repoConnectionId || null,
      repo_name: repoName || null,
      jira_connection_id: jiraConnectionId || null,
      jira_project_key: jiraProjectKey || null,
      pod_id: podId || null,
      context_md: contextMd || undefined,
      deploy_targets: deployTargets.filter((dt) => dt.env && dt.branch),
    })
  }

  return (
    <div className="space-y-6">
      {/* Step indicator */}
      <div className="flex items-center gap-2 flex-wrap">
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
            {i < STEPS.length - 1 && <div className="h-px w-6 bg-border" />}
          </div>
        ))}
      </div>

      {/* ── Step 1: Project Info ── */}
      {step === 0 && (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Project Name *</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Customer Portal" />
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What does this project do?" />
          </div>
          <div className="space-y-1.5">
            <Label>Project Type</Label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Select type…</option>
              {PROJECT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div className="flex justify-end">
            <Button onClick={() => setStep(1)} disabled={!name.trim()}>Next: Source Control</Button>
          </div>
        </div>
      )}

      {/* ── Step 2: Source Control ── */}
      {step === 1 && (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Repository Connection</Label>
            {repoConnections.length === 0 ? (
              <p className="text-sm text-muted-foreground">No GitHub/GitLab connections found. You can skip this step.</p>
            ) : (
              <select
                value={repoConnectionId}
                onChange={(e) => { setRepoConnectionId(e.target.value); setRepoName('') }}
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">Select connection…</option>
                {repoConnections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            )}
          </div>

          {repoConnectionId && (
            <div className="space-y-1.5">
              <Label>Repository</Label>
              {fetchingRepos ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Fetching repos…
                </div>
              ) : (
                <select
                  value={repoName}
                  onChange={(e) => setRepoName(e.target.value)}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">Select repository…</option>
                  {repos.map((r) => <option key={r.full_name} value={r.full_name}>{r.full_name}</option>)}
                </select>
              )}
            </div>
          )}

          {/* Deploy targets */}
          <div className="space-y-2">
            <Label>Deploy Targets (optional)</Label>
            {deployTargets.map((dt, i) => (
              <div key={i} className="flex items-center gap-2">
                <Input
                  placeholder="env (e.g. dev)"
                  value={dt.env}
                  onChange={(e) => updateDeployTarget(i, 'env', e.target.value)}
                  className="w-28"
                />
                <Input
                  placeholder="branch (e.g. develop)"
                  value={dt.branch}
                  onChange={(e) => updateDeployTarget(i, 'branch', e.target.value)}
                  className="flex-1"
                />
                <Button type="button" variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => removeDeployTarget(i)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button type="button" variant="outline" size="sm" onClick={addDeployTarget}>
              <Plus className="h-3.5 w-3.5 mr-1" /> Add Environment
            </Button>
          </div>

          <div className="flex justify-between pt-2">
            <Button variant="outline" onClick={() => setStep(0)}>Back</Button>
            <Button onClick={() => setStep(2)}>Next: Issue Tracker</Button>
          </div>
        </div>
      )}

      {/* ── Step 3: Issue Tracker ── */}
      {step === 2 && (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Jira Connection</Label>
            {jiraConnections.length === 0 ? (
              <p className="text-sm text-muted-foreground">No Jira connections found. You can skip this step.</p>
            ) : (
              <select
                value={jiraConnectionId}
                onChange={(e) => { setJiraConnectionId(e.target.value); setJiraProjectKey('') }}
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">Select connection…</option>
                {jiraConnections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            )}
          </div>

          {jiraConnectionId && (
            <div className="space-y-1.5">
              <Label>Jira Project</Label>
              {fetchingJiraProjects ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Fetching projects…
                </div>
              ) : (
                <select
                  value={jiraProjectKey}
                  onChange={(e) => setJiraProjectKey(e.target.value)}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">Select project…</option>
                  {jiraProjects.map((p) => (
                    <option key={p.key} value={p.key}>{p.key} — {p.name}</option>
                  ))}
                </select>
              )}
            </div>
          )}

          <div className="flex justify-between pt-2">
            <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
            <Button onClick={() => setStep(3)}>Next: Pod & Context</Button>
          </div>
        </div>
      )}

      {/* ── Step 4: Pod + Context ── */}
      {step === 3 && (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Pod *</Label>
            {pods.length === 0 ? (
              <p className="text-sm text-muted-foreground">No pods yet. Create a pod first in the Pods section.</p>
            ) : (
              <select
                value={podId}
                onChange={(e) => setPodId(e.target.value)}
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">Select pod…</option>
                {pods.filter((p) => p.is_active).map((p) => (
                  <option key={p.id} value={p.id}>{p.name} ({p.agents.length} agent{p.agents.length !== 1 ? 's' : ''})</option>
                ))}
              </select>
            )}
          </div>

          <div className="space-y-1.5">
            <Label>Project Context</Label>
            <p className="text-xs text-muted-foreground">Describe the codebase conventions, architecture and stack so agents have context.</p>
            <textarea
              value={contextMd}
              onChange={(e) => setContextMd(e.target.value)}
              placeholder="## Stack&#10;- Node.js + Express&#10;&#10;## Conventions&#10;- Use camelCase for variables"
              rows={8}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none font-mono"
            />
          </div>

          {/* Summary */}
          <div className="rounded-lg border bg-muted/30 p-4 space-y-2 text-sm">
            <p className="font-medium">Summary</p>
            <div className="space-y-1 text-muted-foreground">
              <p><span className="text-foreground font-medium">Name:</span> {name}</p>
              {type && <p><span className="text-foreground font-medium">Type:</span> {type}</p>}
              {repoName && <p><span className="text-foreground font-medium">Repo:</span> {repoName}</p>}
              {deployTargets.filter((d) => d.env).length > 0 && (
                <p><span className="text-foreground font-medium">Envs:</span> {deployTargets.filter((d) => d.env).map((d) => `${d.env}→${d.branch}`).join(', ')}</p>
              )}
              {jiraProjectKey && <p><span className="text-foreground font-medium">Jira:</span> {jiraProjectKey}</p>}
              {podId && <p><span className="text-foreground font-medium">Pod:</span> {pods.find((p) => p.id === podId)?.name}</p>}
            </div>
          </div>

          <div className="flex justify-between pt-2">
            <Button variant="outline" onClick={() => setStep(2)}>Back</Button>
            <Button onClick={handleSave} disabled={loading || !podId}>
              {loading ? 'Creating…' : 'Create Project'}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
