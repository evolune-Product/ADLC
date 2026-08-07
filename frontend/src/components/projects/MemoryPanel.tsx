import { useState } from 'react'
import { Brain, Plus, RefreshCw, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  useAddMemoryNote, useIndexMemory, useMemoryStatus, useSearchMemory,
} from '@/hooks/usePlatform'
import type { MemoryHit } from '@/types/platform'

const STATUS_DOT: Record<string, string> = {
  ready: 'bg-emerald-600',
  indexing: 'bg-[#E8632A] animate-pulse',
  failed: 'bg-red-600',
  pending: 'bg-muted-foreground',
}

/**
 * "What do the agents know about this codebase?"
 *
 * Memory a lead cannot inspect is memory they will not trust on a production
 * repo, so retrieval here runs the exact query path a run uses — no separate
 * ranking, no curated view.
 */
export default function MemoryPanel({ projectId }: { projectId: string }) {
  const { data: status, isLoading } = useMemoryStatus(projectId)
  const index = useIndexMemory(projectId)
  const search = useSearchMemory(projectId)
  const addNote = useAddMemoryNote(projectId)

  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<MemoryHit[] | null>(null)
  const [noteOpen, setNoteOpen] = useState(false)
  const [noteTitle, setNoteTitle] = useState('')
  const [noteBody, setNoteBody] = useState('')

  if (isLoading || !status) return null

  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4" />
          <p className="font-medium text-sm">Codebase memory</p>
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[status.status]}`} />
            {status.status}
          </span>
        </div>
        <Button
          size="sm"
          variant="outline"
          disabled={index.isPending || status.status === 'indexing'}
          onClick={() => index.mutate()}
        >
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${status.status === 'indexing' ? 'animate-spin' : ''}`} />
          {status.status === 'ready' ? 'Re-index' : 'Index repo'}
        </Button>
      </div>

      <div className="px-4 py-3 border-b border-border">
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <span className="text-muted-foreground">
            <strong className="text-foreground">{status.chunk_count}</strong> chunks
          </span>
          <span className="text-muted-foreground">
            <strong className="text-foreground">{status.file_count}</strong> files
          </span>
          {Object.entries(status.chunks_by_kind).map(([kind, count]) => (
            <span key={kind} className="text-muted-foreground">
              {kind}: <strong className="text-foreground">{count}</strong>
            </span>
          ))}
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          {status.embedding_backend === 'provider'
            ? `Embeddings via ${status.embedding_model}.`
            : 'Using the deterministic local embedder — set an embedding provider key for stronger retrieval.'}
          {status.last_indexed_at &&
            ` Last indexed ${new Date(status.last_indexed_at).toLocaleString()}.`}
        </p>
        {status.error && <p className="text-xs text-red-600 mt-1">{status.error}</p>}
      </div>

      {/* Retrieval preview */}
      <div className="px-4 py-3 space-y-3">
        <div className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && query) search.mutate(query, { onSuccess: setHits })
            }}
            placeholder="What would an agent retrieve for…"
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
          <Button
            variant="outline"
            disabled={!query || search.isPending}
            onClick={() => search.mutate(query, { onSuccess: setHits })}
          >
            <Search className="h-3.5 w-3.5" />
          </Button>
        </div>

        {hits && (
          hits.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nothing retrieved for that query.</p>
          ) : (
            <div className="space-y-2">
              {hits.map((h) => (
                <div key={h.id} className="border border-border rounded-md p-2.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                      {h.kind}
                    </span>
                    <code className="text-xs text-muted-foreground truncate">
                      {h.path ?? h.title}
                    </code>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1.5 line-clamp-3 whitespace-pre-wrap">
                    {h.excerpt}
                  </p>
                </div>
              ))}
            </div>
          )
        )}
      </div>

      {/* Human-authored memory */}
      <div className="px-4 py-3 border-t border-border">
        {noteOpen ? (
          <div className="space-y-2">
            <input
              value={noteTitle}
              onChange={(e) => setNoteTitle(e.target.value)}
              placeholder="Title — e.g. 'Never call the billing API directly'"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <textarea
              rows={3}
              value={noteBody}
              onChange={(e) => setNoteBody(e.target.value)}
              placeholder="The convention, gotcha or decision the agents should know."
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                disabled={!noteTitle || !noteBody || addNote.isPending}
                onClick={() =>
                  addNote.mutate(
                    { title: noteTitle, content: noteBody, kind: 'convention' },
                    { onSuccess: () => { setNoteOpen(false); setNoteTitle(''); setNoteBody('') } },
                  )
                }
              >
                Add to memory
              </Button>
              <Button size="sm" variant="outline" onClick={() => setNoteOpen(false)}>Cancel</Button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setNoteOpen(true)}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <Plus className="h-3.5 w-3.5" />
            Teach the agents something the repo doesn't say
          </button>
        )}
      </div>
    </div>
  )
}
