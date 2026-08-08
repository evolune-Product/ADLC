import { useCallback, useRef } from 'react'
import type { CSSProperties } from 'react'
import { Code2, FlaskConical, ListChecks, Lock, Rocket, ScanEye, Server } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { PipelineCanvas } from './PipelineCanvas'
import { useMediaQuery, usePipelinePhase } from '../hooks'
import type { NodeId, NodeState, PipelinePhase } from './pipelineTimeline'

/**
 * The hero's stage: the run, on its own lit band, with every node named.
 *
 * Two decisions worth keeping:
 *
 * **The graph is not wallpaper.** It used to sit behind the headline, which
 * meant it had to stay dim enough not to fight the type — so it never got to
 * be legible. Given its own band it can be lit properly, framed properly, and
 * actually read as the product demo it is.
 *
 * **The labels are DOM, not textures.** Each node's world position is
 * projected to screen space every frame and written straight onto a positioned
 * element's `transform`. That keeps the type crisp at any DPI, lets the chips
 * use the real UI font and real icons, and — because the writes bypass React —
 * costs nothing per frame. Nothing here ever calls setState from the render
 * loop.
 */

const LABELS: Array<{ id: NodeId; icon: LucideIcon; text: string; sub: string }> = [
  { id: 'commit-0', icon: ListChecks, text: 'Planner', sub: 'plans the change' },
  { id: 'commit-1', icon: Code2, text: 'Coder', sub: 'writes it' },
  { id: 'commit-2', icon: FlaskConical, text: 'QA', sub: 'proves it' },
  { id: 'commit-3', icon: ScanEye, text: 'Reviewer', sub: 'scores it' },
  { id: 'gate', icon: Lock, text: 'Approval gate', sub: 'a human decides' },
  { id: 'env-0', icon: Server, text: 'dev', sub: '' },
  { id: 'env-1', icon: Server, text: 'qa', sub: '' },
  { id: 'env-2', icon: Rocket, text: 'prod', sub: '' },
]

/** Chips for nodes above the trunk hang above them; chips on the trunk hang
 *  below it, so nothing ever covers the line itself. */
const BELOW: ReadonlySet<NodeId> = new Set<NodeId>(['gate', 'env-0', 'env-1', 'env-2'])

export function HeroStage({
  phase,
  onPhase,
}: {
  phase: PipelinePhase | null
  onPhase: (phase: PipelinePhase) => void
}) {
  const chips = useRef<Partial<Record<NodeId, HTMLDivElement | null>>>({})

  /**
   * Eight labels pinned to a graph that is only ~360px wide collapse into an
   * unreadable pile. Below this width the chips come off the scene entirely
   * and the stages are listed underneath instead, in order, with the live one
   * lit — which is arguably the clearer reading of a pipeline anyway.
   */
  const compact = useMediaQuery('(max-width: 860px)')

  // On a phone the timeline is driven directly, because the compact stage has
  // no render loop to emit phases from. `enabled` keeps exactly one driver
  // running at a time.
  const compactPhase = usePipelinePhase(compact)
  const shown = compact ? compactPhase : phase

  const handleProject = useCallback((id: NodeId, x: number, y: number, state: NodeState) => {
    const el = chips.current[id]
    if (!el) return
    // Written directly. Routing 8 nodes × 60fps through React state would be
    // ~480 re-renders a second for a value only this element cares about.
    el.style.transform = `translate3d(${Math.round(x)}px, ${Math.round(y)}px, 0)`
    if (el.dataset.state !== state) el.dataset.state = state
  }, [])

  return (
    <div className="relative w-full">
      {compact ? (
        <CompactStage phase={compactPhase} />
      ) : (
        /* The band. Tall enough for the graph to breathe, capped so it never
           eats the fold on a laptop. */
        <div className="relative h-[clamp(240px,31vh,340px)] w-full">
          <PipelineCanvas
            className="absolute inset-0"
            onPhase={onPhase}
            onProject={handleProject}
          />

          {/* Label overlay. Chips are positioned from the origin and centred by
              an inner transform, so the outer transform stays free for the
              projected position. */}
          <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
            {LABELS.map((label) => (
              <div
                key={label.id}
                ref={(el) => {
                  chips.current[label.id] = el
                }}
                data-state="idle"
                className="absolute left-0 top-0 will-change-transform"
                style={{ transform: 'translate3d(-9999px, -9999px, 0)' }}
              >
                <NodeChip {...label} below={BELOW.has(label.id)} />
              </div>
            ))}
          </div>

          {/* Edge fades, so the line runs out of frame instead of stopping at
              a hard border. */}
          <div className="pointer-events-none absolute inset-y-0 left-0 w-24 bg-gradient-to-r from-[var(--mk-ground)] to-transparent" />
          <div className="pointer-events-none absolute inset-y-0 right-0 w-24 bg-gradient-to-l from-[var(--mk-ground)] to-transparent" />
        </div>
      )}

      {/* The run's state, in words. Not a decorative ticker: this text changes
          because the run behind it changed. */}
      <div className="mt-3 flex justify-center px-4">
        <PhaseReadout phase={shown} />
      </div>
    </div>
  )
}

/**
 * The run, for a phone.
 *
 * A 19-by-3 diagram cannot be squeezed into a portrait frame and stay legible
 * — rotating it upright only turned a sliver into a thread. So narrow screens
 * get a purpose-built vertical timeline instead of a shrunken copy of the
 * desktop one. It is driven by the same schedule, so it names the same stage at
 * the same moment, and it means **three.js is never downloaded on a phone at
 * all** — about 250 kB saved on exactly the devices least able to afford it.
 */
