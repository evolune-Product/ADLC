import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { useCreateWorkflow, type WorkflowNode } from '@/hooks/useWorkflows'
import { getApiError } from '@/lib/api'

const NODE_TYPES = [
  'trigger', 'human_task', 'agent_task', 'api_call', 'condition',
  'approval', 'notification', 'webhook', 'transform', 'delay',
  'sub_workflow', 'completion',
]

interface DraftNode extends WorkflowNode {
  configText: string
  nextText: string
}

function emptyNode(id: string): DraftNode {
  return { id, type: 'trigger', configText: '{}', nextText: '' }
}

export default function NewWorkflowPage() {
  const navigate = useNavigate()
  const createWorkflow = useCreateWorkflow()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [triggerType, setTriggerType] = useState('manual')
  const [nodes, setNodes] = useState<DraftNode[]>([emptyNode('n1')])
  const [startNodeId, setStartNodeId] = useState('n1')
  const [error, setError] = useState<string | null>(null)

  function updateNode(idx: number, patch: Partial<DraftNode>) {
    setNodes((prev) => prev.map((n, i) => (i === idx ? { ...n, ...patch } : n)))
  }

  function addNode() {
    setNodes((prev) => [...prev, emptyNode(`n${prev.length + 1}`)])
  }

  function removeNode(idx: number) {
    setNodes((prev) => prev.filter((_, i) => i !== idx))
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!name.trim()) { setError('Name is required'); return }

    let parsedNodes: WorkflowNode[]
    try {
      parsedNodes = nodes.map((n) => {
        const config = n.configText.trim() ? JSON.parse(n.configText) : {}
        let next: WorkflowNode['next'] | undefined
        const nt = n.nextText.trim()
        if (nt) {
          // A bare node id, a comma list, or JSON for a branch spec.
          if (nt.startsWith('{')) next = JSON.parse(nt)
          else if (nt.includes(',')) next = nt.split(',').map((s) => s.trim())
          else next = nt
        }
        return { id: n.id.trim(), type: n.type, config, next }
      })
    } catch {
      setError('One of the node "config" or "next" fields is not valid JSON')
      return
    }

    if (parsedNodes.some((n) => !n.id)) { setError('Every node needs an id'); return }
    if (!parsedNodes.some((n) => n.id === startNodeId)) { setError('start_node_id must match one of the node ids'); return }

    try {
      const wf = await createWorkflow.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        trigger_type: triggerType,
        definition: { start_node_id: startNodeId, nodes: parsedNodes },
        is_active: true,
      })
      toast.success('Workflow created')
      navigate(`/workflows/${wf.id}`)
    } catch (err) {
      toast.error(getApiError(err))
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button onClick={() => navigate('/workflows')} className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to Workflows
      </button>

      <div>
        <p className="onto-label mb-1">Automation</p>
        <h1 className="text-xl font-bold text-foreground tracking-tight">New Workflow</h1>
        <p className="text-xs text-muted-foreground mt-1">
          A structured node list, not a drag-and-drop canvas — add nodes one at a time, configure them, and link to the next node id(s).
        </p>
      </div>

      <form onSubmit={submit} className="space-y-6">
        <div className="bg-card rounded-lg border border-border p-4 space-y-3">
          <div>
            <label className="onto-label block mb-1.5">Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)}
                   className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-foreground/20" />
          </div>
          <div>
            <label className="onto-label block mb-1.5">Description</label>
            <input value={description} onChange={(e) => setDescription(e.target.value)}
                   className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-foreground/20" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="onto-label block mb-1.5">Trigger Type</label>
              <select value={triggerType} onChange={(e) => setTriggerType(e.target.value)}
                      className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-foreground/20">
                <option value="manual">manual</option>
                <option value="work_created">work_created</option>
              </select>
            </div>
            <div>
              <label className="onto-label block mb-1.5">Start Node ID</label>
              <input value={startNodeId} onChange={(e) => setStartNodeId(e.target.value)}
                     className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-foreground/20" />
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-foreground">Nodes</p>
            <button type="button" onClick={addNode}
                    className="flex items-center gap-1.5 px-2.5 py-1 border border-border text-xs font-semibold rounded hover:bg-muted/40 transition-colors">
              <Plus className="h-3.5 w-3.5" /> Add Node
            </button>
          </div>

          {nodes.map((n, idx) => (
            <div key={idx} className="bg-card rounded-lg border border-border p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="onto-label">Node {idx + 1}</span>
                {nodes.length > 1 && (
                  <button type="button" onClick={() => removeNode(idx)} className="text-muted-foreground hover:text-red-500 transition-colors">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="onto-label block mb-1.5">ID</label>
                  <input value={n.id} onChange={(e) => updateNode(idx, { id: e.target.value })}
                         className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-foreground/20" />
                </div>
                <div>
                  <label className="onto-label block mb-1.5">Type</label>
                  <select value={n.type} onChange={(e) => updateNode(idx, { type: e.target.value })}
                          className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-foreground/20">
                    {NODE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="onto-label block mb-1.5">Config (JSON)</label>
                <textarea value={n.configText} onChange={(e) => updateNode(idx, { configText: e.target.value })}
                          rows={2}
                          className="w-full bg-background border border-border rounded px-3 py-2 text-xs font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-foreground/20 resize-none" />
              </div>
              <div>
                <label className="onto-label block mb-1.5">Next (node id, comma list, or {'{'}"field","branches"{'}'} JSON)</label>
                <input value={n.nextText} onChange={(e) => updateNode(idx, { nextText: e.target.value })}
                       placeholder="n2"
                       className="w-full bg-background border border-border rounded px-3 py-2 text-xs font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-foreground/20" />
              </div>
            </div>
          ))}
        </div>

        {error && <div className="text-xs rounded border border-red-500/30 bg-red-500/5 text-red-500 px-3 py-2">{error}</div>}

        <button type="submit" disabled={createWorkflow.isPending}
                className="flex items-center gap-1.5 px-4 py-2 bg-foreground text-background text-xs font-semibold rounded hover:opacity-85 transition-opacity disabled:opacity-40">
          {createWorkflow.isPending ? 'Creating…' : 'Create Workflow'}
        </button>
      </form>
    </div>
  )
}
