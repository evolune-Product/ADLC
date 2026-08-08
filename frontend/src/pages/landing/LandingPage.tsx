import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

import { Atmosphere, MarketingFooter, MarketingNav } from '@/components/marketing/Chrome'
import { useMarketingSurface } from '@/components/marketing/hooks'
import { PipelineCanvas } from '@/components/marketing/scene/PipelineCanvas'
import type { PipelinePhase } from '@/components/marketing/scene/DeliveryLine'
import { Hero } from '@/components/marketing/sections/Hero'
import { Problem } from '@/components/marketing/sections/Problem'
import { Interstitial } from '@/components/marketing/sections/Interstitial'
import { HowItWorks } from '@/components/marketing/sections/HowItWorks'
import { TheGate } from '@/components/marketing/sections/TheGate'
import { Platform } from '@/components/marketing/sections/Platform'
import { PricingSection } from '@/components/marketing/sections/Pricing'
import { Trust } from '@/components/marketing/sections/Trust'
import { ClosingCta } from '@/components/marketing/sections/ClosingCta'

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
      <Atmosphere />
      <MarketingNav />

      {/* The scene sits behind the first screen only. */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[100svh] overflow-hidden">
        <PipelineCanvas className="absolute inset-0" onPhase={handlePhase} />
        {/* Horizon: the scene dissolves into the page instead of ending at an
            edge. */}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-64 bg-gradient-to-b from-transparent to-[var(--mk-ground)]" />
      </div>

      <main className="relative">
        <Hero phase={phase} />

        <Problem />

        <Interstitial
          statement="The agent was never the risky part. The unreviewed merge was."
          highlight={['unreviewed', 'merge', 'was.']}
          rise={0.44}
          caption="Autonomy without a control plane is not speed, it is unmeasured risk moved closer to production. ADLC does not slow the agents down — it makes the one moment that matters explicit, and writes down who owned it."
        />

        <HowItWorks />
        <TheGate />

        <Interstitial
          statement="Ask any platform who approved last Tuesday's deploy."
          highlight={["Tuesday's", 'deploy.']}
          rise={0.56}
          caption="Under which policy, against which reviewer score, on which files, at what cost. If the answer takes an afternoon of log archaeology, that is the gap this product exists to close — and it is the question your auditor is going to ask first."
        />

        <Platform />
        <PricingSection />
        <Trust />
        <ClosingCta />
      </main>

      <MarketingFooter />
    </div>
  )
}

/**
 * React Router does not scroll to `#anchor` on navigation, so arriving from
 * `/pricing` on a `/#the-gate` link would silently land at the top of the page.
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
