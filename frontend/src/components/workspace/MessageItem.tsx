/**
 * One message in the scroll.
 *
 * Four kinds render four ways, and the differences are load-bearing rather than
 * decorative:
 *
 *   user             a bubble with an author
 *   agent            the same, marked as a machine — you must always be able to
 *                    tell at a glance whether a person or an agent said it
 *   system           run narration; quieter, no avatar, carries a run card
 *   approval_request the gate itself, with the buttons on it
 *
 * Grouping: consecutive messages from the same author inside a few minutes drop
 * the avatar and header. That is what makes a chat log readable rather than a
 * wall of repeated names, and it is why `isGrouped` is computed by the list and
 * passed down instead of being derived here.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle, Bot, Check, CheckCircle2, GitPullRequest, MessageSquare,
  Pencil, Pin, Rocket, ShieldAlert, Trash2, X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import type { Message } from '@/types/workspace'

/** The reaction set on the hover bar. Deliberately short — a full emoji picker
 *  is a lot of weight for something people use six of. */
const QUICK_REACTIONS = ['👍', '🎉', '👀', '🚀', '❤️', '😄']

const SEVERITY_ICON: Record<string, typeof Rocket> = {
  info: Rocket,
  success: CheckCircle2,
  warning: AlertTriangle,
  critical: ShieldAlert,
}

const SEVERITY_TINT: Record<string, string> = {
  info: 'text-muted-foreground',
  success: 'text-emerald-600',
  warning: 'text-[#E8632A]',
  critical: 'text-red-600',
}

function initials(name: string): string {
  return name.split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? '').join('')
}

function timeOf(iso: string | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

/**
 * Render @mentions and `code` without pulling in a Markdown engine.
 *
 * A full renderer in a chat scroll is both a bundle cost and an XSS surface;
 * this splits on the two patterns that actually carry meaning here and leaves
 * everything else as text, which React escapes for us.
 */
function RichText({ body }: { body: string }) {
  const parts = body.split(/(@[A-Za-z0-9][A-Za-z0-9._-]*|`[^`]+`|\*\*[^*]+\*\*)/g)
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('@')) {
          return (
            <span key={i} className="font-medium text-[#E8632A] bg-[#E8632A]/10 rounded px-1">
              {part}
            </span>
          )
        }
        if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
          return (
            <code key={i} className="app-metric text-[0.85em] bg-muted rounded px-1 py-0.5">
              {part.slice(1, -1)}
            </code>
          )
        }
        if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
          return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>
        }
        return <span key={i}>{part}</span>
      })}
    </>
  )
}

/** The run card carried by a system or approval message. */
function RunCard({ payload }: { payload: Record<string, unknown> }) {
  const runId = payload.run_id as string | undefined
  const prUrl = payload.pr_url as string | undefined
  const prNumber = payload.pr_number as number | undefined
  const score = payload.review_score as number | undefined
  if (!runId) return null

  return (
    <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
      <Link to={`/runs/${runId}`} className="underline underline-offset-2 hover:text-foreground text-muted-foreground">
        Open run trace
      </Link>
      {prUrl && (
        <a
          href={prUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
        >
          <GitPullRequest className="h-3 w-3" />
          PR {prNumber ? `#${prNumber}` : ''}
        </a>
      )}
      {typeof score === 'number' && (
        <span className="app-metric text-muted-foreground">Review {score}/100</span>
      )}
    </div>
  )
}

interface Props {
  message: Message
  isGrouped: boolean
  currentUserId?: string
  onReact: (emoji: string) => void
  onReply: () => void
  onEdit: (body: string) => void
  onDelete: () => void
  onPin: () => void
  onApprove?: (decision: 'approved' | 'changes_requested') => void
}

