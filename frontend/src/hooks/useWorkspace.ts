/**
 * useWorkspace — data hooks for the collaboration layer.
 *
 * One file, like `usePlatform`, because the invalidation graph is shared and
 * dense: posting a message changes the channel list (preview, ordering),
 * the message page, and the global unread badge. Splitting these across files
 * would mean re-declaring that graph three times and getting it wrong once.
 *
 * The socket is the primary transport for new messages; these hooks are the
 * fallback and the initial load. `useChannelSocket` writes straight into the
 * query cache rather than re-fetching, so a message that arrives over the wire
 * costs nothing — a refetch per inbound message is how a chat UI melts a laptop
 * in an active channel.
 */
import { useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import api, { getApiError } from '@/lib/api'
import { getSocket, joinChannelRoom, leaveChannelRoom } from '@/lib/socket'
import type {
  CatchupResult, Channel, ChannelListResponse, ChannelMember,
  DirectoryEntry, Message, MessagePage, NotifyLevel, PresenceState, UnreadSummary,
} from '@/types/workspace'

const err = (fallback: string) => (e: unknown) => toast.error(getApiError(e, fallback))

export const wsKeys = {
  channels: ['workspace', 'channels'] as const,
  channel: (id: string) => ['workspace', 'channel', id] as const,
  messages: (id: string) => ['workspace', 'messages', id] as const,
  thread: (id: string) => ['workspace', 'thread', id] as const,
  members: (id: string) => ['workspace', 'members', id] as const,
  pins: (id: string) => ['workspace', 'pins', id] as const,
  directory: ['workspace', 'directory'] as const,
  unread: ['workspace', 'unread'] as const,
}

// ═══ Channels ═════════════════════════════════════════════════════════════════

export function useChannels() {
  return useQuery<ChannelListResponse>({
    queryKey: wsKeys.channels,
    queryFn: () => api.get('/workspace/channels').then((r) => r.data),
    // The sidebar is the one surface that must never look stale — but the
    // socket already pushes changes, so this is a safety net, not the mechanism.
    staleTime: 15_000,
  })
}

export function useChannel(channelId?: string) {
  return useQuery<Channel>({
    queryKey: wsKeys.channel(channelId ?? ''),
    queryFn: () => api.get(`/workspace/channels/${channelId}`).then((r) => r.data),
    enabled: !!channelId,
  })
}

export function useCreateChannel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      name: string; kind?: string; topic?: string; description?: string
      project_id?: string; member_ids?: string[]; agent_ids?: string[]
    }) => api.post('/workspace/channels', body).then((r) => r.data as Channel),
    onSuccess: (ch) => {
      qc.invalidateQueries({ queryKey: wsKeys.channels })
      toast.success(`#${ch.slug ?? ch.name} created`)
    },
    onError: err('Could not create the channel'),
  })
}

export function useUpdateChannel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Partial<Channel>) =>
      api.patch(`/workspace/channels/${id}`, body).then((r) => r.data as Channel),
    onSuccess: (ch) => {
      qc.invalidateQueries({ queryKey: wsKeys.channels })
      qc.invalidateQueries({ queryKey: wsKeys.channel(ch.id) })
    },
    onError: err('Could not update the channel'),
  })
}

export function useJoinChannel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/workspace/channels/${id}/join`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: wsKeys.channels }),
    onError: err('Could not join the channel'),
  })
}

export function useLeaveChannel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/workspace/channels/${id}/leave`),
    onSuccess: () => qc.invalidateQueries({ queryKey: wsKeys.channels }),
    onError: err('Could not leave the channel'),
  })
}

export function useChannelPrefs() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: {
      id: string; notify_level?: NotifyLevel; is_muted?: boolean; is_starred?: boolean
    }) => api.patch(`/workspace/channels/${id}/prefs`, body).then((r) => r.data as Channel),
    onSuccess: (ch) => {
      qc.invalidateQueries({ queryKey: wsKeys.channels })
      qc.invalidateQueries({ queryKey: wsKeys.channel(ch.id) })
    },
    onError: err('Could not save that preference'),
  })
}

