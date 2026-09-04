import { Atmosphere, MarketingFooter, MarketingNav } from '@/components/marketing/Chrome'
import { useMarketingSurface } from '@/components/marketing/hooks'
import { TheGate } from '@/components/marketing/sections/TheGate'
import { ClosingCta } from '@/components/marketing/sections/ClosingCta'
import { Seo } from '@/components/Seo'

/**
 * The approval gate, on its own page. `TheGate` is the playable policy demo —
 * a faithful port of `policy_service`, not a mock-up — and it earns a page a
 * visitor can land on directly from a search result or a shared link, rather
 * than only being reachable by scrolling past everything else first.
 */
export default function TheGatePage() {
  useMarketingSurface()

  return (
    <div className="mk-root relative min-h-screen bg-[var(--mk-ground)] text-[var(--mk-ink)]">
      <Seo
        title="The approval gate — Evolune OS"
        description="An approval that anyone can give is not a control. Toggle real policy rules against a sample run and watch a deploy that was about to happen stop happening."
        path="/the-gate"
        schema={GATE_SCHEMA}
      />
      <Atmosphere />
      <MarketingNav />

      <main className="relative pt-36 sm:pt-44">
        <TheGate />
        <ClosingCta />
      </main>

      <MarketingFooter />
    </div>
  )
}

/**
 * The five policy rules named here are the five `TheGate` actually evaluates,
 * which are in turn a faithful port of `policy_service`. Stating them as
 * structured Q&A is what lets an answer engine quote the specific rule rather
 * than paraphrasing "it has approvals".
 */
const GATE_SCHEMA = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://evoluneos.com/' },
        { '@type': 'ListItem', position: 2, name: 'The approval gate', item: 'https://evoluneos.com/the-gate' },
      ],
    },
    {
      '@type': 'FAQPage',
      mainEntity: [
        {
          '@type': 'Question',
          name: 'What is an approval gate in an agentic SDLC platform?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'A point where an agent-generated change stops and cannot proceed to production until a human approves it and a policy confirms that approval was sufficient. In Evolune OS the run holds at the gate rather than failing, so the work survives and the reason it was held is recorded.',
          },
        },
        {
          '@type': 'Question',
          name: 'What rules can an approval policy enforce?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Minimum number of approvers, a minimum reviewer score (0–100, computed as 100 minus a weighted severity penalty), blocking on unresolved findings at or above a chosen severity, protected file paths the agent may not modify, and a maximum cost per run. Policies scope per environment, so dev can be open while production requires two names.',
          },
        },
        {
          '@type': 'Question',
          name: 'Why is a human clicking approve not enough on its own?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'An approval that anyone can give is not a control. Without a policy, one click from any account releases a deploy regardless of reviewer score, outstanding high-severity findings, which files were touched, or what the run cost. The policy is what makes the click accountable.',
          },
        },
        {
          '@type': 'Question',
          name: 'Does the default policy block deploys out of the box?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'No. The default policy ships permissive — one approver, no reviewer gate. Governance a team did not ask for, blocking their first run, is how a pilot dies. Tightening it is an explicit act.',
          },
        },
      ],
    },
  ],
}
