import { Atmosphere, MarketingFooter, MarketingNav } from '@/components/marketing/Chrome'
import { useMarketingSurface } from '@/components/marketing/hooks'
import { HowItWorks } from '@/components/marketing/sections/HowItWorks'
import { ClosingCta } from '@/components/marketing/sections/ClosingCta'
import { Seo } from '@/components/Seo'

/**
 * The run, step by step — its own page rather than a mid-scroll section on
 * the landing page, so it can be linked to directly and read on its own.
 * `HowItWorks` already carries its own header and layout; this file is only
 * the page shell around it.
 */
export default function HowItWorksPage() {
  useMarketingSurface()

  return (
    <div className="mk-root relative min-h-screen bg-[var(--mk-ground)] text-[var(--mk-ink)]">
      <Seo
        title="How it works — Evolune OS"
        description="One ticket, six steps, one of them a human. How a run moves from plan to production through a pod of agents, and where it stops for you."
        path="/how-it-works"
        schema={HOW_IT_WORKS_SCHEMA}
      />
      <Atmosphere />
      <MarketingNav />

      <main className="relative pt-36 sm:pt-44">
        <HowItWorks />
        <ClosingCta />
      </main>

      <MarketingFooter />
    </div>
  )
}

/**
 * HowTo + breadcrumb. The six steps are the same six the page renders and the
 * same six the pipeline actually runs — if `PIPELINE_STEPS` or the run graph
 * changes, this changes with it or the page starts describing a product that
 * does not exist.
 */
const HOW_IT_WORKS_SCHEMA = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://evoluneos.com/' },
        { '@type': 'ListItem', position: 2, name: 'How it works', item: 'https://evoluneos.com/how-it-works' },
      ],
    },
    {
      '@type': 'HowTo',
      name: 'How a run moves from ticket to production in Evolune OS',
      description:
        'One ticket taken through one pod of agents — plan, code, QA, review — stopping at a human approval gate before anything is promoted to production.',
      step: [
        { '@type': 'HowToStep', position: 1, name: 'Planner', text: 'Reads the ticket from Jira or Linear, reads the codebase memory for the project, and writes an explicit plan naming the files it intends to touch.' },
        { '@type': 'HowToStep', position: 2, name: 'Coder', text: 'Works to your skills — markdown files that define how your team builds — and opens a real pull request on GitHub or GitLab.' },
        { '@type': 'HowToStep', position: 3, name: 'QA', text: 'Runs the test suite against the diff and hands work back to the Coder on failure.' },
        { '@type': 'HowToStep', position: 4, name: 'Reviewer', text: 'Posts structured findings with severities and a 0–100 score. Advisory only — it never fails a run on its own.' },
        { '@type': 'HowToStep', position: 5, name: 'Approval gate', text: 'The run holds. A policy decides whether the approval in front of it is even sufficient: how many approvers, what reviewer score, which paths, how much cost.' },
        { '@type': 'HowToStep', position: 6, name: 'DevOps', text: 'Merges and promotes across dev, qa and prod, pausing for a fresh approval at every environment you have marked as gated. Every step is written to an immutable audit log.' },
      ],
    },
  ],
}
