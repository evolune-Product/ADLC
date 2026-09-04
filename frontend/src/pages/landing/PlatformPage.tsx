import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Atmosphere, MarketingFooter, MarketingNav } from '@/components/marketing/Chrome'
import { useMarketingSurface } from '@/components/marketing/hooks'
import { Platform } from '@/components/marketing/sections/Platform'
import { ClosingCta } from '@/components/marketing/sections/ClosingCta'
import { Seo } from '@/components/Seo'

/**
 * What the platform is made of, on its own page — skills, codebase memory,
 * model freedom, and everything it plugs into. Answering the two questions
 * every technical evaluator asks (which models, what does it plug into) is
 * worth a real URL, not just a scroll position on the landing page.
 */
export default function PlatformPage() {
  useMarketingSurface()

  // React Router does not scroll to `#anchor` on navigation, so a footer
  // link like `/platform#models` would silently land at the top of the page.
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
        title="Platform — Evolune OS"
        description="Skills as markdown, codebase memory, and no single-model dependency — model choice is per agent, across five providers or your own local endpoint. What Evolune OS is made of, and what it plugs into."
        path="/platform"
        schema={PLATFORM_SCHEMA}
      />
      <Atmosphere />
      <MarketingNav />

      <main className="relative pt-36 sm:pt-44">
        <Platform />
        <ClosingCta />
      </main>

      <MarketingFooter />
    </div>
  )
}

/**
 * The provider and integration names here are the same lists `content.ts`
 * declares and the page renders. "Which models does it support" and "what does
 * it plug into" are the two questions an evaluator asks first and the two an
 * answer engine is most often asked to summarise, so they are stated as
 * quotable facts rather than left implicit in a grid.
 */
const PLATFORM_SCHEMA = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://evoluneos.com/' },
        { '@type': 'ListItem', position: 2, name: 'Platform', item: 'https://evoluneos.com/platform' },
      ],
    },
    {
      '@type': 'FAQPage',
      mainEntity: [
        {
          '@type': 'Question',
          name: 'Which AI models does Evolune OS support?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Model choice is per agent, not per workspace: Anthropic (Claude, the default), OpenAI, Azure OpenAI for enterprise tenancy, any OpenAI-compatible /v1 endpoint, and local Ollama for air-gapped installs. Your Planner and your Reviewer need not be the same model or the same vendor.',
          },
        },
        {
          '@type': 'Question',
          name: 'Does Evolune OS resell inference or mark up model tokens?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'No. There is no bundled model quota and no markup. You connect a vendor you already pay; tokens are billed by that vendor on your own contract under your own data-processing terms. Every call is metered with its token counts and costed in integer millicents for attribution only.',
          },
        },
        {
          '@type': 'Question',
          name: 'What does Evolune OS integrate with?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'GitHub and GitLab for repositories, pull requests and merges; Jira and Linear for ticket sync into runs; Slack for approval alerts; and HMAC-signed, replay-safe webhooks for automation. There is also a scoped public API and an MCP server so other agents can list runs, start them and see what is waiting at the gate.',
          },
        },
        {
          '@type': 'Question',
          name: 'Can Evolune OS run self-hosted or air-gapped?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Yes, on the Enterprise plan — self-hosted or in your own VPC, against stock PostgreSQL 15. No external vendor is load-bearing: embeddings fall back to a local deterministic embedder, models can be a local Ollama, and with no payment processor configured the platform bills by invoice.',
          },
        },
        {
          '@type': 'Question',
          name: 'Does the approval policy work the same across GitHub and GitLab, and across model vendors?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Yes. Approval policy — minimum approvers, reviewer-score thresholds, protected paths and branches, and per-run cost caps — is enforced by the same policy engine regardless of which repository host the change is on or which model vendor the agent that wrote it used. A team on GitHub today and GitLab tomorrow, or Claude for one agent role and a local Ollama for another, does not reconfigure governance to do it.',
          },
        },
      ],
    },
  ],
}
