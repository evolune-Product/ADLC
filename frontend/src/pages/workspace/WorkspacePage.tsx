/**
 * The workspace — channels, threads, agents and the approval gate in one place.
 *
 * This page is the reason a team can stop keeping a WhatsApp group. Everything
 * that would otherwise happen in a side channel happens here, attached to the
 * work it is about: runs narrate themselves into the project's channel, an
 * @mention of an agent starts one, and an approval is a message with buttons
 * that writes the same audit row as the Runs page.
 *
 * Layout is three columns — rail, conversation, thread — collapsing to one on
 * mobile, because the phone is where a WhatsApp group would have been read.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import {
  ArrowLeft, Bell, BellOff, Bot, Hash, Loader2, Lock, Megaphone, MessageSquare,
  Pin, Search, Sparkles, Star, Users, X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import api, { getApiError } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import ChannelSidebar from '@/components/workspace/ChannelSidebar'
import Composer from '@/components/workspace/Composer'
import MessageItem from '@/components/workspace/MessageItem'
import ThreadPanel from '@/components/workspace/ThreadPanel'
import {
  TYPING_TTL, useCatchup, useChannelMembers, useChannelPrefs, useChannelSocket,
  useChannels, useCreateChannel, useDeleteMessage, useDirectory, useEditMessage,
  useMessages, useOpenDm, useMarkChannelRead, usePins, usePostMessage, useReact,
  useThread, useTogglePin, useTypingSignal, useWorkspaceLive, useWorkspaceSearch, wsKeys,
} from '@/hooks/useWorkspace'
import { useQueryClient } from '@tanstack/react-query'
import type { Channel, Message } from '@/types/workspace'

/** Messages this close together from the same author render as one block. */
const GROUP_WINDOW_MS = 5 * 60 * 1000

const KIND_ICON = {
  channel: Hash, private: Lock, broadcast: Megaphone,
  dm: MessageSquare, group_dm: MessageSquare,
} as const

function isGrouped(prev: Message | undefined, msg: Message): boolean {
  if (!prev) return false
  if (prev.kind !== msg.kind) return false
  if (msg.kind === 'system' || msg.kind === 'approval_request') return false
  if (prev.author?.id !== msg.author?.id) return false
  if (!prev.created_at || !msg.created_at) return false
  return new Date(msg.created_at).getTime() - new Date(prev.created_at).getTime() < GROUP_WINDOW_MS
}

