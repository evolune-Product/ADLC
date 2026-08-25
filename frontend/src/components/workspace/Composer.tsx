/**
 * The composer, with @mention autocomplete and slash-command hinting.
 *
 * The autocomplete is the feature that makes agents usable. Typing "@" has to
 * surface the QA agent next to your colleagues, because the whole premise is
 * that assigning work to a machine is the same gesture as asking a person —
 * if agents are hidden behind a different menu, nobody uses them.
 *
 * Enter sends, Shift+Enter breaks the line. That is the convention every chat
 * tool has converged on and violating it is a daily papercut.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { Bot, CornerDownLeft, Loader2, Send, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { DirectoryEntry } from '@/types/workspace'

const SLASH_HINTS = [
  { cmd: '/run', hint: 'PROJ-214 — start a run for a ticket' },
  { cmd: '/status', hint: 'the last five runs in this project' },
  { cmd: '/approve', hint: '<run-id> — approve a waiting deploy' },
  { cmd: '/reject', hint: '<run-id> <reason> — send it back' },
  { cmd: '/catchup', hint: 'summarise what you missed' },
  { cmd: '/invite', hint: '@someone — add a person or an agent' },
  { cmd: '/help', hint: 'all commands' },
]

interface Props {
  onSend: (body: string) => void
  onTyping?: () => void
  directory: DirectoryEntry[]
  placeholder?: string
  disabled?: boolean
  disabledReason?: string
  sending?: boolean
  autoFocus?: boolean
}

export default function Composer({
  onSend, onTyping, directory, placeholder = 'Message the channel…',
  disabled, disabledReason, sending, autoFocus,
}: Props) {
  const [value, setValue] = useState('')
  const [caret, setCaret] = useState(0)
  const [highlight, setHighlight] = useState(0)
  const ref = useRef<HTMLTextAreaElement>(null)

  // The token being typed right now, if the caret sits inside an @mention.
  // Recomputed from the caret rather than tracked as state, so a click into the
  // middle of an existing line behaves the same as typing at the end.
  const mentionQuery = useMemo(() => {
    const upToCaret = value.slice(0, caret)
    const match = /(?:^|\s)@([A-Za-z0-9._-]*)$/.exec(upToCaret)
    return match ? match[1].toLowerCase() : null
  }, [value, caret])

  const suggestions = useMemo(() => {
    if (mentionQuery === null) return []
    return directory
      .filter((d) => d.handle.toLowerCase().includes(mentionQuery) ||
                     d.name.toLowerCase().includes(mentionQuery))
      // Agents first: the mention that starts work is the one worth surfacing.
      .sort((a, b) => Number(b.is_agent) - Number(a.is_agent))
      .slice(0, 6)
  }, [directory, mentionQuery])

  const slashSuggestions = useMemo(() => {
    if (!value.startsWith('/') || value.includes(' ')) return []
    return SLASH_HINTS.filter((s) => s.cmd.startsWith(value.toLowerCase()))
  }, [value])

  useEffect(() => setHighlight(0), [mentionQuery, value])

  function autosize() {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    // Grow with the content but stop at ~8 lines; past that the scroll inside
    // the box is better than a composer that eats the conversation.
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }

  useEffect(autosize, [value])

  function applyMention(entry: DirectoryEntry) {
    const upToCaret = value.slice(0, caret)
    const replaced = upToCaret.replace(/@([A-Za-z0-9._-]*)$/, `@${entry.handle} `)
    const next = replaced + value.slice(caret)
    setValue(next)
    requestAnimationFrame(() => {
      ref.current?.focus()
      const pos = replaced.length
      ref.current?.setSelectionRange(pos, pos)
      setCaret(pos)
    })
  }

  function send() {
    const body = value.trim()
    if (!body || disabled) return
    onSend(body)
    setValue('')
    requestAnimationFrame(autosize)
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setHighlight((h) => (h + 1) % suggestions.length)
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setHighlight((h) => (h - 1 + suggestions.length) % suggestions.length)
        return
      }
      if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) {
        e.preventDefault()
        applyMention(suggestions[highlight])
        return
      }
      if (e.key === 'Escape') {
        setCaret(-1)
        return
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  if (disabled) {
    return (
      <div className="border-t border-border px-4 py-3 text-sm text-muted-foreground bg-muted/40">
        {disabledReason ?? 'You cannot post here.'}
      </div>
    )
  }

  return (
    <div className="border-t border-border relative">
      {/* @mention autocomplete */}
      {suggestions.length > 0 && (
        <div className="absolute bottom-full left-3 right-3 mb-1 rounded-lg border border-border bg-card shadow-lg overflow-hidden z-20">
          {suggestions.map((entry, i) => (
            <button
              key={entry.id}
              onMouseDown={(e) => { e.preventDefault(); applyMention(entry) }}
              onMouseEnter={() => setHighlight(i)}
              className={cn(
                'w-full flex items-center gap-2.5 px-3 py-2 text-left text-sm',
                i === highlight ? 'bg-foreground text-background' : 'hover:bg-muted',
              )}
            >
              {entry.is_agent
                ? <Bot className="h-4 w-4 shrink-0 text-[#E8632A]" />
                : <span className={cn(
                    'h-4 w-4 rounded-full shrink-0',
                    entry.presence === 'active' ? 'bg-emerald-500'
                      : entry.presence === 'dnd' ? 'bg-red-500'
                      : entry.presence === 'away' ? 'bg-amber-500' : 'bg-muted-foreground/40',
                  )} />}
              <span className="font-medium">{entry.name}</span>
              <span className={cn('text-xs', i === highlight ? 'opacity-70' : 'text-muted-foreground')}>
                @{entry.handle}
              </span>
              {entry.is_agent && (
                <span className={cn('ml-auto text-[0.65rem]', i === highlight ? 'opacity-70' : 'text-[#E8632A]')}>
                  mention to assign work
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* slash command hints */}
      {slashSuggestions.length > 0 && (
        <div className="absolute bottom-full left-3 right-3 mb-1 rounded-lg border border-border bg-card shadow-lg overflow-hidden z-20">
          {slashSuggestions.map((s) => (
            <button
              key={s.cmd}
              onMouseDown={(e) => { e.preventDefault(); setValue(`${s.cmd} `); ref.current?.focus() }}
              className="w-full flex items-baseline gap-2 px-3 py-2 text-left text-sm hover:bg-muted"
            >
              <code className="app-metric text-[#E8632A]">{s.cmd}</code>
              <span className="text-xs text-muted-foreground">{s.hint}</span>
            </button>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2 px-3 py-2.5">
        <textarea
          ref={ref}
          value={value}
          rows={1}
          autoFocus={autoFocus}
          placeholder={placeholder}
          onChange={(e) => {
            setValue(e.target.value)
            setCaret(e.target.selectionStart ?? 0)
            onTyping?.()
          }}
          onKeyUp={(e) => setCaret(e.currentTarget.selectionStart ?? 0)}
          onClick={(e) => setCaret(e.currentTarget.selectionStart ?? 0)}
          onKeyDown={onKeyDown}
          className={cn(
            'flex-1 resize-none bg-background text-sm rounded-md border border-border',
            'px-3 py-2 focus:outline-none focus:ring-1 focus:ring-foreground/20',
          )}
        />
        <button
          onClick={send}
          disabled={!value.trim() || sending}
          className={cn(
            'h-9 w-9 shrink-0 rounded-md grid place-items-center transition-opacity',
            'bg-foreground text-background hover:opacity-85 disabled:opacity-30',
          )}
          title="Send (Enter)"
        >
          {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </div>

      <div className="px-3 pb-2 flex items-center gap-3 text-[0.65rem] text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <CornerDownLeft className="h-3 w-3" /> to send · Shift+Enter for a new line
        </span>
        <span className="inline-flex items-center gap-1">
          <Sparkles className="h-3 w-3" /> @an agent with a ticket key to start a run
        </span>
      </div>
    </div>
  )
}
