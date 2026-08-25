/**
 * The thread drawer.
 *
 * A thread is where a message stops being chatter and becomes work — the PR
 * discussion, the "why did QA fail", the approval argument. It gets its own
 * column rather than an inline expansion so the channel keeps scrolling behind
 * it and you do not lose your place in one to read the other.
 */
import { X } from 'lucide-react'
import MessageItem from './MessageItem'
import Composer from './Composer'
import type { DirectoryEntry, Message } from '@/types/workspace'

interface Props {
  parent: Message
  replies: Message[]
  directory: DirectoryEntry[]
  currentUserId?: string
  sending?: boolean
  onClose: () => void
  onReply: (body: string) => void
  onReact: (messageId: string, emoji: string) => void
  onEdit: (messageId: string, body: string) => void
  onDelete: (messageId: string) => void
  onPin: (messageId: string) => void
  onApprove?: (messageId: string, decision: 'approved' | 'changes_requested') => void
}

export default function ThreadPanel({
  parent, replies, directory, currentUserId, sending,
  onClose, onReply, onReact, onEdit, onDelete, onPin, onApprove,
}: Props) {
  return (
    <aside className="w-[26rem] shrink-0 border-l border-border flex flex-col bg-background">
      <div className="h-12 px-4 flex items-center justify-between border-b border-border shrink-0">
        <div>
          <p className="onto-label">Thread</p>
          <p className="text-xs text-muted-foreground">
            {replies.length} {replies.length === 1 ? 'reply' : 'replies'}
          </p>
        </div>
        <button
          onClick={onClose}
          className="h-7 w-7 rounded grid place-items-center hover:bg-foreground/5 text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* The parent always renders ungrouped — it is the subject of the
            thread, not another line in a run of messages. */}
        <MessageItem
          message={parent}
          isGrouped={false}
          currentUserId={currentUserId}
          onReact={(emoji) => onReact(parent.id, emoji)}
          onReply={() => {}}
          onEdit={(body) => onEdit(parent.id, body)}
          onDelete={() => onDelete(parent.id)}
          onPin={() => onPin(parent.id)}
          onApprove={onApprove ? (d) => onApprove(parent.id, d) : undefined}
        />

        <div className="px-4 py-2 flex items-center gap-3">
          <span className="h-px flex-1 bg-border" />
          <span className="onto-label">
            {replies.length === 0 ? 'No replies yet' : `${replies.length} replies`}
          </span>
          <span className="h-px flex-1 bg-border" />
        </div>

        {replies.map((reply, i) => (
          <MessageItem
            key={reply.id}
            message={reply}
            isGrouped={
              i > 0 &&
              replies[i - 1].author?.id === reply.author?.id &&
              reply.kind === replies[i - 1].kind
            }
            currentUserId={currentUserId}
            onReact={(emoji) => onReact(reply.id, emoji)}
            onReply={() => {}}
            onEdit={(body) => onEdit(reply.id, body)}
            onDelete={() => onDelete(reply.id)}
            onPin={() => onPin(reply.id)}
          />
        ))}
        <div className="h-3" />
      </div>

      <Composer
        onSend={onReply}
        directory={directory}
        placeholder="Reply in thread…"
        sending={sending}
      />
    </aside>
  )
}
