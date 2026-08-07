import { useEffect, useState, type ReactElement } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, ExternalLink, GitBranch, CheckCircle2,
  XCircle, Loader2, Clock, ChevronDown, ChevronRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useRun, useApproveRun, useRetryRun, useCancelRun } from '@/hooks/useRuns'
import { useRunStore } from '@/stores/runStore'
import { getSocket, connectSocket, joinRunRoom, leaveRunRoom } from '@/lib/socket'
import PrDiffViewer from '@/components/runs/PrDiffViewer'
import ReviewFindings from '@/components/runs/ReviewFindings'
import FeedbackWidget from '@/components/runs/FeedbackWidget'
import type { RunStep, DeployTarget } from '@/types'

// ─── Status helpers ───────────────────────────────────────────────────────────

const STATUS_COLOR: Record<string, string> = {
  queued:            'bg-muted text-muted-foreground',
  running:           'bg-blue-100 text-blue-700',
  awaiting_approval: 'bg-yellow-100 text-yellow-700',
  approved:          'bg-green-100 text-green-700',
  completed:         'bg-green-100 text-green-700',
  failed:            'bg-red-100 text-red-700',
}

const STEP_ICON: Record<string, ReactElement> = {
  success: <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />,
  failed:  <XCircle      className="h-4 w-4 text-red-500   shrink-0" />,
  running: <Loader2      className="h-4 w-4 text-blue-500  shrink-0 animate-spin" />,
  skipped: <Clock        className="h-4 w-4 text-muted-foreground  shrink-0" />,
}

function duration(run: { started_at?: string; completed_at?: string }): string {
  if (!run.started_at) return '—'
  const end = run.completed_at ?? new Date().toISOString()
  const ms  = new Date(end).getTime() - new Date(run.started_at).getTime()
  const s   = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
}

function stepDuration(ms?: number): string {
  if (!ms) return ''
  if (ms < 1000) return `${ms}ms`
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
}

// ─── Step row ─────────────────────────────────────────────────────────────────

