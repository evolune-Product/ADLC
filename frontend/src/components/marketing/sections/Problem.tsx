import { Reveal, SplitHeading } from '../Reveal'
import { Eyebrow } from '../ui'
import { MARKET_FACTS } from '../content'

/**
 * The case for the category, argued entirely with other people's numbers.
 *
 * Each figure renders its own attribution. A statistic without a source on a
 * vendor's website is decoration, and the buyer this page is written for knows
 * that better than anyone.
 */
export function Problem() {
  return (
    <section className="mk-section" id="why-now">
      <div className="mk-shell">
        <div className="max-w-3xl">
          <Eyebrow n="01">Why this, why now</Eyebrow>
          <SplitHeading
            text="Everyone shipped the agents. Nobody shipped the brakes."
            highlight={['brakes.']}
            className="mk-display mt-6 text-[clamp(30px,4.6vw,58px)]"
          />
          <Reveal delay={0.15}>
            <p className="mt-7 max-w-[64ch] text-[clamp(15px,1.6vw,18px)] leading-relaxed text-[var(--mk-ink-2)]">
              Adoption is finished — the argument about whether AI writes production code is over.
              What arrived instead is a review backlog, an audit trail nobody can produce, and a
              model bill nobody can attribute. The constraint moved downstream, and the tooling
              did not move with it.
            </p>
          </Reveal>
        </div>

        <div className="mt-16 grid gap-px overflow-hidden rounded-2xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)] sm:grid-cols-2 lg:grid-cols-4">
          {MARKET_FACTS.map((fact, i) => (
            <Reveal
              key={fact.label}
              delay={i * 0.08}
              className="flex flex-col bg-[var(--mk-panel)] p-6"
            >
              <div className="mk-readout-value text-[clamp(28px,3.6vw,42px)] text-[var(--mk-ember-lit)]">
                {fact.value}
              </div>
              <div className="mt-3 text-[15px] font-semibold leading-snug text-[var(--mk-ink)]">
                {fact.label}
              </div>
              <p className="mt-3 flex-1 text-[13.5px] leading-relaxed text-[var(--mk-ink-2)]">
                {fact.note}
              </p>
              <div className="mk-mono mt-5 text-[10.5px] uppercase tracking-[0.14em] text-[var(--mk-ink-3)]">
                {fact.source}
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
