import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

import { Atmosphere, MarketingFooter, MarketingNav } from '@/components/marketing/Chrome'
import { useMarketingSurface } from '@/components/marketing/hooks'
import type { PipelinePhase } from '@/components/marketing/scene/pipelineTimeline'
import { Hero } from '@/components/marketing/sections/Hero'
import { Marquee } from '@/components/marketing/sections/Marquee'
import { Problem } from '@/components/marketing/sections/Problem'
import { Interstitial } from '@/components/marketing/sections/Interstitial'
import { Positioning } from '@/components/marketing/sections/Positioning'
import { Trust } from '@/components/marketing/sections/Trust'
import { Faq } from '@/components/marketing/sections/Faq'
import { ClosingCta } from '@/components/marketing/sections/ClosingCta'
import { SectionHead } from '@/components/marketing/ui'
import { SplitHeading } from '@/components/marketing/Reveal'
import { FAQS } from '@/components/marketing/content'
import { Seo } from '@/components/Seo'

/**
 * The public landing page.
 *
 * Composition note: the WebGL scene is anchored to the first viewport only and
 * stops rendering the moment it scrolls away, so everything below the fold
 * runs against an idle GPU. The hero's status readout is wired to that same
 * scene — when the packet stops at the gate, the words under the headline say
 * so. The page's whole argument is that one pause, and the two halves of the
 * page are not allowed to disagree about it.
 */
export default function LandingPage() {
  useMarketingSurface()
  useHashScroll()

  const [phase, setPhase] = useState<PipelinePhase | null>(null)
  const handlePhase = useCallback((next: PipelinePhase) => setPhase(next), [])

  return (
    <div className="mk-root relative min-h-screen bg-[var(--mk-ground)] text-[var(--mk-ink)]">
      <Seo
        title="Evolune OS — Ship agent work you can actually approve"
        description="Evolune OS runs your whole delivery loop with AI agents — plan, code, test, review — and stops at an approval gate a human controls. Every deploy is policy-checked and written to an audit log."
        path="/"
        schema={FAQ_SCHEMA}
      />
      <Atmosphere />
      <MarketingNav />

      <main className="relative">
        {/* The scene lives inside the hero now, on its own stage, rather than
            as a full-bleed layer behind the type. */}
        <Hero phase={phase} onPhase={handlePhase} />

        <Marquee />

        <Problem />

        <Interstitial
          statement="The agent was never the risky part. The unreviewed merge was."
          highlight={['unreviewed', 'merge', 'was.']}
          rise={0.44}
          caption="Autonomy without a control plane is not speed, it is unmeasured risk moved closer to production. Evolune OS does not slow the agents down — it makes the one moment that matters explicit, and writes down who owned it."
        />

        {/* "How is this different from what I already use?" is asked within the
            first minute of every evaluation. Answered here, before the reader
            is asked to trust anything else. How it works, the approval gate
            and the platform itself each now have their own page — reachable
            from the nav — rather than living mid-scroll here. */}
        <Positioning />

        <Interstitial
          statement="Ask any platform who approved last Tuesday's deploy."
          highlight={["Tuesday's", 'deploy.']}
          rise={0.56}
          caption="Under which policy, against which reviewer score, on which files, at what cost. If the answer takes an afternoon of log archaeology, that is the gap this product exists to close — and it is the question your auditor is going to ask first."
        />

        <Trust />

        {/* The FAQ used to live only on /pricing, which meant the answers to
            "do the agents get write access to my repo" and "can I self-host"
            were one navigation away from the page where those doubts actually
            occur. It is the same component and the same source copy. */}
        <section className="mk-section" id="faq">
          <div className="mk-shell">
            <SectionHead
              n="04"
              eyebrow="Questions"
              standfirst="The ones a technical buyer asks before they will point an agent at their repository."
            >
              <SplitHeading
                text="Asked and answered."
                highlight={['answered.']}
                className="mk-display text-[clamp(30px,4.4vw,56px)]"
              />
            </SectionHead>
            <div className="mt-14">
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

/**
 * FAQPage schema, generated from the same `FAQS` array the section renders, so
 * the two can never drift. Google shows these as rich results and the answer
 * engines lift them wholesale — which is worth having when the questions are
 * "can I self-host it" and "do the agents get write access to my repository".
 */
const FAQ_SCHEMA = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: FAQS.map((faq) => ({
    '@type': 'Question',
    name: faq.q,
    acceptedAnswer: { '@type': 'Answer', text: faq.a },
  })),
}

/**
 * React Router does not scroll to `#anchor` on navigation, so arriving from
 * `/pricing` on a `/#faq` link would silently land at the top of the page.
 * Deferred a frame so the target section exists in the DOM before we look for
 * it.
 */
function useHashScroll() {
  const { hash } = useLocation()

  useEffect(() => {
    if (!hash) {
      window.scrollTo(0, 0)
      return
    }
    const id = hash.slice(1)
    const frame = requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
    return () => cancelAnimationFrame(frame)
  }, [hash])
}