export default function MessageItem({
  message, isGrouped, currentUserId, onReact, onReply, onEdit, onDelete, onPin, onApprove,
}: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(message.body)
  const [showActions, setShowActions] = useState(false)

  const isMine = message.author?.id === currentUserId && !message.author?.is_agent
  const isAgent = !!message.author?.is_agent
  const isSystem = message.kind === 'system'
  const isGate = message.kind === 'approval_request'

  if (message.is_deleted) {
    return (
      <div className="px-4 py-1 text-xs text-muted-foreground italic">
        This message was deleted.
      </div>
    )
  }

  // ── System narration and the approval gate ────────────────────────────────
  if (isSystem || isGate) {
    const severity = (message.payload?.severity as string) ?? 'info'
    const Icon = SEVERITY_ICON[severity] ?? Rocket
    return (
      <div
        className={cn(
          'px-4 py-2 group',
          isGate && 'bg-[#E8632A]/5 border-l-2 border-[#E8632A]',
        )}
      >
        <div className="flex items-start gap-2.5">
          <Icon className={cn('h-4 w-4 mt-0.5 shrink-0', SEVERITY_TINT[severity] ?? SEVERITY_TINT.info)} />
          <div className="min-w-0 flex-1">
            <div className="text-sm text-foreground/90 whitespace-pre-wrap break-words">
              <RichText body={message.body} />
            </div>
            <RunCard payload={message.payload ?? {}} />

            {isGate && onApprove && (
              <div className="mt-3 flex flex-wrap gap-2">
                <Button size="sm" onClick={() => onApprove('approved')}>
                  <Check className="h-3.5 w-3.5 mr-1.5" /> Approve deploy
                </Button>
                <Button size="sm" variant="outline" onClick={() => onApprove('changes_requested')}>
                  <X className="h-3.5 w-3.5 mr-1.5" /> Request changes
                </Button>
                {/* Approving from chat writes the same Approval row and the same
                    audit entry as the Runs page. Saying so is the point. */}
                <span className="self-center text-[0.65rem] text-muted-foreground">
                  Recorded in the audit log either way
                </span>
              </div>
            )}
          </div>
          <span className="app-metric text-[0.65rem] text-muted-foreground shrink-0">
            {timeOf(message.created_at)}
          </span>
        </div>
      </div>
    )
  }

  // ── A person or an agent speaking ─────────────────────────────────────────
  return (
    <div
      className={cn('px-4 group relative', isGrouped ? 'py-0.5' : 'pt-3 pb-0.5')}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="flex gap-2.5">
        {/* Avatar column — kept at a fixed width so grouped messages align. */}
        <div className="w-8 shrink-0">
          {!isGrouped && (
            <div
              className={cn(
                'h-8 w-8 rounded flex items-center justify-center text-[0.7rem] font-semibold',
                isAgent
                  ? 'bg-[#E8632A]/15 text-[#E8632A]'
                  : 'bg-foreground text-background',
              )}
            >
              {isAgent ? <Bot className="h-4 w-4" /> : initials(message.author?.name ?? '?')}
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          {!isGrouped && (
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-medium text-foreground">
                {message.author?.name ?? 'Unknown'}
              </span>
              {isAgent && (
                <span className="onto-label text-[#E8632A]">
                  agent{message.author?.role ? ` · ${message.author.role}` : ''}
                </span>
              )}
              <span className="app-metric text-[0.65rem] text-muted-foreground">
                {timeOf(message.created_at)}
              </span>
              {message.is_pinned && <Pin className="h-3 w-3 text-[#E8632A]" />}
            </div>
          )}

          {editing ? (
            <div className="mt-1 space-y-2">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                className="w-full text-sm rounded border border-border bg-background p-2 resize-none"
                rows={2}
                autoFocus
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => { onEdit(draft); setEditing(false) }}
                  disabled={!draft.trim() || draft === message.body}
                >
                  Save
                </Button>
                <Button size="sm" variant="ghost" onClick={() => { setDraft(message.body); setEditing(false) }}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-foreground/90 whitespace-pre-wrap break-words">
              <RichText body={message.body} />
              {message.edited_at && (
                <span className="ml-1.5 text-[0.65rem] text-muted-foreground">(edited)</span>
              )}
            </div>
          )}

          <RunCard payload={message.payload ?? {}} />

          {/* Attachments */}
          {message.attachments.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-2">
              {message.attachments.map((a, i) => (
                <a
                  key={i}
                  href={a.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs px-2 py-1 rounded border border-border bg-card hover:bg-muted"
                >
                  {a.name ?? a.url}
                </a>
              ))}
            </div>
          )}

          {/* Reactions */}
          {message.reactions.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {message.reactions.map((r) => (
                <button
                  key={r.emoji}
                  onClick={() => onReact(r.emoji)}
                  className={cn(
                    'text-xs rounded-full border px-1.5 py-0.5 transition-colors',
                    currentUserId && r.users.includes(currentUserId)
                      ? 'border-[#E8632A] bg-[#E8632A]/10'
                      : 'border-border bg-card hover:bg-muted',
                  )}
                >
                  {r.emoji} <span className="app-metric">{r.count}</span>
                </button>
              ))}
            </div>
          )}

          {/* Thread affordance */}
          {message.reply_count > 0 && (
            <button
              onClick={onReply}
              className="mt-1.5 inline-flex items-center gap-1.5 text-xs text-[#E8632A] hover:underline"
            >
              <MessageSquare className="h-3 w-3" />
              {message.reply_count} {message.reply_count === 1 ? 'reply' : 'replies'}
            </button>
          )}
        </div>
      </div>

      {/* Hover action bar */}
      {showActions && !editing && (
        <div className="absolute right-4 -top-3 flex items-center gap-0.5 rounded border border-border bg-card shadow-sm px-1 py-0.5">
          {QUICK_REACTIONS.map((emoji) => (
            <button
              key={emoji}
              onClick={() => onReact(emoji)}
              className="h-6 w-6 text-xs rounded hover:bg-muted"
              title={`React ${emoji}`}
            >
              {emoji}
            </button>
          ))}
          <span className="w-px h-4 bg-border mx-0.5" />
          <button onClick={onReply} className="h-6 w-6 rounded hover:bg-muted grid place-items-center" title="Reply in thread">
            <MessageSquare className="h-3.5 w-3.5" />
          </button>
          <button onClick={onPin} className="h-6 w-6 rounded hover:bg-muted grid place-items-center" title={message.is_pinned ? 'Unpin' : 'Pin'}>
            <Pin className="h-3.5 w-3.5" />
          </button>
          {isMine && (
            <>
              <button onClick={() => setEditing(true)} className="h-6 w-6 rounded hover:bg-muted grid place-items-center" title="Edit">
                <Pencil className="h-3.5 w-3.5" />
              </button>
              <button onClick={onDelete} className="h-6 w-6 rounded hover:bg-muted grid place-items-center text-red-600" title="Delete">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
