import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

import { Atmosphere, MarketingFooter, MarketingNav } from '@/components/marketing/Chrome'
import { useMarketingSurface } from '@/components/marketing/hooks'
import { Reveal, SplitHeading, DrawRule } from '@/components/marketing/Reveal'
import { Eyebrow } from '@/components/marketing/ui'
import {
  PricingComparison,
  PricingNotes,
  PricingPlans,
} from '@/components/marketing/sections/Pricing'
import { Faq } from '@/components/marketing/sections/Faq'
import { ClosingCta } from '@/components/marketing/sections/ClosingCta'
import { Seo } from '@/components/Seo'

/**
 * Pricing in full: the four plans, why the numbers are what they are, a
 * complete feature comparison, and the questions a technical buyer asks before
 * they will put a credit card near an agent platform.
 *
 * No WebGL here. The scene earns its cost on the landing page, where its job
 * is to explain the product; on a page someone is reading to make a purchasing
 * decision it would just be in the way.
 */
export default function PricingPage() {
  useMarketingSurface()

  const { hash } = useLocation()
  useEffect(() => {
    if (!hash) {
      window.scrollTo(0, 0)
      return
    }
    const frame = requestAnimationFrame(() => {
      document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: 'smooth' })
    })
    return () => cancelAnimationFrame(frame)
  }, [hash])

  return (
    <div className="mk-root relative min-h-screen bg-[var(--mk-ground)] text-[var(--mk-ink)]">
      <Seo
        title="Pricing — ADLC"
        description="Free forever on your own model key. Enterprise is $5,000/mo for 25 seats and unlimited runs. Runs are the meter, seats are the governance — and every run has an enforced budget cap."
        path="/pricing"
      />
      <Atmosphere />
      <MarketingNav />

      <main className="relative">
        {/* Header */}
        <section className="relative overflow-hidden pb-16 pt-36 sm:pt-44">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                'radial-gradient(54% 60% at 50% 0%, rgba(232, 99, 42, 0.16) 0%, transparent 66%)',
            }}
          />
          <div className="mk-shell relative">
            <div className="mx-auto max-w-3xl text-center">
              <div className="flex justify-center">
                <Eyebrow>Pricing</Eyebrow>
              </div>
              <SplitHeading
                as="h1"
                text="Pay for runs. Buy seats for governance."
                highlight={['governance.']}
                className="mk-display mt-6 text-[clamp(34px,5.6vw,68px)]"
              />
              <Reveal delay={0.15}>
                <p className="mx-auto mt-8 max-w-[58ch] text-[clamp(15px,1.7vw,19px)] leading-relaxed text-[var(--mk-ink-2)]">
                  A run is one ticket taken through one pod — plan, code, QA, review, approval,
                  deploy. Retries inside a run are not a second run. Start free with your own model
                  key; there is no trial clock.
                </p>
              </Reveal>
            </div>
          </div>
        </section>

        <section className="pb-24">
          <div className="mk-shell">
            <PricingPlans />
            <p className="mt-6 text-[13px] text-[var(--mk-ink-3)]">
              All prices in USD, excluding tax. Annual billing and committed-use terms on request.
            </p>
          </div>
        </section>

        {/* Why these numbers */}
        <section className="pb-24">
          <div className="mk-shell">
            <div className="max-w-3xl">
              <Eyebrow n="01">How we priced it</Eyebrow>
              <SplitHeading
                text="Here is our cost per run, so you do not have to guess."
                highlight={['guess.']}
                className="mk-display mt-6 text-[clamp(26px,3.8vw,46px)]"
              />
            </div>
            <div className="mt-12">
              <PricingNotes />
            </div>
          </div>
        </section>

        <DrawRule />

        {/* Comparison */}
        <section className="py-24">
          <div className="mk-shell">
            <div className="max-w-3xl">
              <Eyebrow n="02">Everything, side by side</Eyebrow>
              <SplitHeading
                text="What each plan actually includes."
                className="mk-display mt-6 text-[clamp(26px,3.8vw,46px)]"
              />
            </div>
            <Reveal delay={0.1} className="mt-12">
              <PricingComparison />
            </Reveal>
          </div>
        </section>

        <DrawRule />

        {/* FAQ */}
        <section className="py-24" id="faq">
          <div className="mk-shell">
            <div className="max-w-3xl">
              <Eyebrow n="03">Questions</Eyebrow>
              <SplitHeading
                text="The things you would ask on the call."
                className="mk-display mt-6 text-[clamp(26px,3.8vw,46px)]"
              />
            </div>
            <div className="mt-12">
              <Faq />
            </div>
          </div>
        </section>

        <ClosingCta />
      </main>

      <MarketingFooter />
    </div>
  )
}
