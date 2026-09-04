import type { CSSProperties } from 'react'
import { ArrowRight, Terminal } from 'lucide-react'
import { MkButton } from '../ui'
import { PLATFORM_FACTS } from '../content'
import { HeroStage } from '../scene/HeroStage'
import { HeroCockpit } from './HeroCockpit'
import type { PipelinePhase } from '../scene/pipelineTimeline'

/**
 * The hero: the claim, an interactive cockpit demo, then the run.
 *
 * The instrument strip at the bottom is the same four counted facts the page
 * always led with (`PLATFORM_FACTS` in `content.ts`) — the redesign changed
 * the card styling, not the numbers.
 */
export function Hero({
  phase,
  onPhase,
}: {
  phase: PipelinePhase | null
  onPhase: (phase: PipelinePhase) => void
}) {
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
    <section className="relative overflow-hidden pb-12 pt-28 sm:pt-36">
      {/* Ambient background glows */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 h-[550px] w-[800px] rounded-full blur-[140px] opacity-25"
        style={{
          background: 'radial-gradient(circle, #e8632a 0%, #8b5cf6 45%, transparent 70%)',
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute top-48 -left-20 h-[360px] w-[360px] rounded-full blur-[120px] opacity-15"
        style={{
          background: 'radial-gradient(circle, #3b82f6 0%, transparent 70%)',
        }}
      />

      <div className="mk-shell relative z-10">
        <div className="mx-auto max-w-4xl text-center">
          {/* Top announcement badge */}
          <div {...rise(0.05)} className="mk-rise flex justify-center">
            <span className="mk-mono inline-flex items-center gap-2.5 rounded-full border border-[var(--mk-hairline-lit)] bg-[var(--mk-panel-2)] px-4 py-1.5 text-[11px] uppercase tracking-[0.16em] text-[var(--mk-ink-2)] backdrop-blur-md shadow-[0_2px_10px_rgba(0,0,0,0.2)]">
              <span className="relative flex h-2 w-2">
                <span className="mk-radar-ping absolute inline-flex h-full w-full rounded-full bg-[var(--mk-ember)] opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--mk-ember)]" />
              </span>
              Agentic development platform
            </span>
          </div>

          {/* Main Headline */}
          <h1 className="mk-display mt-7 text-[clamp(36px,6.2vw,78px)] font-bold tracking-[-0.03em] leading-[1.08]">
            <span className="mk-rise block" style={{ '--mk-rise-delay': '0.12s' } as CSSProperties}>
              Ship agent work
            </span>
            <span className="mk-rise block" style={{ '--mk-rise-delay': '0.2s' } as CSSProperties}>
              you can <span className="mk-text-shimmer">actually approve.</span>
            </span>
          </h1>

          {/* Subcopy */}
          <p
            {...rise(0.38)}
            className="mk-rise mx-auto mt-6 max-w-[68ch] text-[clamp(15px,1.6vw,18px)] leading-relaxed text-[var(--mk-ink-2)]"
          >
            Evolune OS runs a ticket from plan to production through a pod of agents — and stops it
            at a gate you control. Who approves, what the reviewer had to score, which files the
            agent was allowed to touch, what the run was allowed to cost.
          </p>

          {/* CTA Buttons */}
          <div
            {...rise(0.5)}
            className="mk-rise mt-8 flex flex-wrap items-center justify-center gap-3.5"
          >
            <MkButton to="/register" className="mk-btn-luxury px-6 py-3 text-[14.5px]">
              Start free sandbox <ArrowRight className="h-4 w-4 ml-1" />
            </MkButton>
            <MkButton href="#interactive-cockpit" variant="ghost" className="px-5 py-3 text-[14.5px]">
              <Terminal className="h-4 w-4 mr-1.5 text-[var(--mk-ember-lit)]" />
              Try the live cockpit
            </MkButton>
          </div>
        </div>
      </div>

      {/* The Continuous Run Timeline Stage — the WebGL scene, full-bleed and
          first: it is the state machine the rest of the hero narrates against,
          so it earns the first look. */}
      <div {...rise(0.62)} className="mk-rise relative z-10 mt-10 w-full">
        <div className="mk-shell text-center mb-4">
          <span className="mk-mono text-[11px] uppercase tracking-[0.2em] text-[var(--mk-ink-3)]">
            Runtime delivery line &amp; stage graph
          </span>
        </div>
        <HeroStage phase={phase} onPhase={onPhase} />
      </div>

      {/* Interactive demo: a fixed sample ticket run through the pipeline, the
          gate, and the agent logs. Illustrative — see HeroCockpit.tsx. Sits
          below the scene, the concrete screen after the abstract diagram. */}
      <div id="interactive-cockpit" {...rise(0.72)} className="mk-rise relative z-10 mt-14 sm:mt-20 px-4 sm:px-6">
        <HeroCockpit />
      </div>

      {/* Instrument strip. Every value is counted from the codebase. */}
      <div {...rise(0.84)} className="mk-rise mk-shell relative z-10 mt-8">
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)] shadow-2xl sm:grid-cols-4">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="bg-[color-mix(in_srgb,var(--mk-ground)_90%,transparent)] px-6 py-4 backdrop-blur-md transition-colors hover:bg-[var(--mk-panel-2)]"
            >
              <div className="mk-readout-label">{stat.label}</div>
              <div className="mk-readout-value mt-1.5 text-[clamp(18px,2vw,24px)]">
                {stat.value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
