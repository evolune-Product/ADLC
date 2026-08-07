import type { ReactNode } from 'react'
import { Reveal, SplitHeading } from '../Reveal'

/**
 * A full-width statement between narrative beats. No card, no icon, no button
 * — just one sentence given the room to land, over a bloom of heat.
 *
 * These exist because a page made entirely of feature grids reads as a
 * specification. The pauses are what make it read as an argument.
 */
export function Interstitial({
  statement,
  highlight,
  caption,
  /** 0–1: how far up the section the glow sits. */
  rise = 0.5,
}: {
  statement: string
  highlight?: string[]
  caption?: ReactNode
  rise?: number
}) {
  return (
    <section className="relative overflow-hidden py-[clamp(80px,10vw,150px)]">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background: `radial-gradient(52% 46% at 50% ${rise * 100}%, rgba(232, 99, 42, 0.14) 0%, transparent 70%)`,
        }}
      />
      <div className="mk-shell relative">
        <div className="mx-auto max-w-4xl text-center">
          <SplitHeading
            text={statement}
            highlight={highlight}
            className="mk-display text-[clamp(28px,5vw,64px)]"
          />
          {caption ? (
            <Reveal delay={0.2}>
              <p className="mx-auto mt-8 max-w-[62ch] text-[clamp(14px,1.5vw,17px)] leading-relaxed text-[var(--mk-ink-2)]">
                {caption}
              </p>
            </Reveal>
          ) : null}
        </div>
      </div>
    </section>
  )
}