export default function WorkspacePage() {
  const { channelId } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)

  const [threadId, setThreadId] = useState<string | null>(null)
  const [showMembers, setShowMembers] = useState(false)
  const [showPins, setShowPins] = useState(false)
  const [showBrowse, setShowBrowse] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [catchupText, setCatchupText] = useState<string | null>(null)
  const [typers, setTypers] = useState<Record<string, { name: string; at: number }>>({})

  const scrollRef = useRef<HTMLDivElement>(null)

  const { data: channelData, isLoading } = useChannels()
  const channels = useMemo(() => channelData?.channels ?? [], [channelData])
  const active = useMemo(
    () => channels.find((c) => c.id === channelId),
    [channels, channelId],
  )

  const { data: messagePage } = useMessages(channelId)
  const { data: directoryData } = useDirectory()
  const { data: memberData } = useChannelMembers(showMembers ? channelId : undefined)
  const { data: pinData } = usePins(showPins ? channelId : undefined)
  const { data: threadData } = useThread(threadId ?? undefined)
  const { data: searchData } = useWorkspaceSearch(searchQuery)

  const post = usePostMessage(channelId)
  const edit = useEditMessage(channelId)
  const remove = useDeleteMessage(channelId)
  const react = useReact(channelId)
  const pin = useTogglePin(channelId)
  const prefs = useChannelPrefs()
  const createChannel = useCreateChannel()
  const openDm = useOpenDm()
  const markRead = useMarkChannelRead()
  const catchup = useCatchup(channelId)
  const signalTyping = useTypingSignal(channelId)

  const directory = useMemo(
    () => [...(directoryData?.agents ?? []), ...(directoryData?.people ?? [])],
    [directoryData],
  )

  // ── Live wiring ───────────────────────────────────────────────────────────

  const onTyping = useCallback((who: { userId: string; name: string }) => {
    if (who.userId === currentUser?.id) return
    setTypers((prev) => ({ ...prev, [who.userId]: { name: who.name, at: Date.now() } }))
  }, [currentUser?.id])

  // Badges for every channel you belong to, plus the rendering feed for the
  // one on screen. Two hooks, one socket event, deliberately separate caches.
  useWorkspaceLive(channels, currentUser?.id)
  useChannelSocket(channelId, onTyping, active?.is_member ?? false)

  // Expire typing indicators locally. The sender refreshes faster than the TTL
  // while they are still typing, so a stale name here means they stopped.
  useEffect(() => {
    if (Object.keys(typers).length === 0) return
    const t = setInterval(() => {
      const now = Date.now()
      setTypers((prev) => {
        const next = Object.fromEntries(
          Object.entries(prev).filter(([, v]) => now - v.at < TYPING_TTL),
        )
        return Object.keys(next).length === Object.keys(prev).length ? prev : next
      })
    }, 1000)
    return () => clearInterval(t)
  }, [typers])

  // Land on a channel rather than an empty pane on first visit.
  useEffect(() => {
    if (!channelId && channels.length > 0) {
      const first = channels.find((c) => c.slug === 'general') ?? channels[0]
      navigate(`/workspace/${first.id}`, { replace: true })
    }
  }, [channelId, channels, navigate])

  // Opening a channel marks it read and clears any catch-up from the last one.
  useEffect(() => {
    if (!channelId) return
    setThreadId(null)
    setCatchupText(null)
    markRead.mutate(channelId)
    // markRead is a stable mutation object; including it would re-fire on every
    // render of the page rather than on a channel change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channelId])

  // Stick to the bottom as messages arrive. Only when already near it — yanking
  // someone out of history they are reading is worse than a missed message.
  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 200
    if (nearBottom) el.scrollTop = el.scrollHeight
  }, [messagePage?.messages.length])

  // ── Actions ───────────────────────────────────────────────────────────────

  async function approveFromChat(message: Message, decision: 'approved' | 'changes_requested') {
    const runId = message.payload?.run_id as string | undefined
    if (!runId) return
    const comment = decision === 'changes_requested'
      ? window.prompt('What needs to change? (required)')
      : undefined
    if (decision === 'changes_requested' && !comment) return

    try {
      await api.post(`/runs/${runId}/approve`, { decision, comment })
      toast.success(decision === 'approved' ? 'Deploy approved' : 'Changes requested')
      qc.invalidateQueries({ queryKey: wsKeys.messages(channelId ?? '') })
      qc.invalidateQueries({ queryKey: ['runs'] })
    } catch (e) {
      toast.error(getApiError(e, 'Could not record that decision'))
    }
  }

  function runCatchup() {
    catchup.mutate(undefined, {
      onSuccess: (data) => setCatchupText(data.summary),
    })
  }

  const messages = messagePage?.messages ?? []
  const typingNames = Object.values(typers).map((t) => t.name)

  if (isLoading) {
    return (
      <div className="h-[calc(100vh-3rem)] grid place-items-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const ActiveIcon = active ? (KIND_ICON[active.kind] ?? Hash) : Hash
  const canPost = !active?.is_archived &&
    !(active?.kind === 'broadcast' && !['owner', 'admin'].includes(active.member_role ?? ''))

  return (
    // The dashboard shell owns a 3rem topbar; this page takes the rest and
    // manages its own scrolling, because a chat log inside a page-level scroll
    // cannot stick to the bottom.
    <div className="flex h-[calc(100vh-3rem)] -m-6 overflow-hidden">
      <div className="hidden md:flex">
        <ChannelSidebar
          channels={channels}
          activeId={channelId}
          totalMentions={channelData?.total_mentions ?? 0}
          onSelect={(c) => navigate(`/workspace/${c.id}`)}
          onCreate={() => {
            const name = window.prompt('Channel name')
            if (name?.trim()) createChannel.mutate({ name: name.trim() })
          }}
          onBrowse={() => setShowBrowse(true)}
        />
      </div>

      {/* ── Conversation ─────────────────────────────────────────────────── */}
      <section className="flex-1 flex flex-col min-w-0">
        {/* Channel header */}
        <header className="h-12 px-4 flex items-center gap-3 border-b border-border shrink-0">
          <button
            onClick={() => navigate('/workspace')}
            className="md:hidden h-7 w-7 rounded grid place-items-center hover:bg-foreground/5"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>

          <ActiveIcon className="h-4 w-4 text-muted-foreground shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{active?.name ?? 'Select a channel'}</p>
            {active?.topic && (
              <p className="text-xs text-muted-foreground truncate">{active.topic}</p>
            )}
          </div>

          <div className="ml-auto flex items-center gap-1">
            {active && (
              <>
                <button
                  onClick={runCatchup}
                  disabled={catchup.isPending}
                  className="h-7 px-2 rounded text-xs inline-flex items-center gap-1.5 hover:bg-foreground/5 text-muted-foreground hover:text-foreground"
                  title="Summarise what you missed"
                >
                  {catchup.isPending
                    ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    : <Sparkles className="h-3.5 w-3.5" />}
                  Catch up
                </button>
                <button
                  onClick={() => prefs.mutate({ id: active.id, is_starred: !active.is_starred })}
                  className={cn('h-7 w-7 rounded grid place-items-center hover:bg-foreground/5',
                    active.is_starred ? 'text-[#E8632A]' : 'text-muted-foreground')}
                  title={active.is_starred ? 'Unstar' : 'Star'}
                >
                  <Star className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => prefs.mutate({ id: active.id, is_muted: !active.is_muted })}
                  className="h-7 w-7 rounded grid place-items-center hover:bg-foreground/5 text-muted-foreground hover:text-foreground"
                  title={active.is_muted ? 'Unmute' : 'Mute'}
                >
                  {active.is_muted ? <BellOff className="h-3.5 w-3.5" /> : <Bell className="h-3.5 w-3.5" />}
                </button>
                <button
                  onClick={() => { setShowPins((v) => !v); setShowMembers(false) }}
                  className="h-7 w-7 rounded grid place-items-center hover:bg-foreground/5 text-muted-foreground hover:text-foreground"
                  title="Pinned"
                >
                  <Pin className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => { setShowMembers((v) => !v); setShowPins(false) }}
                  className="h-7 w-7 rounded grid place-items-center hover:bg-foreground/5 text-muted-foreground hover:text-foreground"
                  title="Members"
                >
                  <Users className="h-3.5 w-3.5" />
                </button>
              </>
            )}
          </div>
        </header>

        {/* Search bar — searching replaces the scroll rather than overlaying it */}
        <div className="px-4 py-2 border-b border-border shrink-0">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search every message you can see…"
              className="w-full text-sm rounded border border-border bg-background pl-8 pr-8 py-1.5 focus:outline-none focus:ring-1 focus:ring-foreground/20"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Catch-up result */}
        {catchupText && (
          <div className="mx-4 mt-3 rounded-lg border border-[#E8632A]/30 bg-[#E8632A]/5 p-3 shrink-0">
            <div className="flex items-start gap-2">
              <Sparkles className="h-4 w-4 text-[#E8632A] mt-0.5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="onto-label mb-1">While you were away</p>
                <p className="text-sm whitespace-pre-wrap">{catchupText}</p>
              </div>
              <button onClick={() => setCatchupText(null)} className="text-muted-foreground hover:text-foreground">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* The scroll */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {searchQuery.trim().length >= 2 ? (
            <div className="py-2">
              <p className="onto-label px-4 py-2">
                {searchData?.count ?? 0} results for “{searchQuery}”
              </p>
              {(searchData?.results ?? []).map((m) => (
                <div key={m.id} className="border-b border-border/50">
                  <p className="px-4 pt-2 onto-label">
                    {m.channel?.name ?? 'Direct message'}
                  </p>
                  <MessageItem
                    message={m}
                    isGrouped={false}
                    currentUserId={currentUser?.id}
                    onReact={(emoji) => react.mutate({ id: m.id, emoji })}
                    onReply={() => { navigate(`/workspace/${m.channel_id}`); setSearchQuery('') }}
                    onEdit={(body) => edit.mutate({ id: m.id, body })}
                    onDelete={() => remove.mutate(m.id)}
                    onPin={() => pin.mutate(m.id)}
                  />
                </div>
              ))}
            </div>
          ) : messages.length === 0 ? (
            <div className="h-full grid place-items-center px-6">
              <div className="text-center max-w-sm">
                <ActiveIcon className="h-6 w-6 mx-auto mb-3 text-muted-foreground" />
                <p className="font-medium mb-1">{active?.name ?? 'Nothing here yet'}</p>
                <p className="text-sm text-muted-foreground">
                  This is the start of the channel. Runs for the attached project will
                  narrate themselves here, and you can @mention an agent with a ticket
                  key to start one.
                </p>
              </div>
            </div>
          ) : (
            <div className="py-2">
              {messages.map((m, i) => (
                <MessageItem
                  key={m.id}
                  message={m}
                  isGrouped={isGrouped(messages[i - 1], m)}
                  currentUserId={currentUser?.id}
                  onReact={(emoji) => react.mutate({ id: m.id, emoji })}
                  onReply={() => setThreadId(m.id)}
                  onEdit={(body) => edit.mutate({ id: m.id, body })}
                  onDelete={() => remove.mutate(m.id)}
                  onPin={() => pin.mutate(m.id)}
                  onApprove={
                    m.kind === 'approval_request'
                      ? (decision) => approveFromChat(m, decision)
                      : undefined
                  }
                />
              ))}
              <div className="h-2" />
            </div>
          )}
        </div>

        {/* Typing indicator — reserved height so the scroll does not jump */}
        <div className="h-5 px-4 shrink-0 text-[0.7rem] text-muted-foreground">
          {typingNames.length > 0 && (
            <span>
              {typingNames.slice(0, 3).join(', ')}
              {typingNames.length === 1 ? ' is' : ' are'} typing…
            </span>
          )}
        </div>

        {active && (
          <Composer
            onSend={(body) => post.mutate({ body })}
            onTyping={signalTyping}
            directory={directory}
            sending={post.isPending}
            disabled={!canPost}
            disabledReason={
              active.is_archived
                ? 'This channel is archived.'
                : 'Only channel admins can post to a broadcast channel.'
            }
            placeholder={`Message ${active.name ?? 'this conversation'}…`}
          />
        )}
      </section>

      {/* ── Right rail: thread, members or pins ───────────────────────────── */}
      {threadId && threadData && (
        <div className="hidden lg:flex">
          <ThreadPanel
            parent={threadData.parent}
            replies={threadData.replies}
            directory={directory}
            currentUserId={currentUser?.id}
            sending={post.isPending}
            onClose={() => setThreadId(null)}
            onReply={(body) => post.mutate({ body, parent_id: threadId })}
            onReact={(id, emoji) => react.mutate({ id, emoji })}
            onEdit={(id, body) => edit.mutate({ id, body })}
            onDelete={(id) => remove.mutate(id)}
            onPin={(id) => pin.mutate(id)}
            onApprove={(id, decision) => {
              const msg = threadData.parent.id === id ? threadData.parent : undefined
              if (msg) approveFromChat(msg, decision)
            }}
          />
        </div>
      )}

      {showMembers && (
        <aside className="hidden lg:flex w-64 shrink-0 border-l border-border flex-col bg-background">
          <div className="h-12 px-4 flex items-center justify-between border-b border-border">
            <p className="onto-label">Members</p>
            <button onClick={() => setShowMembers(false)} className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
            {(memberData?.members ?? []).map((m) => (
              <div key={m.id} className="flex items-center gap-2 px-2 py-1.5 rounded text-sm">
                {m.is_agent ? (
                  <Bot className="h-3.5 w-3.5 text-[#E8632A] shrink-0" />
                ) : (
                  <span className={cn(
                    'h-2 w-2 rounded-full shrink-0',
                    m.presence === 'active' ? 'bg-emerald-500'
                      : m.presence === 'dnd' ? 'bg-red-500'
                      : m.presence === 'away' ? 'bg-amber-500' : 'bg-muted-foreground/40',
                  )} />
                )}
                <span className="truncate flex-1">
                  {m.is_agent ? m.agent?.name : m.user?.name}
                </span>
                {m.role !== 'member' && <span className="onto-label">{m.role}</span>}
              </div>
            ))}
          </div>
        </aside>
      )}

      {showPins && (
        <aside className="hidden lg:flex w-[26rem] shrink-0 border-l border-border flex-col bg-background">
          <div className="h-12 px-4 flex items-center justify-between border-b border-border">
            <p className="onto-label">Pinned</p>
            <button onClick={() => setShowPins(false)} className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {(pinData?.pins ?? []).length === 0 ? (
              <p className="p-4 text-sm text-muted-foreground">
                Nothing pinned yet. Pin the decisions people keep asking about.
              </p>
            ) : (
              (pinData?.pins ?? []).map((m) => (
                <MessageItem
                  key={m.id}
                  message={m}
                  isGrouped={false}
                  currentUserId={currentUser?.id}
                  onReact={(emoji) => react.mutate({ id: m.id, emoji })}
                  onReply={() => setThreadId(m.id)}
                  onEdit={(body) => edit.mutate({ id: m.id, body })}
                  onDelete={() => remove.mutate(m.id)}
                  onPin={() => pin.mutate(m.id)}
                />
              ))
            )}
          </div>
        </aside>
      )}

      {/* ── Browse people and channels ───────────────────────────────────── */}
      {showBrowse && (
        <div
          className="fixed inset-0 z-50 bg-black/40 grid place-items-center p-4"
          onClick={() => setShowBrowse(false)}
        >
          <div
            className="bg-card rounded-lg border border-border w-full max-w-md max-h-[70vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <p className="font-medium">Start a conversation</p>
              <button onClick={() => setShowBrowse(false)} className="text-muted-foreground hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              <p className="onto-label px-2 py-1.5">People</p>
              {(directoryData?.people ?? [])
                .filter((p) => p.id !== currentUser?.id)
                .map((p) => (
                  <button
                    key={p.id}
                    onClick={() => openDm.mutate(p.id, {
                      onSuccess: (ch: Channel) => {
                        setShowBrowse(false)
                        navigate(`/workspace/${ch.id}`)
                      },
                    })}
                    className="w-full flex items-center gap-2 px-2 py-2 rounded text-sm hover:bg-muted text-left"
                  >
                    <span className={cn(
                      'h-2 w-2 rounded-full shrink-0',
                      p.presence === 'active' ? 'bg-emerald-500' : 'bg-muted-foreground/40',
                    )} />
                    <span className="flex-1 truncate">{p.name}</span>
                    <span className="text-xs text-muted-foreground">@{p.handle}</span>
                  </button>
                ))}

              <p className="onto-label px-2 py-1.5 mt-2">Channels you can join</p>
              {channels.filter((c) => !c.is_member && c.kind !== 'dm').map((c) => (
                <button
                  key={c.id}
                  onClick={() => { setShowBrowse(false); navigate(`/workspace/${c.id}`) }}
                  className="w-full flex items-center gap-2 px-2 py-2 rounded text-sm hover:bg-muted text-left"
                >
                  <Hash className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="flex-1 truncate">{c.name}</span>
                </button>
              ))}
            </div>
            <div className="px-4 py-3 border-t border-border">
              <Button
                className="w-full"
                onClick={() => {
                  const name = window.prompt('Channel name')
                  if (name?.trim()) {
                    createChannel.mutate({ name: name.trim() }, {
                      onSuccess: (ch) => { setShowBrowse(false); navigate(`/workspace/${ch.id}`) },
                    })
                  }
                }}
              >
                New channel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
