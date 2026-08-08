import { AlertTriangle, BookOpen, ExternalLink, FileWarning } from 'lucide-react'
import { useRunSources } from '@/hooks/usePlatform'
import type { SourceRead } from '@/types/platform'

/**
 * What the agents read from outside the repository on this run.
 *
 * The sibling of `ReviewFindings`, and it sits next to it for a reason. The
 * reviewer answers "is this code any good". This answers "was the brief it was
 * written from any good" — and nothing else in the run trace can. A ticket that
 * says "implement per the spec" and links a page that turned out to be a bot
 * wall produces a confident-looking plan built on nothing, and the person about
 * to approve the deploy is the one who needs to know.
 *
 * Advisory only, exactly like the review score: a bad read never fails a run.
 */
export default function SourceReads({ runId }: { runId: string }) {
  const { data, isLoading } = useRunSources(runId)

  if (isLoading || !data || data.count === 0) return null

  const degraded = data.worst_score !== null && data.worst_score < 75
  const reductionPct =
    data.tokens_before > 0 ? Math.round((data.tokens_saved / data.tokens_before) * 100) : 0

  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {degraded || data.failed > 0 ? (
            <AlertTriangle className="h-4 w-4 text-[#E8632A]" />
          ) : (
            <BookOpen className="h-4 w-4 text-emerald-600" />
          )}
          <p className="font-medium text-sm">Linked sources</p>
          <span className="text-xs text-muted-foreground">
            {data.count} read{data.count === 1 ? '' : 's'}
            {data.failed > 0 && ` · ${data.failed} failed`}
          </span>
        </div>

        {/* The saving, because it is the reason this step exists: the agent read
            the article rather than ~800 kB of page furniture. */}
        {data.tokens_saved > 0 && (
          <div className="flex items-center gap-2">
            <span className="onto-label">Tokens saved</span>
            <span className="app-metric text-lg">
              {data.tokens_saved.toLocaleString()}
              <span className="text-xs font-normal text-muted-foreground ml-1">
                ({reductionPct}%)
              </span>
            </span>
          </div>
        )}
      </div>

      <div className="divide-y divide-border">
        {data.sources.map((source) => (
          <SourceRow key={source.id} source={source} />
        ))}
      </div>
    </div>
  )
}

function SourceRow({ source }: { source: SourceRead }) {
  const failed = source.status !== 'ok'
  // Only the flags that mean something is wrong. An "ok" flag on a clean read is
  // noise in a trace someone is scanning for problems.
  const problems = source.flags.filter((f) => f.severity !== 'ok')

  return (
    <div className="px-4 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {failed && <FileWarning className="h-3.5 w-3.5 shrink-0 text-[#E8632A]" />}
            <p className="text-sm font-medium truncate">
              {source.title || source.url}
            </p>
          </div>
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer noopener"
            className="mt-0.5 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground truncate max-w-full"
          >
            <span className="truncate">{source.url}</span>
            <ExternalLink className="h-3 w-3 shrink-0" />
          </a>
        </div>

        {failed ? (
          <span className="shrink-0 text-xs px-2 py-0.5 rounded bg-red-50 text-red-700">
            Not read
          </span>
        ) : (
          <RiskScore score={source.read_score} risk={source.hallucination_risk} />
        )}
      </div>

      {failed && source.error && (
        <p className="mt-2 text-xs text-muted-foreground">{source.error}</p>
      )}

      {problems.length > 0 && (
        <ul className="mt-2 space-y-1">
          {problems.map((flag, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
              <span
                className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${
                  flag.severity === 'high'
                    ? 'bg-[#E8632A]'
                    : flag.severity === 'medium'
                      ? 'bg-amber-500'
                      : 'bg-muted-foreground'
                }`}
              />
              {flag.text}
            </li>
          ))}
        </ul>
      )}

      {!failed && (
        <p className="mt-2 text-[11px] text-muted-foreground">
          <span className="app-metric">{source.tokens_before.toLocaleString()}</span> →{' '}
          <span className="app-metric">{source.tokens_after.toLocaleString()}</span> tokens ·{' '}
          {source.latency_ms} ms{source.cached && ' · cached'}
        </p>
      )}
    </div>
  )
}

function RiskScore({
  score,
  risk,
}: {
  score: number | null
  risk: SourceRead['hallucination_risk']
}) {
  if (score === null) return null

  return (
    <div className="shrink-0 text-right">
      <span
        className={`app-metric text-base ${risk === 'low' ? '' : 'text-[#E8632A]'}`}
      >
        {score}
        <span className="text-[10px] font-normal text-muted-foreground">/100</span>
      </span>
      {/* The risk is written out, not just implied by a colour — this line is
          the whole point of the panel and it has to survive being read by
          someone who cannot distinguish the two shades. */}
      {risk !== 'low' && (
        <p className="onto-label text-[#E8632A]">{risk} risk</p>
      )}
    </div>
  )
}
