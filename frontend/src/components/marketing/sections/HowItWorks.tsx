import { cn } from '@/lib/utils'
import { Reveal, SplitHeading, DrawRule } from '../Reveal'
import { Eyebrow } from '../ui'
import { PIPELINE_STEPS } from '../content'

/**
 * The run, step by step.
 *
 * Laid out as a vertical line with the six stages hung off it, because the
 * shape of the list is the shape of the pipeline. Step 05 — the gate — breaks
 * the pattern deliberately: it is the one step that is not an agent, and the
 * layout should say so before the copy does.
 */
export function HowItWorks() {
  return (
    <section className="mk-section" id="how-it-works">
      <div className="mk-shell">
        <div className="max-w-3xl">
          <Eyebrow n="02">How a run works</Eyebrow>
          <SplitHeading
            text="One ticket. Six steps. One of them is a person."
            highlight={['person.']}
            className="mk-display mt-6 text-[clamp(30px,4.6vw,58px)]"
          />
          <Reveal delay={0.15}>
            <p className="mt-7 max-w-[62ch] text-[clamp(15px,1.6vw,18px)] leading-relaxed text-[var(--mk-ink-2)]">
              Every step streams live over a websocket, and every step writes to the audit log. You
              can watch a run happen, or you can read exactly what happened three months later —
              they are the same record.
            </p>
          </Reveal>
        </div>

        <DrawRule className="mt-16" />

        <ol className="relative mt-4">
          {/* The line the pipeline hangs from. Stops short of the last item so
              it reads as a run that ended rather than one that trails off. */}
          <span
            aria-hidden="true"
            className="absolute left-[19px] top-8 bottom-16 hidden w-px bg-gradient-to-b from-[var(--mk-hairline-lit)] via-[var(--mk-hairline-lit)] to-transparent sm:block"
          />

          {PIPELINE_STEPS.map((step, i) => {
            const isGate = 'isGate' in step && step.isGate
            return (
              <Reveal as="li" key={step.n} delay={i * 0.05} className="relative py-8 sm:pl-16">
                <span
                  aria-hidden="true"
                  className={cn(
                    'absolute left-0 top-9 hidden h-10 w-10 items-center justify-center rounded-full border sm:flex',
                    isGate
                      ? 'border-[var(--mk-ember)] bg-[color-mix(in_srgb,var(--mk-ember)_16%,var(--mk-ground))]'
                      : 'border-[var(--mk-hairline-lit)] bg-[var(--mk-ground)]',
                  )}
                >
                  <span
                    className={cn(
                      'mk-mono text-[11px] font-semibold',
                      isGate ? 'text-[var(--mk-ember-lit)]' : 'text-[var(--mk-ink-3)]',
                    )}
                  >
                    {step.n}
                  </span>
                </span>

                <div
                  className={cn(
                    'grid gap-4 sm:grid-cols-[160px_1fr] sm:gap-10',
                    isGate &&
                      'rounded-2xl border border-[color-mix(in_srgb,var(--mk-ember)_30%,transparent)] bg-[color-mix(in_srgb,var(--mk-ember)_5%,transparent)] p-6 sm:p-7',
                  )}
                >
                  <div>
                    <div
                      className={cn(
                        'mk-mono text-[11px] uppercase tracking-[0.18em]',
                        isGate ? 'text-[var(--mk-ember-lit)]' : 'text-[var(--mk-ink-3)]',
                      )}
                    >
                      {step.role}
                    </div>
                    {isGate ? (
                      <div className="mk-mono mt-2 inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-[var(--mk-hold)]">
                        <span className="mk-animate-blink h-1.5 w-1.5 rounded-full bg-[var(--mk-hold)]" />
                        blocking
                      </div>
                    ) : null}
                  </div>

                  <div>
                    <h3 className="mk-display text-[clamp(19px,2.2vw,26px)] leading-tight">
                      {step.title}
                    </h3>
                    <p className="mt-3 max-w-[64ch] text-[15px] leading-relaxed text-[var(--mk-ink-2)]">
                      {step.body}
                    </p>
                  </div>
                </div>
              </Reveal>
            )
          })}
        </ol>
      </div>
    </section>
  )
}
