import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, RefreshCw, ExternalLink, Trash2, Archive } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useProject, useUpdateProject, useDeleteProject, useArchiveProject } from '@/hooks/useProjects'
import { useTickets, useSyncTickets } from '@/hooks/useTickets'
import { usePods } from '@/hooks/usePods'
import { useProjectRuns } from '@/hooks/useRuns'
import MemoryPanel from '@/components/projects/MemoryPanel'
import WritebackPanel from '@/components/projects/WritebackPanel'
import SprintPlanPanel from '@/components/projects/SprintPlanPanel'

const TABS = ['Overview', 'Sprint', 'Tickets', 'Runs', 'Settings'] as const
type Tab = typeof TABS[number]

const TYPE_LABEL: Record<string, string> = {
  backend: 'Backend', frontend: 'Frontend', fullstack: 'Fullstack',
  mobile: 'Mobile', data: 'Data', other: 'Other',
}

const PRIORITY_COLOR: Record<string, string> = {
  highest: 'text-red-600', high: 'text-orange-500',
  medium: 'text-yellow-500', low: 'text-blue-400',
}

const TYPE_COLORS: Record<string, string> = {
  bug: 'bg-red-100 text-red-700', feature: 'bg-blue-100 text-blue-700',
  task: 'bg-gray-100 text-gray-700', story: 'bg-purple-100 text-purple-700',
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<Tab>('Overview')

  const { data: project, isLoading } = useProject(id!)
  const updateMutation  = useUpdateProject(id!)
  const deleteMutation  = useDeleteProject()
  const archiveMutation = useArchiveProject()

  // Tickets tab
  const { data: tickets = [], isLoading: ticketsLoading } = useTickets(id!)
  const syncMutation = useSyncTickets(id!)

  // Runs tab
  const { data: projectRuns = [], isLoading: runsLoading } = useProjectRuns(id!)

  // Settings helpers
  const { data: pods = [] } = usePods()

  // Settings form state (lazy-init from project once loaded)
  const [settingsName, setSettingsName]           = useState('')
  const [settingsDesc, setSettingsDesc]           = useState('')
  const [settingsPodId, setSettingsPodId]         = useState('')
  const [settingsContextMd, setSettingsContextMd] = useState('')
  const [settingsInit, setSettingsInit]           = useState(false)

  if (!settingsInit && project) {
    setSettingsName(project.name)
    setSettingsDesc(project.description ?? '')
    setSettingsPodId(project.pod_id ?? '')
    setSettingsContextMd(project.context_md ?? '')
    setSettingsInit(true)
  }

  function handleSettingsSave() {
    updateMutation.mutate({
      name: settingsName,
      description: settingsDesc,
      pod_id: settingsPodId || undefined,
      context_md: settingsContextMd,
    })
  }

  function handleDelete() {
    if (!confirm('Delete this project? All tickets and runs will be removed.')) return
    deleteMutation.mutate(id!, { onSuccess: () => navigate('/projects') })
  }

  function handleArchive() {
    if (!confirm('Archive this project?')) return
    archiveMutation.mutate(id!, { onSuccess: () => navigate('/projects') })
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 rounded bg-muted animate-pulse" />
        <div className="h-48 rounded-lg border bg-muted/40 animate-pulse" />
      </div>
    )
  }

  if (!project) {
    return (
      <div>
        <p className="text-muted-foreground">Project not found.</p>
        <Button variant="link" className="px-0 mt-2" onClick={() => navigate('/projects')}>Back to Projects</Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => navigate('/projects')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-2xl font-semibold truncate">{project.name}</h1>
            {project.type && (
              <span className="rounded-full bg-secondary px-2 py-0.5 text-xs">
                {TYPE_LABEL[project.type] ?? project.type}
              </span>
            )}
            {project.status === 'archived' && (
              <span className="rounded-full bg-muted text-muted-foreground px-2 py-0.5 text-xs">Archived</span>
            )}
          </div>
          {project.description && (
            <p className="text-sm text-muted-foreground mt-0.5">{project.description}</p>
          )}
        </div>
        {project.status === 'active' && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending || !project.jira_connection_id}
            title={!project.jira_connection_id ? 'No Jira connection configured' : undefined}
          >
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
            Sync Tickets
          </Button>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b flex gap-0">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* ── Overview ── */}
      {activeTab === 'Overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Tickets',        value: tickets.length },
              { label: 'Active Runs',    value: projectRuns.filter((r) => ['queued','running'].includes(r.status)).length },
              { label: 'Deploy Targets', value: project.deploy_targets?.length ?? 0 },
              { label: 'Pod',            value: project.pod_name ?? '—' },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg border p-4">
                <p className="text-sm text-muted-foreground">{label}</p>
                <p className="text-2xl font-semibold mt-1 truncate">{value}</p>
              </div>
            ))}
          </div>

          <div className="rounded-lg border divide-y">
            {[
              { label: 'Repository',   value: project.repo_name },
              { label: 'Jira Project', value: project.jira_project_key },
              { label: 'Pod',          value: project.pod_name },
              { label: 'Status',       value: project.status },
              { label: 'Created',      value: new Date(project.created_at).toLocaleDateString() },
            ].map(({ label, value }) => value && (
              <div key={label} className="flex items-center justify-between px-4 py-3 text-sm">
                <span className="text-muted-foreground">{label}</span>
                <span className="font-medium">{value}</span>
              </div>
            ))}
          </div>

          {(project.deploy_targets ?? []).length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Deploy Targets</p>
              <div className="flex gap-2 flex-wrap">
                {project.deploy_targets.map((dt: { env: string; branch: string }) => (
                  <div key={dt.env} className="rounded-md border px-3 py-1.5 text-sm">
                    <span className="font-medium">{dt.env}</span>
                    <span className="text-muted-foreground"> → {dt.branch}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* What the agents know about this codebase */}
          <MemoryPanel projectId={project.id} />

          {/* …and what they tell the tracker back */}
          <WritebackPanel project={project} />
        </div>
      )}

      {/* ── Sprint ── */}
      {activeTab === 'Sprint' && (
        <SprintPlanPanel projectId={project.id} writebackEnabled={!!project.writeback?.enabled} />
      )}

      {/* ── Tickets ── */}
      {activeTab === 'Tickets' && (
        <div className="space-y-4">
          {ticketsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <div key={i} className="h-14 rounded-lg border bg-muted/40 animate-pulse" />)}
            </div>
          ) : tickets.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-12 gap-2">
              <p className="font-medium text-sm">No tickets yet</p>
              <p className="text-sm text-muted-foreground">
                {project.jira_connection_id
                  ? 'Click "Sync Tickets" to fetch from Jira.'
                  : 'Configure a Jira connection in Settings to sync tickets.'}
              </p>
              {project.jira_connection_id && (
                <Button variant="outline" size="sm" onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}>
                  <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
                  Sync Now
                </Button>
              )}
            </div>
          ) : (
            <div className="rounded-lg border divide-y">
              {tickets.map((ticket) => (
                <div
                  key={ticket.id}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-accent/50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/projects/${id}/tickets/${ticket.id}`)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-mono text-muted-foreground shrink-0">{ticket.jira_id}</span>
                      {ticket.type && (
                        <span className={`rounded px-1.5 py-0.5 text-xs ${TYPE_COLORS[ticket.type] ?? 'bg-secondary text-secondary-foreground'}`}>
                          {ticket.type}
                        </span>
                      )}
                      <span className="text-sm font-medium truncate">{ticket.title}</span>
                    </div>
                    {ticket.status && (
                      <p className="text-xs text-muted-foreground mt-0.5">{ticket.status}{ticket.assignee ? ` · ${ticket.assignee}` : ''}</p>
                    )}
                  </div>
                  {ticket.priority && (
                    <span className={`text-xs font-medium shrink-0 ${PRIORITY_COLOR[ticket.priority] ?? ''}`}>
                      {ticket.priority}
                    </span>
                  )}
                  {ticket.jira_url && (
                    <a
                      href={ticket.jira_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-muted-foreground hover:text-foreground shrink-0"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Runs ── */}
      {activeTab === 'Runs' && (
        <div className="space-y-3">
          {runsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <div key={i} className="h-14 rounded-lg border bg-muted/40 animate-pulse" />)}
            </div>
          ) : projectRuns.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-14 gap-2">
              <p className="font-medium text-sm">No runs yet</p>
              <p className="text-sm text-muted-foreground">Open a ticket and click "Run with Pod" to start.</p>
            </div>
          ) : (
            <div className="rounded-lg border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/30">
                  <tr>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Status</th>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Current Step</th>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Branch</th>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Started</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {projectRuns.map((run) => (
                    <tr
                      key={run.id}
                      className="hover:bg-accent/50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/runs/${run.id}`)}
                    >
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          {
                            queued:            'bg-gray-100 text-gray-600',
                            running:           'bg-blue-100 text-blue-700',
                            awaiting_approval: 'bg-yellow-100 text-yellow-700',
                            approved:          'bg-green-100 text-green-700',
                            completed:         'bg-green-100 text-green-700',
                            failed:            'bg-red-100 text-red-700',
                          }[run.status] ?? 'bg-secondary'
                        }`}>
                          {run.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground truncate max-w-[160px]">
                        {run.current_step ?? '—'}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs truncate max-w-[140px]">
                        {run.branch_name ?? '—'}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {run.started_at ? new Date(run.started_at).toLocaleString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Settings ── */}
      {activeTab === 'Settings' && (
        <div className="space-y-6 max-w-lg">
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>Project Name</Label>
              <Input value={settingsName} onChange={(e) => setSettingsName(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Description</Label>
              <Input value={settingsDesc} onChange={(e) => setSettingsDesc(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Pod</Label>
              <select
                value={settingsPodId}
                onChange={(e) => setSettingsPodId(e.target.value)}
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">No pod assigned</option>
                {pods.filter((p) => p.is_active).map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Project Context</Label>
              <textarea
                value={settingsContextMd}
                onChange={(e) => setSettingsContextMd(e.target.value)}
                rows={6}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none font-mono"
              />
            </div>
            <Button onClick={handleSettingsSave} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? 'Saving…' : 'Save Changes'}
            </Button>
          </div>

          {/* Danger zone */}
          <div className="rounded-lg border border-destructive/30 p-4 space-y-3">
            <p className="text-sm font-medium text-destructive">Danger Zone</p>
            <div className="flex gap-2">
              {project.status === 'active' && (
                <Button
                  variant="outline"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                  onClick={handleArchive}
                  disabled={archiveMutation.isPending}
                >
                  <Archive className="h-3.5 w-3.5 mr-1.5" /> Archive Project
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
              >
                <Trash2 className="h-3.5 w-3.5 mr-1.5" /> Delete Project
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