// ═══ Messages ═════════════════════════════════════════════════════════════════

export function useMessages(channelId?: string) {
  return useQuery<MessagePage>({
    queryKey: wsKeys.messages(channelId ?? ''),
    queryFn: () => api.get(`/workspace/channels/${channelId}/messages`).then((r) => r.data),
    enabled: !!channelId,
  })
}

export function usePostMessage(channelId?: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { body: string; parent_id?: string; attachments?: unknown[] }) =>
      api.post(`/workspace/channels/${channelId}/messages`, body).then((r) => r.data),
    onSuccess: (data: Message & { command?: unknown }) => {
      // A slash command returns a command result, not a message — its output
      // arrives over the socket as a system message, so there is nothing to
      // splice into the cache here.
      qc.invalidateQueries({ queryKey: wsKeys.messages(channelId ?? '') })
      qc.invalidateQueries({ queryKey: wsKeys.channels })
      if (data?.parent_id) qc.invalidateQueries({ queryKey: wsKeys.thread(data.parent_id) })
      if (data?.dispatched?.length) {
        const first = data.dispatched[0]
        toast.success(`Run started for ${first.ticket ?? 'the ticket'}`)
      }
    },
    onError: err('Message not sent'),
  })
}

export function useEditMessage(channelId?: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: string }) =>
      api.patch(`/workspace/messages/${id}`, { body }).then((r) => r.data as Message),
    onSuccess: () => qc.invalidateQueries({ queryKey: wsKeys.messages(channelId ?? '') }),
    onError: err('Could not edit that message'),
  })
}

export function useDeleteMessage(channelId?: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/workspace/messages/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: wsKeys.messages(channelId ?? '') }),
    onError: err('Could not delete that message'),
  })
}

export function useThread(messageId?: string) {
  return useQuery<{ parent: Message; replies: Message[] }>({
    queryKey: wsKeys.thread(messageId ?? ''),
    queryFn: () => api.get(`/workspace/messages/${messageId}/thread`).then((r) => r.data),
    enabled: !!messageId,
  })
}

export function useReact(channelId?: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, emoji }: { id: string; emoji: string }) =>
      api.post(`/workspace/messages/${id}/reactions`, { emoji }).then((r) => r.data as Message),
    onSuccess: (msg) => {
      qc.invalidateQueries({ queryKey: wsKeys.messages(channelId ?? '') })
      if (msg.parent_id) qc.invalidateQueries({ queryKey: wsKeys.thread(msg.parent_id) })
    },
    onError: err('Could not react'),
  })
}