function StepRow({ step }: { step: RunStep }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-lg border overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent/40 transition-colors"
      >
        {STEP_ICON[step.status] ?? <Clock className="h-4 w-4 shrink-0 text-muted-foreground" />}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium truncate">{step.step_name}</span>
            <span className="text-xs bg-secondary text-secondary-foreground rounded px-1.5 py-0.5 shrink-0">
              {step.agent_role}
            </span>
          </div>
          {step.duration_ms !== undefined && step.duration_ms > 0 && (
            <p className="text-xs text-muted-foreground mt-0.5">{stepDuration(step.duration_ms)}</p>
          )}
        </div>
        {open
          ? <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
          : <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
        }
      </button>

      {open && (
        <div className="border-t bg-muted/20 px-4 py-3 space-y-3">
          {step.log && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Log</p>
              <pre className="text-xs font-mono bg-background rounded p-3 border overflow-x-auto whitespace-pre-wrap max-h-64 overflow-y-auto">
                {step.log}
              </pre>
            </div>
          )}
          {step.output && Object.keys(step.output).length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Output</p>
              <pre className="text-xs font-mono bg-background rounded p-3 border overflow-x-auto whitespace-pre-wrap max-h-40 overflow-y-auto">
                {JSON.stringify(step.output, null, 2)}
              </pre>
            </div>
          )}
          {!step.log && (!step.output || Object.keys(step.output).length === 0) && (
            <p className="text-xs text-muted-foreground">No output yet.</p>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Env pipeline strip ───────────────────────────────────────────────────────

function EnvPipeline({
  deployTargets,
  currentEnvIndex,
  status,
}: {
  deployTargets: DeployTarget[]
  currentEnvIndex: number
  status: string
}) {
  if (!deployTargets.length) return null

  // Which envs are done?
  // currentEnvIndex == -1: none deployed yet (awaiting PR review)
  // currentEnvIndex == N (awaiting_approval): envs 0..N-1 are deployed
  // completed: all envs deployed
  const deployedUpTo = status === 'completed'
    ? deployTargets.length
    : currentEnvIndex <= 0
      ? 0
      : currentEnvIndex  // envs 0..currentEnvIndex-1 are deployed

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {/* PR node */}
      <div className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium ${
        deployedUpTo >= 0 && status !== 'queued' && status !== 'running' && currentEnvIndex !== -1
          ? 'bg-green-50 border-green-200 text-green-700'
          : 'bg-muted border-border text-muted-foreground'
      }`}>
        <CheckCircle2 className="h-3 w-3" />
        PR Merged
      </div>
      {deployTargets.map((t, i) => {
        const done = i < deployedUpTo
        const active = status === 'awaiting_approval' && i === currentEnvIndex
        return (
          <div key={i} className="flex items-center gap-1">
            <div className="w-4 h-px bg-border" />
            <div className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium ${
              done
                ? 'bg-green-50 border-green-200 text-green-700'
                : active
                  ? 'bg-yellow-50 border-yellow-200 text-yellow-700'
                  : 'bg-muted border-border text-muted-foreground'
            }`}>
              {done
                ? <CheckCircle2 className="h-3 w-3" />
                : active
                  ? <Clock className="h-3 w-3" />
                  : <div className="h-3 w-3 rounded-full border border-current opacity-40" />
              }
              {t.env}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Approval panel ───────────────────────────────────────────────────────────

function ApprovalPanel({
  runId,
  prUrl,
  prNumber,
  currentEnvIndex,
  deployTargets,
}: {
  runId: string
  prUrl?: string
  prNumber?: number
  currentEnvIndex: number
  deployTargets: DeployTarget[]
}) {
  const [decision, setDecision] = useState<'approved' | 'changes_requested'>('approved')
  const [comment, setComment]   = useState('')
  const approveMutation = useApproveRun(runId)

  const isPrReview   = currentEnvIndex === -1
  const nextEnv      = !isPrReview && deployTargets[currentEnvIndex] ? deployTargets[currentEnvIndex] : null
  const approveLabel = isPrReview
    ? (deployTargets.length ? `Approve & Deploy to ${deployTargets[0].env}` : 'Approve & Deploy')
    : `Deploy to ${nextEnv?.env ?? 'next env'}`

  function submit() {
    approveMutation.mutate({ decision, comment: comment || undefined })
  }

  return (
    <div className="rounded-lg border p-5 space-y-4 sticky top-4">
      <div>
        <h3 className="font-semibold">
          {isPrReview ? 'Code Review Required' : `Deploy to ${nextEnv?.env ?? 'next env'}`}
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          {isPrReview
            ? prNumber
              ? `PR #${prNumber} is ready for review.`
              : 'The agent is awaiting your approval.'
            : `Approve to merge ${deployTargets[currentEnvIndex - 1]?.branch ?? 'previous env'} → ${nextEnv?.branch}.`
          }
        </p>
      </div>

      {isPrReview && prUrl && (
        <a
          href={prUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-sm text-primary hover:underline"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          Open Pull Request
        </a>
      )}

      <div className="space-y-2">
        <p className="text-sm font-medium">Decision</p>
        <div className="flex flex-col gap-2">
          {(['approved', 'changes_requested'] as const).map((d) => (
            <label key={d} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="decision"
                value={d}
                checked={decision === d}
                onChange={() => setDecision(d)}
                className="accent-primary"
              />
              <span className="text-sm capitalize">{d.replace('_', ' ')}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="space-y-1">
        <p className="text-sm font-medium">Comment <span className="text-muted-foreground font-normal">(optional)</span></p>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Add a comment..."
          rows={3}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      <Button
        className="w-full"
        onClick={submit}
        disabled={approveMutation.isPending}
        variant={decision === 'approved' ? 'default' : 'destructive'}
      >
        {approveMutation.isPending
          ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Submitting...</>
          : decision === 'approved' ? approveLabel : 'Request Changes'
        }
      </Button>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate   = useNavigate()

  const { data: run, isLoading, refetch } = useRun(runId!)
  const { liveSteps, setActiveRun, appendStep, updateStepLog } = useRunStore()
  const retryMutation  = useRetryRun()
  const cancelMutation = useCancelRun()

  // Seed store from polled data whenever run updates
  useEffect(() => {
    if (run) setActiveRun(run)
  }, [run, setActiveRun])

  // Socket.io — join room, listen for live events
  useEffect(() => {
    if (!runId) return
    const socket = getSocket()
    connectSocket()
    joinRunRoom(runId)

    socket.on('run:step:started', (data: RunStep) => appendStep(data))
    socket.on('run:step:log',     (data: { stepName: string; log: string }) =>
      updateStepLog(data.stepName, data.log)
    )
    socket.on('run:step:completed', (data: RunStep) => {
      useRunStore.setState((s) => ({
        liveSteps: s.liveSteps.map((st) =>
          st.step_name === data.step_name ? { ...st, ...data } : st
        ),
      }))
    })

    // Refetch run when an env approval gate is hit so the panel updates
    socket.on('run:awaiting_env_approval', () => { refetch() })
    socket.on('run:completed',             () => { refetch() })

    return () => {
      leaveRunRoom(runId)
      socket.off('run:step:started')
      socket.off('run:step:log')
      socket.off('run:step:completed')
      socket.off('run:awaiting_env_approval')
      socket.off('run:completed')
    }
  }, [runId, appendStep, updateStepLog])

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-4xl mx-auto">
        <div className="h-8 w-48 rounded bg-muted animate-pulse" />
        <div className="h-64 rounded-lg border bg-muted/40 animate-pulse" />
      </div>
    )
  }

  if (!run) {
    return (
      <div className="max-w-4xl mx-auto">
        <p className="text-muted-foreground">Run not found.</p>
        <Button variant="link" className="px-0 mt-2" onClick={() => navigate('/runs')}>Back to Runs</Button>
      </div>
    )
  }

  const isActive     = ['queued', 'running'].includes(run.status)
  const isAwaiting   = run.status === 'awaiting_approval'
  const displaySteps = liveSteps.length > 0 ? liveSteps : run.steps

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 mt-0.5 shrink-0" onClick={() => navigate('/runs')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[run.status] ?? 'bg-secondary'}`}
            >
              {run.status.replace('_', ' ')}
            </span>
            {run.retry_count > 0 && (
              <span className="text-xs text-muted-foreground">Retry #{run.retry_count}</span>
            )}
          </div>
          <p className="text-xs font-mono text-muted-foreground mt-1 truncate">Run {run.id}</p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {isActive && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => cancelMutation.mutate(run.id)}
              disabled={cancelMutation.isPending}
            >
              Cancel
            </Button>
          )}
          {(run.status === 'failed') && (
            <Button
              size="sm"
              onClick={() => retryMutation.mutate(run.id, { onSuccess: () => navigate('/runs') })}
              disabled={retryMutation.isPending}
            >
              {retryMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Retry'}
            </Button>
          )}
        </div>
      </div>

      {/* Meta strip */}
      <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
        {run.branch_name && (
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <GitBranch className="h-3.5 w-3.5" />
            <span className="font-mono text-xs">{run.branch_name}</span>
          </span>
        )}
        {run.pr_url && (
          <a
            href={run.pr_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-primary hover:underline"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            PR #{run.pr_number}
          </a>
        )}
        <span className="text-muted-foreground">Duration: {duration(run)}</span>
        {run.started_at && (
          <span className="text-muted-foreground">
            Started: {new Date(run.started_at).toLocaleString()}
          </span>
        )}
      </div>

      {/* Env deploy pipeline (only shown when deploy targets are configured) */}
      {run.deploy_targets?.length > 0 && (
        <EnvPipeline
          deployTargets={run.deploy_targets}
          currentEnvIndex={run.current_env_index ?? -1}
          status={run.status}
        />
      )}

      {/* Error message */}
      {run.error_message && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <span className="font-medium">Error: </span>{run.error_message}
        </div>
      )}

      {/* Body: steps + optional approval panel */}
      <div className={`grid gap-6 ${isAwaiting ? 'lg:grid-cols-[1fr_320px]' : ''}`}>
        {/* Step timeline */}
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Steps</h2>
          {displaySteps.length === 0 ? (
            <div className="rounded-lg border border-dashed py-10 flex flex-col items-center gap-2">
              {isActive
                ? <><Loader2 className="h-6 w-6 text-muted-foreground animate-spin" /><p className="text-sm text-muted-foreground">Waiting for steps…</p></>
                : <p className="text-sm text-muted-foreground">No steps recorded.</p>
              }
            </div>
          ) : (
            displaySteps.map((step) => <StepRow key={step.id} step={step} />)
          )}
        </div>

        {/* Approval panel */}
        {isAwaiting && (
          <ApprovalPanel
            runId={run.id}
            prUrl={run.pr_url}
            prNumber={run.pr_number}
            currentEnvIndex={run.current_env_index ?? -1}
            deployTargets={run.deploy_targets ?? []}
          />
        )}
      </div>

      {/* Reviewer agent verdict — what the approval policy gates on */}
      <ReviewFindings runId={run.id} />

      {/* Code changes (shown whenever a PR exists) */}
      {run.pr_number && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Code Changes
          </h2>
          <PrDiffViewer runId={run.id} />
        </div>
      )}

      {/* Quality signal — the only input that turns run history into scorecards */}
      {(run.status === 'completed' || run.status === 'awaiting_approval' || run.status === 'failed') && (
        <FeedbackWidget runId={run.id} />
      )}
    </div>
  )
}
