import { useState } from 'react'
import { Download, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuditLogs, auditExportUrl } from '@/hooks/useAudit'

const ENTITY_TYPES = ['run', 'project', 'ticket', 'agent', 'pod', 'skill', 'connection', 'settings', 'user']

const ENTITY_COLOR: Record<string, string> = {
  run:        'bg-blue-100 text-blue-700',
  project:    'bg-purple-100 text-purple-700',
  ticket:     'bg-yellow-100 text-yellow-700',
  agent:      'bg-green-100 text-green-700',
  pod:        'bg-indigo-100 text-indigo-700',
  skill:      'bg-pink-100 text-pink-700',
  connection: 'bg-orange-100 text-orange-700',
  settings:   'bg-muted text-muted-foreground',
  user:       'bg-teal-100 text-teal-700',
}

const PAGE_SIZE = 50

export default function AuditPage() {
  const [actionFilter, setActionFilter]     = useState('')
  const [entityFilter, setEntityFilter]     = useState('')
  const [page, setPage]                     = useState(0)
  const [inputValue, setInputValue]         = useState('')

  const { data, isLoading } = useAuditLogs({
    action:      actionFilter || undefined,
    entity_type: entityFilter || undefined,
    skip:        page * PAGE_SIZE,
    limit:       PAGE_SIZE,
  })

  function applySearch() {
    setActionFilter(inputValue.trim())
    setPage(0)
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Audit Log</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Full trail of all platform actions.
            {data ? ` ${data.total.toLocaleString()} total entries.` : ''}
          </p>
        </div>
        <a
          href={auditExportUrl({ action: actionFilter || undefined, entity_type: entityFilter || undefined })}
          download
        >
          <Button variant="outline" size="sm">
            <Download className="h-3.5 w-3.5 mr-1.5" />
            Export CSV
          </Button>
        </a>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        <div className="flex gap-2 flex-1 min-w-[200px]">
          <Input
            placeholder="Filter by action…"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && applySearch()}
            className="h-8 text-sm"
          />
          <Button size="sm" variant="secondary" className="h-8" onClick={applySearch}>
            <Search className="h-3.5 w-3.5" />
          </Button>
        </div>

        <div className="flex gap-1 flex-wrap">
          <button
            onClick={() => { setEntityFilter(''); setPage(0) }}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              entityFilter === '' ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
            }`}
          >
            All
          </button>
          {ENTITY_TYPES.map((et) => (
            <button
              key={et}
              onClick={() => { setEntityFilter(et); setPage(0) }}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                entityFilter === et ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
              }`}
            >
              {et}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 rounded-lg border bg-muted/40 animate-pulse" />
          ))}
        </div>
      ) : !data?.items.length ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-14 gap-2">
          <p className="text-sm font-medium">No audit entries found</p>
          <p className="text-sm text-muted-foreground">Perform actions in the platform to see them here.</p>
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/30">
              <tr>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Timestamp</th>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Action</th>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Entity</th>
                <th className="text-left px-4 py-2 font-medium text-muted-foreground">Entity ID</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.items.map((log) => (
                <tr key={log.id} className="hover:bg-accent/30 transition-colors">
                  <td className="px-4 py-2.5 text-muted-foreground whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs">{log.action}</td>
                  <td className="px-4 py-2.5">
                    {log.entity_type ? (
                      <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${ENTITY_COLOR[log.entity_type] ?? 'bg-secondary text-secondary-foreground'}`}>
                        {log.entity_type}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground truncate max-w-[180px]">
                    {log.entity_id ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
