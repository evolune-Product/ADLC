import { useState } from 'react'
import { toast } from 'sonner'
import { ArrowLeftRight, Info } from 'lucide-react'
import { useUpdateProject } from '@/hooks/useProjects'
import { getApiError } from '@/lib/api'
import type { Project } from '@/types'

/**
 * Ticket write-back configuration.
 *
 * Off by default and it stays that way until someone turns it on — moving
 * another team's tickets between columns unasked is how an integration gets
 * disconnected. The comments are the part that is always safe, so the copy
 * leads with them: turning this on means the ticket gets *narrated*, and
 * optionally moved.
 *
 * Status names are free text rather than a dropdown because there is nothing
 * to populate a dropdown from until we have called the tracker, and every team
 * renames its columns. A name that does not match any available transition is
 * a no-op on the server, not an error.
 */

const MILESTONES: Array<{ key: string; label: string; hint: string }> = [
  { key: 'running', label: 'Run started', hint: 'Agents have picked the ticket up' },
  { key: 'awaiting_approval', label: 'Waiting for approval', hint: 'PR is open, a human must decide' },
  { key: 'completed', label: 'Deployed to the last environment', hint: 'Shipped' },
  { key: 'failed', label: 'Run failed', hint: 'Leave blank — a failed run is not a ticket state' },
]

const DEFAULTS: Record<string, string> = {
  running: 'In Progress',
  awaiting_approval: 'In Review',
  completed: 'Done',
  failed: '',
}

export default function WritebackPanel({ project }: { project: Project }) {
  const update = useUpdateProject(project.id)
  const config = project.writeback ?? {}

  const [enabled, setEnabled] = useState(!!config.enabled)
  const [map, setMap] = useState<Record<string, string>>({
    ...DEFAULTS,
    ...(config.status_map ?? {}),
  })

  // Nothing to write back to without a ticket connection.
  if (!project.jira_connection_id) return null

  async function save() {
    try {
      await update.mutateAsync({ writeback: { enabled, status_map: map } })
      toast.success(enabled ? 'Write-back enabled' : 'Write-back turned off')
    } catch (e) {
      toast.error(getApiError(e, 'Could not save'))
    }
  }

  return (
    <div className="bg-card rounded-lg border border-border p-5 space-y-4">
      <div className="flex items-center gap-2">
        <ArrowLeftRight className="h-4 w-4" />
        <p className="font-medium">Ticket write-back</p>
      </div>

      <p className="text-sm text-muted-foreground">
        Tickets already sync in. This sends progress back out: a comment on the ticket when the run
        starts, when a pull request is waiting for approval, when it deploys, and if it fails —
        each with the link that makes it actionable. Anyone watching the tracker instead of this
        dashboard sees the work happen.
      </p>

      <label className="flex items-start gap-2.5 rounded-lg border border-border p-3">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          className="mt-0.5"
        />
        <span>
          <span className="text-sm font-medium">Comment on the ticket at each milestone</span>
          <span className="mt-0.5 block text-xs text-muted-foreground">
            A tracker that is unreachable, or a workflow with no matching column, is logged and
            ignored — write-back can never fail a run or block a deploy.
          </span>
        </span>
      </label>

      {enabled && (
        <div className="space-y-3">
          <div className="flex items-start gap-2 text-xs text-muted-foreground">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              Optionally move the ticket too. Type the status name exactly as it appears in your
              workflow; leave a row blank to leave the ticket where it is at that milestone.
            </span>
          </div>

          <div className="divide-y divide-border rounded-md border border-border">
            {MILESTONES.map((m) => (
              <div key={m.key} className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1">
                  <p className="text-sm">{m.label}</p>
                  <p className="text-xs text-muted-foreground">{m.hint}</p>
                </div>
                <input
                  value={map[m.key] ?? ''}
                  onChange={(e) => setMap((s) => ({ ...s, [m.key]: e.target.value }))}
                  placeholder="Leave blank — do not move"
                  className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm sm:w-56"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={save}
        disabled={update.isPending}
        className="rounded bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:opacity-50"
      >
        {update.isPending ? 'Saving…' : 'Save'}
      </button>
    </div>
  )
}
