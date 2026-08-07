import { AlertTriangle, ShieldCheck } from 'lucide-react'
import { useRunFindings } from '@/hooks/usePlatform'
import type { Severity } from '@/types/platform'

const SEVERITY_STYLE: Record<Severity, { dot: string; label: string }> = {
  critical: { dot: 'bg-red-600', label: 'Critical' },
  high: { dot: 'bg-[#E8632A]', label: 'High' },
  medium: { dot: 'bg-amber-500', label: 'Medium' },
  low: { dot: 'bg-muted-foreground', label: 'Low' },
  info: { dot: 'bg-muted-foreground', label: 'Info' },
}

/**
 * Reviewer agent output on a run.
 *
 * This is the differentiator against a generic PR bot: the findings come from
 * *your* rubric skills, and the score is what the approval policy gates on.
 */
export default function ReviewFindings({ runId }: { runId: string }) {
  const { data, isLoading } = useRunFindings(runId)

  if (isLoading || !data || data.count === 0) return null

  const blocking = data.findings.filter((f) => f.severity === 'critical' || f.severity === 'high')

  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {blocking.length > 0 ? (
            <AlertTriangle className="h-4 w-4 text-[#E8632A]" />
          ) : (
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
          )}
          <p className="font-medium text-sm">Reviewer agent</p>
        </div>
        {data.score !== null && (
          <div className="flex items-center gap-2">
            <span className="onto-label">Score</span>
            <span
              className={`text-lg font-semibold tabular-nums ${
                data.score >= 70 ? '' : 'text-[#E8632A]'
              }`}
            >
              {data.score}
              <span className="text-xs font-normal text-muted-foreground">/100</span>
            </span>
          </div>
        )}
      </div>

      <div className="divide-y divide-border">
        {data.findings.map((f) => {
          const style = SEVERITY_STYLE[f.severity] ?? SEVERITY_STYLE.info
          return (
            <div key={f.id} className="px-4 py-3">
              <div className="flex items-start gap-2.5">
                <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${style.dot}`} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium">{style.label}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                      {f.category}
                    </span>
                    {f.file_path && (
                      <code className="text-[11px] text-muted-foreground truncate">
                        {f.file_path}
                        {f.line ? `:${f.line}` : ''}
                      </code>
                    )}
                  </div>
                  <p className="text-sm mt-1">{f.message}</p>
                  {f.suggestion && (
                    <p className="text-sm text-muted-foreground mt-1.5 border-l-2 border-border pl-2.5">
                      {f.suggestion}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <p className="px-4 py-2.5 text-xs text-muted-foreground border-t border-border">
        Findings were posted to the pull request as review comments, and count against any approval
        policy that sets a minimum score or a blocking severity.
      </p>
    </div>
  )
}
