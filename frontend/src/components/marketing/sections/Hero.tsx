import type { CSSProperties } from 'react'
import { ArrowRight } from 'lucide-react'
import { MkButton } from '../ui'
import { PLATFORM_FACTS } from '../content'
import { HeroStage } from '../scene/HeroStage'
import type { PipelinePhase } from '../scene/pipelineTimeline'

/**
 * The hero: the claim, then the run.
 *
 * The scene used to sit *behind* this copy, which meant it had to stay dim
 * enough not to fight the headline — so it never earned its place, and its
 * nodes could not be labelled without printing over the type. Giving it its
 * own band under the copy costs a little vertical space and buys a diagram
 * that is lit properly, framed properly, and names every stage.
 */
export function Hero({
  phase,
  onPhase,
}: {
  phase: PipelinePhase | null
  onPhase: (phase: PipelinePhase) => void
}) {
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
    <section className="relative pb-8 pt-24 sm:pt-28">
      {/* A single wash of heat behind the copy, so the type never sits on a
          flat black field. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-[70%]"
        style={{
          background:
            'radial-gradient(46% 46% at 50% 22%, rgba(232, 99, 42, 0.1) 0%, transparent 72%)',
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

          <h1 className="mk-display mt-6 text-[clamp(34px,6vw,72px)]">
            <span className="mk-rise block" style={{ '--mk-rise-delay': '0.12s' } as CSSProperties}>
              Ship agent work
            </span>
            <span className="mk-rise block" style={{ '--mk-rise-delay': '0.2s' } as CSSProperties}>
              you can <span className="mk-lit">actually approve.</span>
            </span>
          </h1>

          <p
            {...rise(0.38)}
            className="mk-rise mx-auto mt-5 max-w-[66ch] text-[clamp(14.5px,1.5vw,17px)] leading-relaxed text-[var(--mk-ink-2)]"
          >
            ADLC runs a ticket from plan to production through a pod of agents — and stops it at a
            gate you control. Who approves, what the reviewer had to score, which files the agent
            was allowed to touch, what the run was allowed to cost.
          </p>

          <div
            {...rise(0.5)}
            className="mk-rise mt-6 flex flex-wrap items-center justify-center gap-3"
          >
            <MkButton to="/register">
              Start free <ArrowRight className="h-4 w-4" />
            </MkButton>
            <MkButton href="#how-it-works" variant="ghost">
              See how a run works
            </MkButton>
          </div>
        </div>
      </div>

      {/* The run itself, on its own stage. Full-bleed: the line should leave
          the frame rather than stop inside a column. */}
      <div {...rise(0.62)} className="mk-rise relative z-10 mt-6 w-full">
        <HeroStage phase={phase} onPhase={onPhase} />
      </div>

      {/* Instrument strip. Every value is counted from the codebase. */}
      <div {...rise(0.78)} className="mk-rise mk-shell relative z-10 mt-6">
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)] sm:grid-cols-4">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="bg-[color-mix(in_srgb,var(--mk-ground)_78%,transparent)] px-5 py-3.5 backdrop-blur-sm"
            >
              <div className="mk-readout-label">{stat.label}</div>
              <div className="mk-readout-value mt-1.5 text-[clamp(19px,2.2vw,26px)]">
                {stat.value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
