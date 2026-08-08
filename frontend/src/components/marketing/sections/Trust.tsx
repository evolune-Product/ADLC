import { Reveal, SplitHeading } from '../Reveal'
import { Eyebrow } from '../ui'

/**
 * The security and honesty section.
 *
 * The last block is deliberately about what is *not* built. A page that only
 * claims strengths gets read as marketing; one that names its gaps gets read
 * as a spec — and the buyer this product is for will find the gaps in the
 * first week regardless.
 */

const POSTURE = [
  {
    title: 'Credentials are encrypted at rest',
    body: 'OAuth tokens and bring-your-own model keys are sealed with Fernet before they touch the database. API keys are stored as SHA-256 hashes behind a visible prefix, so a database dump does not hand over anyone’s repositories.',
  },
  {
    title: 'Scoped keys, and approval is its own scope',
    body: 'Public API keys carry explicit scopes. `runs:approve` is separate from `runs:write` on purpose: a CI job that can start work should not be able to sign off on it.',
  },
  {
    title: 'Every decision is written down',
    body: 'Who approved, under which policy, against which reviewer score, at what time, on which environment. Retention is configurable and enforced by a nightly job — a documented policy nobody executes is an audit finding.',
  },
  {
    title: 'It can run entirely inside your perimeter',
    body: 'Self-hosted or VPC on the Enterprise plan, against stock PostgreSQL 15. No external vendor is load-bearing: embeddings fall back to a local deterministic embedder, and with no payment processor configured the platform simply bills by invoice.',
  },
]

const NOT_BUILT = [
  'SAML/SCIM single sign-on — role-based access exists, the identity-provider integration does not',
  'Marketplace payouts — paid listings are modelled, creator payment is not implemented',
  'Bi-directional ticket sync — tickets flow in, status does not yet flow back',
  'An MCP server exposing runs and approvals to other orchestrators',
]

export function Trust() {
  return (
    <section className="mk-section" id="trust">
      <div className="mk-shell">
        <div className="max-w-3xl">
          <Eyebrow n="07">Security &amp; honesty</Eyebrow>
          <SplitHeading
            text="A governance product that oversells itself has already failed."
            highlight={['failed.']}
            className="mk-display mt-6 text-[clamp(30px,4.6vw,58px)]"
          />
        </div>

        <div className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)] md:grid-cols-2">
          {POSTURE.map((item, i) => (
            <Reveal key={item.title} delay={(i % 2) * 0.07} className="bg-[var(--mk-panel)] p-7">
              <h3 className="text-[16px] font-semibold text-[var(--mk-ink)]">{item.title}</h3>
              <p className="mt-3 text-[14px] leading-relaxed text-[var(--mk-ink-2)]">{item.body}</p>
            </Reveal>
          ))}
        </div>

        <Reveal delay={0.1} className="mt-10">
          <div className="rounded-2xl border border-[var(--mk-hairline-lit)] bg-[color-mix(in_srgb,var(--mk-panel)_60%,transparent)] p-7 sm:p-9">
            <div className="mk-readout-label">What we have not built yet</div>
            <p className="mt-4 max-w-[68ch] text-[14.5px] leading-relaxed text-[var(--mk-ink-2)]">
              ADLC is a new product. These are on the roadmap and are not shipping today — if any
              of them is a hard requirement, it is better that you know now than in week three of a
              pilot.
            </p>
            <ul className="mt-5 grid gap-2.5 sm:grid-cols-2">
              {NOT_BUILT.map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <span
                    aria-hidden="true"
                    className="mt-[9px] h-px w-3 shrink-0 bg-[var(--mk-ink-3)]"
                  />
                  <span className="text-[13.5px] leading-relaxed text-[var(--mk-ink-3)]">
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
