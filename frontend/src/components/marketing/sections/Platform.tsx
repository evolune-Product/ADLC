import { Reveal, SplitHeading, DrawRule } from '../Reveal'
import { Eyebrow } from '../ui'
import { CAPABILITIES, INTEGRATIONS, MODEL_PROVIDERS, PLATFORM_FACTS } from '../content'

/**
 * What the platform is made of.
 *
 * Six capabilities, then the two questions every technical evaluator asks in
 * the first five minutes — which models, and what does it plug into. Answering
 * those on the landing page rather than making someone book a call is the
 * whole difference between a bottom-up product and a brochure.
 */
export function Platform() {
  return (
    <section className="mk-section" id="platform">
      <div className="mk-shell">
        <div className="max-w-3xl">
          <Eyebrow n="04">The platform</Eyebrow>
          <SplitHeading
            text="Four things compound. None of them are portable to a competitor."
            highlight={['compound.']}
            className="mk-display mt-6 text-[clamp(30px,4.6vw,58px)]"
          />
          <Reveal delay={0.15}>
            <p className="mt-7 max-w-[64ch] text-[clamp(15px,1.6vw,18px)] leading-relaxed text-[var(--mk-ink-2)]">
              Your skill library, your codebase memory, your run history and your compliance
              evidence all get better the longer the platform runs — and all four belong to you.
              Skills are markdown in your repository; the audit log exports; the memory is yours to
              delete.
            </p>
          </Reveal>
        </div>

        <div className="mt-16 grid gap-px overflow-hidden rounded-2xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)] md:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((cap, i) => (
            <Reveal
              key={cap.title}
              delay={(i % 3) * 0.07}
              className="group bg-[var(--mk-panel)] p-7 transition-colors duration-300 hover:bg-[var(--mk-panel-2)]"
            >
              <div className="mk-readout-label">{cap.tag}</div>
              <h3 className="mk-display mt-4 text-[22px]">{cap.title}</h3>
              <p className="mt-3.5 text-[14.5px] leading-relaxed text-[var(--mk-ink-2)]">
                {cap.body}
              </p>
            </Reveal>
          ))}
        </div>

        <DrawRule className="mt-24" />

        {/* Models */}
        <div className="mt-20 grid gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:gap-20" id="models">
          <Reveal>
            <Eyebrow>Model agility</Eyebrow>
            <h3 className="mk-display mt-5 text-[clamp(24px,3vw,36px)]">
              No single-model dependency. Ever.
            </h3>
            <p className="mt-5 text-[15px] leading-relaxed text-[var(--mk-ink-2)]">
              Model choice is per agent, so your Planner and your Reviewer need not be the same
              model — or the same vendor. Every call is metered with its token counts and costed in
              integer millicents, whichever provider served it. Point the platform at your own key
              and the inference bill is yours, at zero markup.
            </p>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="grid gap-px overflow-hidden rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)] sm:grid-cols-2">
              {MODEL_PROVIDERS.map((provider) => (
                <div key={provider.name} className="bg-[var(--mk-panel)] px-5 py-5">
                  <div className="text-[15px] font-semibold text-[var(--mk-ink)]">
                    {provider.name}
                  </div>
                  <div className="mk-mono mt-1.5 text-[11.5px] text-[var(--mk-ink-3)]">
                    {provider.detail}
                  </div>
                </div>
              ))}
              <div className="bg-[var(--mk-panel)] px-5 py-5">
                <div className="text-[15px] font-semibold text-[var(--mk-ember-lit)]">
                  Bring your own key
                </div>
                <div className="mk-mono mt-1.5 text-[11.5px] text-[var(--mk-ink-3)]">
                  Per workspace, encrypted at rest
                </div>
              </div>
            </div>
          </Reveal>
        </div>

        {/* Integrations */}
        <div className="mt-24 grid gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:gap-20" id="integrations">
          <Reveal>
            <Eyebrow>Integrations</Eyebrow>
            <h3 className="mk-display mt-5 text-[clamp(24px,3vw,36px)]">
              It works where the work already is.
            </h3>
            <p className="mt-5 text-[15px] leading-relaxed text-[var(--mk-ink-2)]">
              Tickets come in from Jira or Linear. Branches and pull requests go out to GitHub or
              GitLab. Approvals reach people in Slack and email. Everything else can be driven
              through the public API, which uses scoped keys — {' '}
              <span className="mk-mono text-[13.5px] text-[var(--mk-ink)]">runs:approve</span> is
              deliberately a different scope from{' '}
              <span className="mk-mono text-[13.5px] text-[var(--mk-ink)]">runs:write</span>.
            </p>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="grid gap-px overflow-hidden rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)] sm:grid-cols-2">
              {INTEGRATIONS.map((integration) => (
                <div key={integration.name} className="bg-[var(--mk-panel)] px-5 py-5">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-[15px] font-semibold text-[var(--mk-ink)]">
                      {integration.name}
                    </span>
                    <span className="mk-mono text-[10px] uppercase tracking-[0.14em] text-[var(--mk-ink-3)]">
                      {integration.kind}
                    </span>
                  </div>
                  <div className="mk-mono mt-1.5 text-[11.5px] text-[var(--mk-ink-3)]">
                    {integration.detail}
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-[12.5px] text-[var(--mk-ink-3)]">
              {PLATFORM_FACTS.apiEndpoints} endpoints across the platform API; the public v1 surface
              is the scoped, key-authenticated subset.
            </p>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
