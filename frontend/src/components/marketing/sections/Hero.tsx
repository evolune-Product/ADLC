import type { CSSProperties } from 'react'
import { ArrowRight } from 'lucide-react'
import { MkButton } from '../ui'
import { PLATFORM_FACTS } from '../content'
import type { PipelinePhase } from '../scene/DeliveryLine'

/**
 * The hero opens on the product's actual argument rather than a description of
 * it: the scene behind the type is a run moving through a pod, and the readout
 * under the headline is wired to that same state machine — when the packet
 * stops at the gate, the readout goes red and says so.
 */
export function Hero({ phase }: { phase: PipelinePhase | null }) {
  /**
   * CSS-driven, not JS-driven. The headline below is this page's Largest
   * Contentful Paint element; animating it from a motion library means it sits
   * at opacity 0 in the served HTML until the bundle hydrates. As a plain CSS
   * animation it starts at first paint, and `.mk-rise` no-ops under reduced
   * motion at the stylesheet level, so no JS check is needed here either.
   */
  const rise = (delay: number) => ({
    className: 'mk-rise',
    style: { '--mk-rise-delay': `${delay}s` } as CSSProperties,
  })

  const stats = [
    { label: 'Agent roles per pod', value: String(PLATFORM_FACTS.agentRoles) },
    { label: 'Skills & templates', value: String(PLATFORM_FACTS.templates) },
    { label: 'Model providers', value: String(PLATFORM_FACTS.modelProviders) },
    { label: 'API endpoints', value: String(PLATFORM_FACTS.apiEndpoints) },
  ]

  return (
    <section className="relative flex min-h-[100svh] flex-col justify-center pb-20 pt-32 sm:pt-36">
      {/* Scrim. The headline sits directly in front of the core, which is the
          composition we want — but type over a bloom-lit sphere loses contrast
          fast, so a soft radial darkens just the area behind the words without
          ever reading as a box. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-[12%] h-[64%]"
        style={{
          background:
            'radial-gradient(46% 52% at 50% 42%, var(--mk-hero-scrim-in) 0%, var(--mk-hero-scrim-mid) 46%, var(--mk-hero-scrim-out) 78%)',
        }}
      />

      <div className="mk-shell relative z-10">
        <div className="mx-auto max-w-4xl text-center">
          <div {...rise(0.05)} className="mk-rise flex justify-center">
            <span className="mk-mono inline-flex items-center gap-2.5 rounded-full border border-[var(--mk-hairline-lit)] px-3.5 py-1.5 text-[11px] uppercase tracking-[0.16em] text-[var(--mk-ink-2)]">
              <span className="mk-animate-breathe h-1.5 w-1.5 rounded-full bg-[var(--mk-ember)]" />
              Agentic development platform
            </span>
          </div>

          <h1 className="mk-display mt-8 text-[clamp(40px,8vw,98px)]">
            <span className="mk-rise block" style={{ '--mk-rise-delay': '0.12s' } as CSSProperties}>
              Ship agent work
            </span>
            <span className="mk-rise block" style={{ '--mk-rise-delay': '0.2s' } as CSSProperties}>
              you can <span className="mk-lit">actually approve.</span>
            </span>
          </h1>

          <p
            {...rise(0.38)}
            className="mk-rise mx-auto mt-8 max-w-[58ch] text-[clamp(15px,1.7vw,19px)] leading-relaxed text-[var(--mk-ink-2)]"
          >
            ADLC runs a ticket from plan to production through a pod of agents — and stops it at a
            gate you control. Who approves, what the reviewer had to score, which files the agent
            was allowed to touch, what the run was allowed to cost.
          </p>

          {/* The scene's state machine, in words. Not a decorative ticker: this
              text changes because the run behind it changed. */}
          <div {...rise(0.5)} className="mk-rise mx-auto mt-9 flex justify-center">
            <PhaseReadout phase={phase} />
          </div>

          <div {...rise(0.58)} className="mk-rise mt-9 flex flex-wrap items-center justify-center gap-3">
            <MkButton to="/register">
              Start free <ArrowRight className="h-4 w-4" />
            </MkButton>
            <MkButton href="#how-it-works" variant="ghost">
              See how a run works
            </MkButton>
          </div>

          <p {...rise(0.66)} className="mk-rise mt-5 text-[13px] text-[var(--mk-ink-3)]">
            25 runs a month on the free tier. Bring your own model key — no card, no trial clock.
          </p>
        </div>
      </div>

      {/* Instrument strip. Every value is counted from the codebase. */}
      <div {...rise(0.76)} className="mk-rise mk-shell relative z-10 mt-16">
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)] sm:grid-cols-4">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="bg-[color-mix(in_srgb,var(--mk-ground)_78%,transparent)] px-5 py-5 backdrop-blur-sm"
            >
              <div className="mk-readout-label">{stat.label}</div>
              <div className="mk-readout-value mt-2 text-[clamp(20px,2.4vw,28px)]">{stat.value}</div>
            </div>
          ))}
        </div>
      </div>

      <div
        {...rise(0.9)}
        className="mk-rise pointer-events-none absolute inset-x-0 bottom-5 flex justify-center"
        aria-hidden="true"
      >
        <div className="flex flex-col items-center gap-2">
          <span className="mk-mono text-[10.5px] uppercase tracking-[0.28em] text-[var(--mk-ink-3)]">
            Follow the run
          </span>
          <span className="relative h-10 w-px overflow-hidden bg-[var(--mk-hairline-lit)]">
            <span className="absolute inset-x-0 top-0 h-4 animate-[mk-scroll-cue_2.4s_ease-in-out_infinite] bg-gradient-to-b from-transparent via-[var(--mk-ember)] to-transparent" />
          </span>
        </div>
      </div>
    </section>
  )
}

const KIND_COLOR: Record<PipelinePhase['kind'], string> = {
  running: 'var(--mk-amber)',
  held: 'var(--mk-hold)',
  passed: 'var(--mk-pass)',
  idle: 'var(--mk-ink-3)',
}

function PhaseReadout({ phase }: { phase: PipelinePhase | null }) {
  // Before the scene boots — and permanently, for reduced-motion and
  // no-WebGL visitors — the readout shows the state the static diagram is
  // drawn in, so the words and the picture never disagree.
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
        style={{ backgroundColor: color, boxShadow: `0 0 12px ${color}` }}
      />
      <span
        className="mk-mono text-[11.5px] uppercase tracking-[0.14em]"
        style={{ color }}
      >
        {current.label}
      </span>
    </div>
  )
}
