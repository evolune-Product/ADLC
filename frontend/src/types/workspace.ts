// ─── Workspace — the collaboration layer ─────────────────────────────────────
//
// Mirrors `backend/app/services/workspace_service.py::serialize_channel` and
// `serialize_message`. Those two functions are the contract; if a field moves
// there it moves here, and nowhere else.

export type ChannelKind = 'channel' | 'private' | 'broadcast' | 'dm' | 'group_dm'
export type MessageKind = 'user' | 'agent' | 'system' | 'approval_request'
export type NotifyLevel = 'all' | 'mentions' | 'none'
export type PresenceStatus = 'active' | 'away' | 'dnd' | 'offline'

export interface Channel {
  id: string
  kind: ChannelKind
  /** NULL on the wire for a DM the server could not resolve a partner for. */
  name: string | null
  slug: string | null
  topic: string | null
  description: string | null
  project_id: string | null
  run_id: string | null
  ticket_id: string | null
  is_default: boolean
  is_archived: boolean
  message_count: number
  last_message_at: string | null
  last_message_preview: string | null
  /** Unread top-level messages since this member's high-water mark. */
  unread: number
  /** Of those, how many name you specifically. A different urgency. */
  unread_mentions: number
  is_member: boolean
  is_muted: boolean
  is_starred: boolean
  notify_level: NotifyLevel
  member_role: 'owner' | 'admin' | 'member' | null
  created_at: string | null
}

export interface MessageAuthor {
  id: string
  name: string
  email: string | null
  avatar_url: string | null
  is_agent: boolean
  /** Present only for agents — the pipeline role (dev, qa, review…). */
  role?: string
}

export interface MessageMentions {
  users?: string[]
  agents?: string[]
  channel?: boolean
  here?: boolean
}

export interface MessageAttachment {
  type: string
  url: string
  name?: string
  size?: number
  meta?: Record<string, unknown>
}

export interface MessageReaction {
  emoji: string
  users: string[]
  count: number
}

export interface Message {
  id: string
  channel_id: string
  parent_id: string | null
  kind: MessageKind
  author: MessageAuthor | null
  body: string
  mentions: MessageMentions
  attachments: MessageAttachment[]
  /** Kind-specific. Run cards, approval state, slash-command results. */
  payload: Record<string, unknown>
  reactions: MessageReaction[]
  reply_count: number
  last_reply_at: string | null
  is_pinned: boolean
  is_deleted: boolean
  edited_at: string | null
  created_at: string | null
  /** Only on the POST response, when an @mention started work. */
  dispatched?: Array<{ run_id: string; ticket: string | null; status: string }>
  /** Only on search results. */
  channel?: { id: string; name: string | null; kind: ChannelKind } | null
}

export interface ChannelMember {
  id: string
  role: 'owner' | 'admin' | 'member'
  is_agent: boolean
  user?: { id: string; name: string; email: string; avatar_url: string | null }
  agent?: { id: string; name: string; role: string; model: string; is_active: boolean }
  presence: PresenceStatus
  status_text?: string | null
  status_emoji?: string | null
}

export interface DirectoryEntry {
  id: string
  name: string
  /** What you type after the @. */
  handle: string
  email?: string
  avatar_url?: string | null
  org_role?: string
  role?: string
  model?: string
  presence: PresenceStatus
  status_text?: string | null
  is_agent: boolean
}

export interface ChannelListResponse {
  channels: Channel[]
  total_unread: number
  total_mentions: number
}

export interface MessagePage {
  messages: Message[]
  has_more: boolean
  next_cursor: string | null
}

export interface CatchupResult {
  summary: string
  message_count: number
  cost_millicents: number
}

export interface UnreadSummary {
  total: number
  mentions: number
  by_channel: Record<string, number>
}

export interface PresenceState {
  status: PresenceStatus
  status_text: string | null
  status_emoji: string | null
  last_seen_at?: string | null
  dnd_until?: string | null
}
