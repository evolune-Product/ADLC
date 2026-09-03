import { ArrowRight, CheckCircle2, Sparkles } from 'lucide-react'
import { Reveal, SplitHeading } from '../Reveal'
import { MkButton } from '../ui'

/**
 * The close. One instruction, one honest sentence about what the first five
 * minutes actually look like — because "book a demo" is what you write when
 * the product cannot be tried.
 */
export function ClosingCta() {
  return (
    <section className="relative overflow-hidden py-24 sm:py-32">
      {/* Radiant horizon flare */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            'radial-gradient(ellipse 70% 60% at 50% 100%, rgba(232, 99, 42, 0.25) 0%, rgba(139, 92, 246, 0.1) 40%, transparent 75%)',
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-[var(--mk-ember)] to-transparent opacity-60 shadow-[0_0_15px_#e8632a]"
      />

      <div className="mk-shell relative">
        <div className="mx-auto max-w-3xl text-center">
          <div className="flex justify-center mb-6">
            <span className="mk-mono inline-flex items-center gap-2 rounded-full border border-[var(--mk-hairline)] bg-[var(--mk-panel-2)] px-4 py-1.5 text-xs text-[var(--mk-ember-lit)] backdrop-blur-md">
              <Sparkles className="h-3.5 w-3.5" />
              Free sandbox, no card required
            </span>
          </div>

          <SplitHeading
            text="Ship at autonomous speed. Keep the human in the loop."
            highlight={['human', 'loop.']}
            className="mk-display text-[clamp(34px,5.8vw,72px)] font-bold tracking-tight leading-[1.1]"
          />

          <Reveal delay={0.18}>
            <p className="mx-auto mt-6 max-w-[56ch] text-[clamp(15px,1.6vw,18px)] leading-relaxed text-[var(--mk-ink-2)]">
              Sign in, install the Standard SDLC Pod from the marketplace, and connect a GitHub or
              GitLab repository. That gives you five agents, their skills, and a runnable governed
              pipeline without writing a line of markdown.
            </p>
          </Reveal>

          <Reveal delay={0.28}>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-3.5">
              <MkButton to="/register" className="mk-btn-luxury px-7 py-3.5 text-[15px]">
                Start free <ArrowRight className="h-4 w-4 ml-1.5" />
              </MkButton>
              <MkButton to="/pricing" variant="ghost" className="px-6 py-3.5 text-[15px]">
                View pricing
              </MkButton>
            </div>
          </Reveal>

          <Reveal delay={0.36}>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-6 text-xs text-[var(--mk-ink-3)] mk-mono">
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-[var(--mk-pass)]" /> 25 free runs a month
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-[var(--mk-pass)]" /> No card, nothing expires
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-[var(--mk-pass)]" /> Your own model key
              </span>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
