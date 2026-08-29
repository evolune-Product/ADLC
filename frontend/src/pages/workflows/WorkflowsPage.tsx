import { useNavigate } from 'react-router-dom'
import { Plus, GitBranch } from 'lucide-react'
import { useWorkflows } from '@/hooks/useWorkflows'

export default function WorkflowsPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useWorkflows()

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="onto-label mb-1">Automation</p>
          <h1 className="text-xl font-bold text-foreground tracking-tight">Workflows</h1>
        </div>
        <button
          onClick={() => navigate('/workflows/new')}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-foreground text-background text-xs font-semibold rounded hover:opacity-85 transition-opacity"
        >
          <Plus className="h-3.5 w-3.5" />
          New Workflow
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 rounded-lg border border-border bg-card animate-pulse opacity-60" />
          ))}
        </div>
      ) : !data?.length ? (
        <div className="flex flex-col items-center justify-center bg-card rounded-lg border border-border border-dashed py-16 gap-2">
          <GitBranch className="h-6 w-6 text-muted-foreground" />
          <p className="text-sm font-medium text-foreground">No workflows yet</p>
          <p className="text-xs text-muted-foreground">Build one from a structured node list — no canvas needed.</p>
        </div>
      ) : (
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left px-4 py-2.5"><span className="onto-label">Name</span></th>
                <th className="text-left px-4 py-2.5 hidden sm:table-cell"><span className="onto-label">Trigger</span></th>
                <th className="text-left px-4 py-2.5"><span className="onto-label">Status</span></th>
                <th className="text-left px-4 py-2.5 hidden md:table-cell"><span className="onto-label">Nodes</span></th>
                <th className="text-left px-4 py-2.5 hidden lg:table-cell"><span className="onto-label">Version</span></th>
              </tr>
            </thead>
            <tbody>
              {data.map((wf, i) => (
                <tr
                  key={wf.id}
                  onClick={() => navigate(`/workflows/${wf.id}`)}
                  className={`cursor-pointer hover:bg-muted/40 transition-colors ${i < data.length - 1 ? 'border-b border-border' : ''}`}
                >
                  <td className="px-4 py-3">
                    <p className="text-xs font-medium text-foreground">{wf.name}</p>
                    {wf.description && <p className="text-[11px] text-muted-foreground truncate max-w-[280px]">{wf.description}</p>}
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell text-xs text-muted-foreground capitalize">{wf.trigger_type.replace(/_/g, ' ')}</td>
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${wf.is_active ? 'bg-emerald-500' : 'bg-muted-foreground'}`} />
                      <span className="text-xs font-medium text-foreground">{wf.is_active ? 'Active' : 'Inactive'}</span>
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell text-xs text-muted-foreground">{wf.definition?.nodes?.length ?? 0}</td>
                  <td className="px-4 py-3 hidden lg:table-cell text-xs text-muted-foreground">v{wf.version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
