import { FileCheck, KeyRound, Lock, Server } from 'lucide-react'
import { Reveal, SplitHeading } from '../Reveal'
import { Eyebrow } from '../ui'

/**
 * The security and honesty section.
 *
 * The "what we have not built" block at the bottom is deliberately styled
 * like everything above it rather than tucked into a footnote. A page that
 * only claims strengths gets read as marketing; one that names its gaps gets
 * read as a spec — and the buyer this product is for will find the gaps in
 * the first week regardless.
 */

const POSTURE = [
  {
    icon: Lock,
    title: 'Credentials encrypted at rest',
    body: 'OAuth tokens and bring-your-own model keys are sealed with Fernet before they touch the database. API keys are stored as SHA-256 hashes behind a visible prefix, so a database dump does not hand over anyone’s repositories. Code and prompts are never used to train third-party models.',
  },
  {
    icon: KeyRound,
    title: 'Scoped keys, and approval is its own scope',
    body: 'Public API keys and user roles carry explicit scopes. `runs:approve` is deliberately a different scope from `runs:write` — a CI job or agent that can start work should not be able to sign off on it.',
  },
  {
    icon: FileCheck,
    title: 'Every decision is written down',
    body: 'Who approved, under which policy, against which reviewer score, at what time, on which environment — every mutating request across the whole API is logged, not only the endpoints someone remembered to instrument. Retention is configurable and enforced by a nightly job.',
  },
  {
    icon: Server,
    title: 'It can run entirely inside your perimeter',
    body: 'Self-hosted or VPC on the Enterprise plan, against stock PostgreSQL 15. No external vendor is load-bearing: embeddings fall back to a local deterministic embedder, and Ollama is a first-class provider for fully air-gapped inference.',
  },
]

/** As of this pass: MCP (`POST /mcp`) and Jira/Linear ticket write-back both
 *  shipped, so neither is listed here any more — see CLAUDE.md's "MCP
 *  Server" and "Ticket Write-back" sections. What is left is what `/security`
 *  itself still lists as absent. */
const NOT_BUILT = [
  'SAML-only SSO and SCIM directory provisioning — OIDC SSO is built and covers Okta, Entra ID, Google Workspace, Auth0, Keycloak and PingFederate',
  'Marketplace creator payouts — paid listings are modelled, creator payment is not implemented',
]

export function Trust() {
  return (
    <section className="mk-section relative" id="trust">
      <div className="mk-shell relative z-10">
        <div className="max-w-3xl">
          <Eyebrow n="03">Security &amp; honesty</Eyebrow>
          <SplitHeading
            text="A governance product that oversells itself has already failed."
            highlight={['failed.']}
            className="mk-display mt-6 text-[clamp(32px,4.8vw,60px)] font-bold tracking-tight"
          />
          <p className="mt-6 text-[clamp(15px,1.6vw,18px)] leading-relaxed text-[var(--mk-ink-2)]">
            A platform that orchestrates code delivery into production must hold itself to the
            highest standard of verification. Every claim below can be inspected in the codebase.
          </p>
        </div>

        {/* Detailed Posture Cards */}
        <div className="mt-12 grid gap-4 md:grid-cols-2">
          {POSTURE.map((item, i) => {
            const Icon = item.icon
            return (
              <Reveal key={item.title} delay={(i % 2) * 0.07} className="mk-bento-card">
                <div className="flex items-center gap-3 pb-3 border-b border-[var(--mk-hairline)]">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--mk-ember)]/15 text-[var(--mk-ember-lit)]">
                    <Icon className="h-4 w-4" />
                  </span>
                  <h3 className="text-[16px] font-semibold text-[var(--mk-ink)]">{item.title}</h3>
                </div>
                <p className="mt-3.5 text-[14px] leading-relaxed text-[var(--mk-ink-2)]">{item.body}</p>
              </Reveal>
            )
          })}
        </div>

        <Reveal delay={0.1} className="mt-8">
          <div className="mk-bento-card rounded-2xl border-[var(--mk-hairline-lit)] p-7 sm:p-9">
            <div className="mk-readout-label">What we have not built yet</div>
            <p className="mt-4 max-w-[68ch] text-[14.5px] leading-relaxed text-[var(--mk-ink-2)]">
              Evolune OS is a new product. These are on the roadmap and are not shipping today — if
              any of them is a hard requirement, it is better that you know now than in week three
              of a pilot. The full posture, including everything already built, is on{' '}
              <a href="/security" className="text-[var(--mk-ember-lit)] hover:underline">
                /security
              </a>
              .
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
