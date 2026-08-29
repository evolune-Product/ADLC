import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Play, Power, ChevronRight } from 'lucide-react'
import { toast } from 'sonner'
import {
  useWorkflow, useWorkflowExecutions, useWorkflowExecution,
  useDeactivateWorkflow, useExecuteWorkflow, useResumeExecution,
} from '@/hooks/useWorkflows'
import { getApiError } from '@/lib/api'

const STATUS_DOT: Record<string, string> = {
  pending: 'bg-muted-foreground',
  running: 'bg-blue-500',
  awaiting_approval: 'bg-[#E8632A]',
  completed: 'bg-emerald-500',
  failed: 'bg-red-500',
  cancelled: 'bg-muted-foreground',
}

export default function WorkflowDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: wf, isLoading } = useWorkflow(id)
  const { data: executions } = useWorkflowExecutions(id)
  const [selectedExecId, setSelectedExecId] = useState<string | null>(null)
  const { data: execDetail } = useWorkflowExecution(selectedExecId ?? undefined)
  const deactivate = useDeactivateWorkflow()
  const execute = useExecuteWorkflow()
  const resume = useResumeExecution()

  if (isLoading || !wf) {
    return <div className="max-w-5xl mx-auto"><div className="h-40 rounded-lg border border-border bg-card animate-pulse opacity-60" /></div>
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <button onClick={() => navigate('/workflows')} className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to Workflows
      </button>

      <div className="flex items-start justify-between">
        <div>
          <p className="onto-label mb-1">{wf.trigger_type.replace(/_/g, ' ')} · v{wf.version}</p>
          <h1 className="text-xl font-bold text-foreground tracking-tight">{wf.name}</h1>
          {wf.description && <p className="text-sm text-muted-foreground mt-1">{wf.description}</p>}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={async () => {
              try {
                const exec = await execute.mutateAsync({ id: wf.id })
                setSelectedExecId(exec.id)
                toast.success('Execution started')
              } catch (err) { toast.error(getApiError(err)) }
            }}
            disabled={!wf.is_active || execute.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-foreground text-background text-xs font-semibold rounded hover:opacity-85 transition-opacity disabled:opacity-40"
          >
            <Play className="h-3.5 w-3.5" /> Execute
          </button>
          {wf.is_active && (
            <button
              onClick={async () => {
                try { await deactivate.mutateAsync(wf.id); toast.success('Workflow deactivated') }
                catch (err) { toast.error(getApiError(err)) }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-border text-xs font-semibold rounded hover:bg-muted/40 transition-colors"
            >
              <Power className="h-3.5 w-3.5" /> Deactivate
            </button>
          )}
        </div>
      </div>

      {/* Node list — structured table, not a canvas. Per spec: a robust
          structured editor first, a visual builder only if that would not
          jeopardize stability. */}
      <div>
        <p className="text-sm font-semibold text-foreground mb-3">Nodes ({wf.definition.nodes.length})</p>
        <div className="bg-card rounded-lg border border-border overflow-hidden overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left px-4 py-2.5"><span className="onto-label">ID</span></th>
                <th className="text-left px-4 py-2.5"><span className="onto-label">Type</span></th>
                <th className="text-left px-4 py-2.5"><span className="onto-label">Config</span></th>
                <th className="text-left px-4 py-2.5"><span className="onto-label">Next</span></th>
              </tr>
            </thead>
            <tbody>
              {wf.definition.nodes.map((n, i) => (
                <tr key={n.id} className={i < wf.definition.nodes.length - 1 ? 'border-b border-border' : ''}>
                  <td className="px-4 py-3 text-xs font-mono text-foreground">
                    {n.id}
                    {n.id === wf.definition.start_node_id && <span className="ml-1.5 text-[10px] text-[#E8632A]">start</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-foreground capitalize">{n.type.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-3 text-[11px] text-muted-foreground font-mono max-w-[240px] truncate">
                    {n.config && Object.keys(n.config).length ? JSON.stringify(n.config) : '—'}
                  </td>
                  <td className="px-4 py-3 text-[11px] text-muted-foreground font-mono">
                    {typeof n.next === 'string' ? n.next
                      : Array.isArray(n.next) ? n.next.join(', ')
                      : n.next ? JSON.stringify(n.next) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Execution history */}
      <div>
        <p className="text-sm font-semibold text-foreground mb-3">Execution History</p>
        {!executions?.length ? (
          <div className="flex flex-col items-center justify-center bg-card rounded-lg border border-border border-dashed py-10">
            <p className="text-sm text-muted-foreground">No executions yet</p>
          </div>
        ) : (
          <div className="bg-card rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-2.5"><span className="onto-label">Status</span></th>
                  <th className="text-left px-4 py-2.5"><span className="onto-label">Current Node</span></th>
                  <th className="text-left px-4 py-2.5 hidden sm:table-cell"><span className="onto-label">Started</span></th>
                  <th className="px-4 py-2.5 w-8" />
                </tr>
              </thead>
              <tbody>
                {executions.map((ex, i) => (
                  <tr
                    key={ex.id}
                    onClick={() => setSelectedExecId(ex.id === selectedExecId ? null : ex.id)}
                    className={`cursor-pointer hover:bg-muted/40 transition-colors ${i < executions.length - 1 ? 'border-b border-border' : ''}`}
                  >
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS_DOT[ex.status] ?? 'bg-muted-foreground'}`} />
                        <span className="text-xs font-medium text-foreground capitalize">{ex.status.replace(/_/g, ' ')}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-muted-foreground">{ex.current_node_id ?? '—'}</td>
                    <td className="px-4 py-3 hidden sm:table-cell text-xs text-muted-foreground">{new Date(ex.started_at).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <ChevronRight className={`h-3.5 w-3.5 text-muted-foreground transition-transform ${selectedExecId === ex.id ? 'rotate-90' : ''}`} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Selected execution's step log */}
      {selectedExecId && execDetail && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold text-foreground">Steps</p>
            {(execDetail.status === 'running' || execDetail.status === 'awaiting_approval') && (
              <button
                onClick={async () => {
                  try { await resume.mutateAsync(execDetail.id); toast.success('Execution resumed') }
                  catch (err) { toast.error(getApiError(err)) }
                }}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Force resume →
              </button>
            )}
          </div>
          {execDetail.error && (
            <div className="mb-3 text-xs rounded border border-red-500/30 bg-red-500/5 text-red-500 px-3 py-2">
              {execDetail.error}
            </div>
          )}
          <div className="bg-card rounded-lg border border-border divide-y divide-border">
            {execDetail.steps.map((s) => (
              <div key={s.id} className="px-4 py-2.5">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS_DOT[s.status] ?? 'bg-muted-foreground'}`} />
                    <span className="text-xs font-mono text-foreground">{s.node_id}</span>
                    <span className="text-xs text-muted-foreground capitalize">{s.node_type.replace(/_/g, ' ')}</span>
                  </span>
                  <span className="text-[11px] text-muted-foreground">{new Date(s.started_at).toLocaleTimeString()}</span>
                </div>
                {s.error && <p className="text-[11px] text-red-500 mt-1">{s.error}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
