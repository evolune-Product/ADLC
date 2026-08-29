import { ArrowRight } from 'lucide-react'
import { Reveal, SplitHeading } from '../Reveal'
import { MkButton } from '../ui'

/**
 * The close. One instruction, one honest sentence about what the first five
 * minutes actually look like — because "book a demo" is what you write when
 * the product cannot be tried.
 */
export function ClosingCta() {
  return (
    <section className="relative overflow-hidden" style={{ paddingBlock: 'var(--mk-section-y)' }}>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(58% 60% at 50% 100%, rgba(232, 99, 42, 0.2) 0%, transparent 68%)',
        }}
      />
      {/* The horizon line the heat comes off. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-[var(--mk-ember)] to-transparent opacity-40"
      />

      <div className="mk-shell relative">
        <div className="mx-auto max-w-3xl text-center">
          <SplitHeading
            text="Put a gate in front of it."
            highlight={['gate']}
            className="mk-display text-[clamp(34px,6vw,76px)]"
          />

          <Reveal delay={0.18}>
            <p className="mx-auto mt-8 max-w-[56ch] text-[clamp(15px,1.7vw,19px)] leading-relaxed text-[var(--mk-ink-2)]">
              Sign in, install the Standard SDLC Pod from the marketplace, connect a repository.
              That gives you five agents, their skills, and a runnable governed pipeline without
              writing a line of markdown.
            </p>
          </Reveal>

          <Reveal delay={0.28}>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
              <MkButton to="/register" className="px-6 py-3 text-[15px]">
                Start free <ArrowRight className="h-4 w-4" />
              </MkButton>
              <MkButton to="/pricing" variant="ghost" className="px-6 py-3 text-[15px]">
                See pricing
              </MkButton>
            </div>
          </Reveal>

          <Reveal delay={0.36}>
            <p className="mt-6 text-[13px] text-[var(--mk-ink-3)]">
              25 runs a month, one project, your own model key. No card, and nothing expires.
            </p>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
