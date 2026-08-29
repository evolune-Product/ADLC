import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Check, ExternalLink, Loader2, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useCloseTicket, useTicket } from '@/hooks/useTickets'
import { useProject } from '@/hooks/useProjects'
import { useCreateRun } from '@/hooks/useRuns'

const PRIORITY_COLOR: Record<string, string> = {
  highest: 'bg-red-100 text-red-700',
  high:    'bg-orange-100 text-orange-700',
  medium:  'bg-yellow-100 text-yellow-700',
  low:     'bg-blue-100 text-blue-700',
}

const TYPE_COLORS: Record<string, string> = {
  bug:     'bg-red-100 text-red-700',
  feature: 'bg-blue-100 text-blue-700',
  task:    'bg-muted text-muted-foreground',
  story:   'bg-purple-100 text-purple-700',
}

export default function TicketDetailPage() {
  const { id, ticketId } = useParams<{ id: string; ticketId: string }>()
  const navigate = useNavigate()

  const { data: project } = useProject(id!)
  const { data: ticket, isLoading } = useTicket(id!, ticketId!)
  const createRun = useCreateRun()
  const closeTicket = useCloseTicket(id!)

  function handleRun() {
    if (!project?.pod_id) return
    createRun.mutate(
      { project_id: project.id, ticket_id: ticket?.id, pod_id: project.pod_id },
      { onSuccess: (run) => navigate(`/runs/${run.id}`) },
    )
  }

  function handleClose() {
    if (!ticket) return
    if (!window.confirm(`Mark ${ticket.jira_id} as Done? This posts a comment and moves the ticket in your issue tracker.`)) {
      return
    }
    closeTicket.mutate({ ticketId: ticket.id })
  }

  const isClosed = (ticket?.status || '').toLowerCase() === 'done'

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="h-8 w-48 rounded bg-muted animate-pulse" />
        <div className="h-48 rounded-lg border bg-muted/40 animate-pulse" />
      </div>
    )
  }

  if (!ticket) {
    return (
      <div className="max-w-2xl mx-auto">
        <p className="text-muted-foreground">Ticket not found.</p>
        <Button variant="link" className="px-0 mt-2" onClick={() => navigate(`/projects/${id}`)}>
          Back to Project
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => navigate(`/projects/${id}`)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-mono text-muted-foreground shrink-0">{ticket.jira_id}</span>
            {ticket.type && (
              <span className={`rounded px-1.5 py-0.5 text-xs ${TYPE_COLORS[ticket.type] ?? 'bg-secondary'}`}>
                {ticket.type}
              </span>
            )}
            {ticket.priority && (
              <span className={`rounded px-1.5 py-0.5 text-xs ${PRIORITY_COLOR[ticket.priority] ?? 'bg-secondary'}`}>
                {ticket.priority}
              </span>
            )}
          </div>
          <h1 className="text-xl font-semibold mt-1">{ticket.title}</h1>
        </div>
      </div>

      {/* Meta */}
      <div className="rounded-lg border divide-y">
        {[
          { label: 'Status',   value: ticket.status },
          { label: 'Assignee', value: ticket.assignee },
          { label: 'Project',  value: project?.name },
          { label: 'Synced',   value: new Date(ticket.synced_at).toLocaleString() },
        ].map(({ label, value }) => value && (
          <div key={label} className="flex items-center justify-between px-4 py-3 text-sm">
            <span className="text-muted-foreground">{label}</span>
            <span className="font-medium">{value}</span>
          </div>
        ))}
      </div>

      {/* Description */}
      {ticket.description && (
        <div className="space-y-2">
          <p className="text-sm font-medium">Description</p>
          <div className="rounded-lg border p-4 text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
            {ticket.description}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <Button
          onClick={handleRun}
          disabled={!project?.pod_id || createRun.isPending}
          title={!project?.pod_id ? 'This project has no pod assigned' : undefined}
        >
          {createRun.isPending
            ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Starting…</>
            : <><Play className="h-4 w-4 mr-2" /> Run with Pod</>
          }
        </Button>
        {ticket.jira_url && (
          <Button variant="outline" asChild>
            <a href={ticket.jira_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4 mr-2" />
              Open in Jira
            </a>
          </Button>
        )}
        <Button
          variant="outline"
          onClick={handleClose}
          disabled={isClosed || closeTicket.isPending}
          title={isClosed ? 'Already marked Done' : 'Confirm the work is complete and close this ticket'}
        >
          {closeTicket.isPending
            ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Closing…</>
            : <><Check className="h-4 w-4 mr-2" /> {isClosed ? 'Closed' : 'Mark as Done'}</>
          }
        </Button>
      </div>
    </div>
  )
}