export function useTogglePin(channelId?: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/workspace/messages/${id}/pin`).then((r) => r.data as Message),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: wsKeys.messages(channelId ?? '') })
      qc.invalidateQueries({ queryKey: wsKeys.pins(channelId ?? '') })
    },
    onError: err('Could not pin that message'),
  })
}

export function usePins(channelId?: string) {
  return useQuery<{ pins: Message[] }>({
    queryKey: wsKeys.pins(channelId ?? ''),
    queryFn: () => api.get(`/workspace/channels/${channelId}/pins`).then((r) => r.data),
    enabled: !!channelId,
  })
}

// ═══ Members, directory, DMs ══════════════════════════════════════════════════

export function useChannelMembers(channelId?: string) {
  return useQuery<{ members: ChannelMember[] }>({
    queryKey: wsKeys.members(channelId ?? ''),
    queryFn: () => api.get(`/workspace/channels/${channelId}/members`).then((r) => r.data),
    enabled: !!channelId,
  })
}

export function useAddMembers(channelId?: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { user_ids?: string[]; agent_ids?: string[] }) =>
      api.post(`/workspace/channels/${channelId}/members`, body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: wsKeys.members(channelId ?? '') })
      qc.invalidateQueries({ queryKey: wsKeys.messages(channelId ?? '') })
      toast.success('Added to the channel')
    },
    onError: err('Could not add members'),
  })
}

export function useDirectory() {
  return useQuery<{ people: DirectoryEntry[]; agents: DirectoryEntry[] }>({
    queryKey: wsKeys.directory,
    queryFn: () => api.get('/workspace/directory').then((r) => r.data),
    staleTime: 60_000,
  })
}

export function useOpenDm() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) =>
      api.post(`/workspace/dm/${userId}`).then((r) => r.data as Channel),
    onSuccess: () => qc.invalidateQueries({ queryKey: wsKeys.channels }),
    onError: err('Could not open that conversation'),
  })
}

// ═══ Read state, catch-up, search, presence ═══════════════════════════════════

export function useMarkChannelRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (channelId: string) =>
      api.post(`/workspace/channels/${channelId}/read`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: wsKeys.channels })
      qc.invalidateQueries({ queryKey: wsKeys.unread })
    },
    // Deliberately silent on failure: a read marker that could not be saved is
    // not worth a toast on top of whatever else just broke.
  })
}

export function useCatchup(channelId?: string) {
  return useMutation({
    mutationFn: () =>
      api.get(`/workspace/channels/${channelId}/catchup`).then((r) => r.data as CatchupResult),
    onError: err('Could not summarise this channel'),
  })
}

export function useWorkspaceSearch(q: string, channelId?: string) {
  return useQuery<{ results: Message[]; query: string; count: number }>({
    queryKey: ['workspace', 'search', q, channelId ?? 'all'],
    queryFn: () =>
      api.get('/workspace/search', { params: { q, channel_id: channelId } }).then((r) => r.data),
    enabled: q.trim().length >= 2,
  })
}

export function useUnread() {
  return useQuery<UnreadSummary>({
    queryKey: wsKeys.unread,
    queryFn: () => api.get('/workspace/unread').then((r) => r.data),
    refetchInterval: 60_000,
  })
}

export function useSetPresence() {
  return useMutation({
    mutationFn: (body: {
      status?: string; status_text?: string; status_emoji?: string; dnd_minutes?: number
    }) => api.put('/workspace/presence', body).then((r) => r.data as PresenceState),
    onError: err('Could not update your status'),
  })
}

// ═══ Live wiring ══════════════════════════════════════════════════════════════

/** How long a typing indicator survives without a refresh from the sender. */
const TYPING_TTL = 4000

/**
 * Subscribe to every channel you belong to, and keep the sidebar live.
 *
 * The server publishes each message exactly once, to its channel's room — it
 * does not also send a per-recipient badge event, because that would be one
 * broker publish per member per message. The cost of that decision is paid
 * here: the client joins all of its channels, not just the one on screen, and
 * decides locally whether an inbound message is a badge or a rendered line.
 *
 * This hook owns the badge half. `useChannelSocket` owns the rendering half.
 * They listen to the same event and deliberately touch different caches.
 */
export function useWorkspaceLive(channels: Channel[], currentUserId?: string) {
  const qc = useQueryClient()
  const joined = useRef<Set<string>>(new Set())

  useEffect(() => {
    const mine = channels.filter((c) => c.is_member).map((c) => c.id)
    for (const id of mine) {
      if (!joined.current.has(id)) {
        joinChannelRoom(id)
        joined.current.add(id)
      }
    }
  }, [channels])

  useEffect(() => {
    const socket = getSocket()
    const rooms = joined.current

    const onMessage = (msg: Message) => {
      // Your own message is not unread for you, and a threaded reply does not
      // change the channel's preview line.
      if (msg.author?.id === currentUserId) return
      if (msg.parent_id) return

      qc.setQueryData<ChannelListResponse>(wsKeys.channels, (prev) => {
        if (!prev) return prev
        return {
          ...prev,
          channels: prev.channels.map((c) =>
            c.id === msg.channel_id
              ? {
                  ...c,
                  unread: c.unread + 1,
                  last_message_at: msg.created_at,
                  last_message_preview: msg.body.replace(/\n/g, ' ').slice(0, 280),
                }
              : c,
          ),
        }
      })
    }

    socket.on('message:new', onMessage)
    return () => {
      socket.off('message:new', onMessage)
      // Leave on unmount so a signed-out session stops receiving traffic.
      rooms.forEach((id) => leaveChannelRoom(id))
      rooms.clear()
    }
  }, [qc, currentUserId])
}

/**
 * Subscribe to one channel's live events and fold them into the query cache.
 *
 * Writes directly rather than invalidating: an active channel can produce
 * several messages a second, and a refetch per message would make the scroll
 * jump and the network chatter constantly.
 */
export function useChannelSocket(
  channelId: string | undefined,
  onTyping?: (who: { userId: string; name: string }) => void,
  /** True when `useWorkspaceLive` already owns this room's membership. Passing
   *  it stops this hook from leaving a room the sidebar still needs for badges
   *  the moment you navigate to another channel. */
  isMember = false,
) {
  const qc = useQueryClient()

  useEffect(() => {
    if (!channelId) return
    const socket = getSocket()
    // Idempotent server-side — a room is a set. Joining here covers the case
    // of reading a public channel you have not joined.
    joinChannelRoom(channelId)

    const key = wsKeys.messages(channelId)

    const upsert = (msg: Message) => {
      // A threaded reply does not belong in the channel scroll — it belongs in
      // the thread, and it bumps the parent's reply count.
      if (msg.parent_id) {
        qc.invalidateQueries({ queryKey: wsKeys.thread(msg.parent_id) })
        qc.setQueryData<MessagePage>(key, (prev) =>
          prev ? {
            ...prev,
            messages: prev.messages.map((m) =>
              m.id === msg.parent_id
                ? { ...m, reply_count: m.reply_count + 1, last_reply_at: msg.created_at }
                : m,
            ),
          } : prev,
        )
        return
      }
      qc.setQueryData<MessagePage>(key, (prev) => {
        if (!prev) return prev
        if (prev.messages.some((m) => m.id === msg.id)) return prev
        return { ...prev, messages: [...prev.messages, msg] }
      })
      qc.invalidateQueries({ queryKey: wsKeys.channels })
    }

    const replace = (msg: Message) => {
      qc.setQueryData<MessagePage>(key, (prev) =>
        prev ? { ...prev, messages: prev.messages.map((m) => (m.id === msg.id ? msg : m)) } : prev,
      )
      if (msg.parent_id) qc.invalidateQueries({ queryKey: wsKeys.thread(msg.parent_id) })
    }

    const remove = ({ id }: { id: string }) => {
      qc.setQueryData<MessagePage>(key, (prev) =>
        prev ? {
          ...prev,
          messages: prev.messages.map((m) =>
            m.id === id ? { ...m, is_deleted: true, body: '', attachments: [] } : m,
          ),
        } : prev,
      )
    }

    const typing = (data: { channelId: string; userId: string; name: string }) => {
      if (data.channelId === channelId) onTyping?.({ userId: data.userId, name: data.name })
    }

    socket.on('message:new', upsert)
    socket.on('message:updated', replace)
    socket.on('message:deleted', remove)
    socket.on('typing', typing)

    return () => {
      socket.off('message:new', upsert)
      socket.off('message:updated', replace)
      socket.off('message:deleted', remove)
      socket.off('typing', typing)
      if (!isMember) leaveChannelRoom(channelId)
    }
  }, [channelId, qc, onTyping, isMember])
}

/**
 * Typing indicators, with the send-rate throttle on this side.
 *
 * One POST per keystroke would be a request per character. The server emits
 * and forgets; the receiver expires the indicator after TYPING_TTL, so the
 * sender only has to refresh it slower than that.
 */
export function useTypingSignal(channelId?: string) {
  const lastSent = useRef(0)
  return () => {
    if (!channelId) return
    const now = Date.now()
    if (now - lastSent.current < TYPING_TTL / 2) return
    lastSent.current = now
    api.post(`/workspace/channels/${channelId}/typing`).catch(() => {})
  }
}

export { TYPING_TTL }
