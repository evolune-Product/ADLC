import { useState } from 'react'
import { ThumbsDown, ThumbsUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useSubmitFeedback } from '@/hooks/usePlatform'

const CATEGORIES = [
  { value: 'wrong_approach', label: 'Wrong approach' },
  { value: 'missing_tests', label: 'Missing tests' },
  { value: 'scope_creep', label: 'Did more than asked' },
  { value: 'style', label: 'Style / conventions' },
  { value: 'other', label: 'Something else' },
]

const ROLES = ['sprint', 'dev', 'qa', 'reviewer', 'devops']

/**
 * Per-run quality signal. Cheap for the reviewer, and it is the only input that
 * turns run history into agent scorecards — so it sits directly under the diff
 * where the judgement is already being made.
 */
export default function FeedbackWidget({ runId }: { runId: string }) {
  const submit = useSubmitFeedback(runId)
  const [rating, setRating] = useState<number | null>(null)
  const [role, setRole] = useState('dev')
  const [category, setCategory] = useState('')
  const [comment, setComment] = useState('')
  const [done, setDone] = useState(false)

  if (done) {
    return (
      <div className="bg-card rounded-lg border border-border p-4 text-sm text-muted-foreground">
        Feedback recorded — it now feeds this agent's scorecard in Insights.
      </div>
    )
  }

  return (
    <div className="bg-card rounded-lg border border-border p-4 space-y-3">
      <p className="font-medium text-sm">How was this agent's work?</p>

      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant={rating === 1 ? 'default' : 'outline'}
          onClick={() => setRating(1)}
        >
          <ThumbsUp className="h-3.5 w-3.5 mr-1.5" /> Good
        </Button>
        <Button
          size="sm"
          variant={rating === -1 ? 'default' : 'outline'}
          onClick={() => setRating(-1)}
        >
          <ThumbsDown className="h-3.5 w-3.5 mr-1.5" /> Needs work
        </Button>

        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="rounded-md border border-input bg-background px-2 py-1.5 text-sm ml-auto"
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>

      {rating === -1 && (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-1.5">
            {CATEGORIES.map((c) => (
              <button
                key={c.value}
                onClick={() => setCategory(c.value)}
                className={`text-xs px-2 py-1 rounded border transition-colors ${
                  category === c.value
                    ? 'bg-foreground text-background border-foreground'
                    : 'border-border text-muted-foreground hover:text-foreground'
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
          <textarea
            rows={2}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What would you have done differently?"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>
      )}

      {rating !== null && (
        <Button
          size="sm"
          disabled={submit.isPending}
          onClick={() =>
            submit.mutate(
              { rating, agent_role: role, category: category || undefined, comment: comment || undefined },
              { onSuccess: () => setDone(true) },
            )
          }
        >
          Submit
        </Button>
      )}
    </div>
  )
}