function CompactStage({ phase }: { phase: PipelinePhase | null }) {
  const activeIndex = phase?.node ? LABELS.findIndex((l) => l.id === phase.node) : -1

  return (
    <ol className="mk-shell relative space-y-0.5 py-2">
      {LABELS.map((label, i) => {
        const isActive = i === activeIndex
        const isPast = activeIndex > -1 && i < activeIndex
        const held = isActive && phase?.kind === 'held'
        const isGate = label.id === 'gate'
        const last = i === LABELS.length - 1

        const tone = held
          ? 'var(--mk-hold)'
          : isActive
            ? 'var(--mk-amber)'
            : isPast
              ? 'var(--mk-pass)'
              : 'var(--mk-ink-3)'

        return (
          <li key={label.id} className="relative flex items-center gap-3 pl-1">
            {/* The line work runs down. Stops at the last step rather than
                trailing off past it. */}
            {last ? null : (
              <span
                aria-hidden="true"
                className="absolute left-[15px] top-1/2 h-full w-px"
                style={{
                  background: isPast
                    ? 'var(--mk-pass)'
                    : 'linear-gradient(to bottom, var(--mk-hairline-lit), var(--mk-hairline))',
                  opacity: isPast ? 0.5 : 1,
                }}
              />
            )}

            <span
              className={cn(
                'relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-colors duration-300',
                isGate ? 'border-2' : 'border',
              )}
              style={{
                borderColor: tone,
                backgroundColor: 'var(--mk-ground)',
                color: tone,
              }}
            >
              <label.icon className="h-3.5 w-3.5" strokeWidth={2.25} />
            </span>

            <span className="flex min-w-0 flex-1 items-baseline justify-between gap-3 py-1.5">
              <span
                className="mk-mono text-[11.5px] uppercase tracking-[0.12em] transition-colors duration-300"
                style={{ color: tone }}
              >
                {label.text}
              </span>
              {label.sub ? (
                <span className="truncate text-[11.5px] text-[var(--mk-ink-3)]">{label.sub}</span>
              ) : (
                <span className="mk-mono text-[10.5px] uppercase tracking-[0.12em] text-[var(--mk-ink-3)]">
                  environment
                </span>
              )}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

function NodeChip({
  icon: Icon,
  text,
  sub,
  below,
}: {
  icon: LucideIcon
  text: string
  sub: string
  below: boolean
}) {
  return (
    <div
      className={cn(
        'group/chip absolute left-1/2 flex -translate-x-1/2 flex-col items-center gap-1.5',
        below ? 'top-3' : 'bottom-3',
      )}
    >
      {below ? <Tick /> : null}

      <div
        className={cn(
          'flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 backdrop-blur-sm transition-colors duration-300',
          // Driven by [data-state] on the positioned ancestor, so the colour
          // change costs one attribute write rather than a React render.
          'border-[var(--mk-hairline-lit)] bg-[color-mix(in_srgb,var(--mk-ground)_82%,transparent)] text-[var(--mk-ink-3)]',
          '[[data-state=active]_&]:border-[var(--mk-amber)] [[data-state=active]_&]:text-[var(--mk-amber)]',
          '[[data-state=passed]_&]:border-[color-mix(in_srgb,var(--mk-pass)_45%,transparent)] [[data-state=passed]_&]:text-[var(--mk-pass)]',
          '[[data-state=held]_&]:border-[var(--mk-hold)] [[data-state=held]_&]:text-[var(--mk-hold)]',
        )}
      >
        <Icon className="h-3 w-3 shrink-0" strokeWidth={2.25} />
        <span className="mk-mono text-[10.5px] uppercase tracking-[0.12em]">{text}</span>
      </div>

      {sub ? (
        <span className="hidden text-[11px] leading-none text-[var(--mk-ink-3)] opacity-70 lg:block">
          {sub}
        </span>
      ) : null}

      {below ? null : <Tick />}
    </div>
  )
}

/** The hairline that ties a chip to the node it names. */
function Tick() {
  return (
    <span className="h-3 w-px bg-gradient-to-b from-[var(--mk-hairline-lit)] to-transparent" />
  )
}

const KIND_COLOR: Record<PipelinePhase['kind'], string> = {
  running: 'var(--mk-amber)',
  held: 'var(--mk-hold)',
  passed: 'var(--mk-pass)',
  idle: 'var(--mk-ink-3)',
}

function PhaseReadout({ phase }: { phase: PipelinePhase | null }) {
  // Before the scene boots — and permanently, for reduced-motion and no-WebGL
  // visitors — the readout shows the state the static diagram is drawn in, so
  // the words and the picture never disagree.
  const current: PipelinePhase = phase ?? {
    label: 'HELD · awaiting human approval',
    kind: 'held',
    activity: 0,
  }
  const color = KIND_COLOR[current.kind]

  return (
    <div
      className="mk-glass flex items-center gap-3 rounded-full px-4 py-2"
      role="status"
      aria-live="off"
    >
      <span
        className="h-2 w-2 shrink-0 rounded-full"
        style={{ backgroundColor: color, boxShadow: `0 0 12px ${color}` } as CSSProperties}
      />
      <span className="mk-mono text-[11.5px] uppercase tracking-[0.14em]" style={{ color }}>
        {current.label}
      </span>
    </div>
  )
}
