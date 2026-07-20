import { useState } from 'react'
import { ChevronDown, ChevronRight, FilePlus, FileMinus, FileEdit } from 'lucide-react'
import { useRunDiff } from '@/hooks/useRuns'

interface FileDiff {
  filename: string
  status: string
  additions: number
  deletions: number
  patch: string
}

// ─── Patch renderer ───────────────────────────────────────────────────────────

function PatchView({ patch }: { patch: string }) {
  if (!patch) return <p className="text-xs text-muted-foreground px-3 py-2">Binary file or no textual diff.</p>

  const lines = patch.split('\n')
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono border-collapse">
        <tbody>
          {lines.map((line, i) => {
            let bg = ''
            let color = 'text-foreground'
            if (line.startsWith('+') && !line.startsWith('+++')) {
              bg = 'bg-green-50 dark:bg-green-950/30'
              color = 'text-green-800 dark:text-green-300'
            } else if (line.startsWith('-') && !line.startsWith('---')) {
              bg = 'bg-red-50 dark:bg-red-950/30'
              color = 'text-red-800 dark:text-red-300'
            } else if (line.startsWith('@@')) {
              bg = 'bg-blue-50 dark:bg-blue-950/30'
              color = 'text-blue-600 dark:text-blue-400'
            } else {
              bg = 'bg-muted/20'
              color = 'text-muted-foreground'
            }
            return (
              <tr key={i} className={`${bg} leading-5`}>
                <td className={`pl-3 pr-4 py-px whitespace-pre select-none ${color}`}>{line || ' '}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ─── Status icon ──────────────────────────────────────────────────────────────

const STATUS_ICON: Record<string, JSX.Element> = {
  added:    <FilePlus  className="h-3.5 w-3.5 text-green-500 shrink-0" />,
  removed:  <FileMinus className="h-3.5 w-3.5 text-red-500   shrink-0" />,
  modified: <FileEdit  className="h-3.5 w-3.5 text-blue-500  shrink-0" />,
}

// ─── File card ────────────────────────────────────────────────────────────────

function FileCard({ file }: { file: FileDiff }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-lg border overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left bg-muted/30 hover:bg-muted/50 transition-colors"
      >
        {STATUS_ICON[file.status] ?? <FileEdit className="h-3.5 w-3.5 text-muted-foreground shrink-0" />}
        <span className="flex-1 text-xs font-mono font-medium truncate">{file.filename}</span>
        <span className="text-xs font-medium text-green-600 shrink-0">+{file.additions}</span>
        <span className="text-xs font-medium text-red-500   shrink-0 ml-1">-{file.deletions}</span>
        {open
          ? <ChevronDown  className="h-3.5 w-3.5 text-muted-foreground shrink-0 ml-1" />
          : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0 ml-1" />
        }
      </button>
      {open && (
        <div className="border-t">
          <PatchView patch={file.patch} />
        </div>
      )}
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

interface Props {
  runId: string
}

export default function PrDiffViewer({ runId }: Props) {
  const { data: files = [], isLoading, error } = useRunDiff(runId)

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-10 rounded-lg border bg-muted/40 animate-pulse" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <p className="text-sm text-muted-foreground rounded-lg border border-dashed py-6 text-center">
        Could not load diff — GitHub connection may be unavailable.
      </p>
    )
  }

  if (files.length === 0) {
    return (
      <p className="text-sm text-muted-foreground rounded-lg border border-dashed py-6 text-center">
        No file changes in this PR.
      </p>
    )
  }

  const totalAdded   = files.reduce((s, f) => s + f.additions, 0)
  const totalDeleted = files.reduce((s, f) => s + f.deletions, 0)

  return (
    <div className="space-y-3">
      {/* Summary bar */}
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span>{files.length} file{files.length !== 1 ? 's' : ''} changed</span>
        <span className="text-green-600 font-medium">+{totalAdded}</span>
        <span className="text-red-500 font-medium">-{totalDeleted}</span>
      </div>

      {/* Per-file cards */}
      {files.map((file) => (
        <FileCard key={file.filename} file={file} />
      ))}
    </div>
  )
}
