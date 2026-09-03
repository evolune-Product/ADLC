import { Check, FileCode2, Minus } from 'lucide-react'
import { Atmosphere, MarketingFooter, MarketingNav } from '@/components/marketing/Chrome'
import { useMarketingSurface } from '@/components/marketing/hooks'
import { Reveal, SplitHeading } from '@/components/marketing/Reveal'
import { MkButton, SectionHead } from '@/components/marketing/ui'
import { SECURITY_POSTURE } from '@/components/marketing/content'
import type { PostureItem } from '@/components/marketing/content'
import { Seo } from '@/components/Seo'

/**
 * The page a security reviewer opens before anyone else at their company is
 * allowed to try the product.
 *
 * Its whole design premise is the fourth group: **what is not in place is
 * listed with everything else**, in the same type, not in a footnote. A vendor
 * page that lists only its strengths gets found out during the questionnaire,
 * and by then the deal has a trust problem rather than a gap problem. Evolune OS has
 * no SOC 2, no SSO and no pen-test report, and saying so here costs less than
 * having it discovered in week six.
 *
 * Every "built" claim names the file it lives in, so it can be verified rather
 * than believed.
 */
export default function SecurityPage() {
  useMarketingSurface()

  return (
    <div className="mk-root relative min-h-screen bg-[var(--mk-ground)] text-[var(--mk-ink)]">
      <Seo
        title="Security & data — Evolune OS"
        description="How Evolune OS handles credentials, model traffic and evidence — and what it does not have yet. Encrypted OAuth tokens, bring-your-own model keys, local inference, policy-enforced approval gates, and a full audit trail. No SOC 2, no SSO: both stated plainly."
        path="/security"
      />
      <Atmosphere />
      <MarketingNav />

      <main className="relative pt-36 sm:pt-44">
        {/* Ambient radial lighting */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-10 left-1/2 -translate-x-1/2 h-[450px] w-[700px] rounded-full blur-[140px] opacity-20"
          style={{ background: 'radial-gradient(circle, #e8632a 0%, #8b5cf6 50%, transparent 70%)' }}
        />
        <section className="mk-shell relative z-10">
          <SectionHead
            eyebrow="Security & data"
            standfirst="This product exists because autonomous work needs a control plane. It would be a poor advertisement for that idea if the platform running it were vague about its own controls. Everything below can be read in the repository, and the last group is the part most vendor pages leave out."
          >
            <SplitHeading
              as="h1"
              text="What we hold, what we enforce, and what we do not have."
              highlight={['do', 'not', 'have.']}
              className="mk-display text-[clamp(30px,4.6vw,58px)]"
            />
          </SectionHead>
        </section>

        {SECURITY_POSTURE.map((group, gi) => (
          <section key={group.group} className="mk-shell mt-20 first-of-type:mt-24">
            <Reveal>
              <div className="flex items-baseline gap-4">
                <span className="mk-mono text-[11px] tracking-[0.2em] text-[var(--mk-ember-lit)]">
                  {String(gi + 1).padStart(2, '0')}
                </span>
                <h2 className="mk-display text-[clamp(22px,2.6vw,30px)]">{group.group}</h2>
              </div>
              <div className="mk-rule mt-5" />
            </Reveal>

            <div className="mt-8 grid gap-px overflow-hidden rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)] md:grid-cols-2">
              {group.items.map((item, i) => (
                <PostureCard key={item.title} item={item} delay={Math.min(i, 3) * 0.06} />
              ))}
            </div>
          </section>
        ))}

        <section className="mk-shell py-24">
          <Reveal>
            <div className="mk-glass flex flex-col items-start gap-6 rounded-2xl p-8 sm:flex-row sm:items-center sm:justify-between sm:p-10">
              <div>
                <h2 className="mk-display text-[clamp(20px,2.4vw,28px)]">
                  Have a question this page does not answer?
                </h2>
                <p className="mt-3 max-w-[52ch] text-[14.5px] leading-relaxed text-[var(--mk-ink-2)]">
                  The free tier needs no card and no call, and it runs on your own model key — which
                  is the fastest way to see exactly what leaves your perimeter and what does not.
                </p>
              </div>
              <MkButton to="/register" className="shrink-0">
                Start free
              </MkButton>
            </div>
          </Reveal>
        </section>
      </main>

      <MarketingFooter />
    </div>
  )
}

function PostureCard({ item, delay }: { item: PostureItem; delay: number }) {
  const absent = item.state === 'absent'

  return (
    <Reveal delay={delay} className="bg-[var(--mk-panel)] p-7">
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="mt-[3px] flex h-5 w-5 shrink-0 items-center justify-center rounded-full border"
          style={{
            borderColor: absent ? 'var(--mk-hairline-lit)' : 'var(--mk-pass)',
            color: absent ? 'var(--mk-ink-3)' : 'var(--mk-pass)',
          }}
        >
          {absent ? <Minus className="h-3 w-3" strokeWidth={3} /> : <Check className="h-3 w-3" strokeWidth={3} />}
        </span>

        <div className="min-w-0">
          <h3 className="text-[15.5px] font-medium leading-snug text-[var(--mk-ink)]">
            {item.title}
          </h3>
          {/* Said in words, not only in an icon: a colour-blind reader and a
              screen-reader user both need the state, and "not built" is the
              single most important thing on this page. */}
          <p className="mk-mono mt-1.5 text-[10.5px] uppercase tracking-[0.16em]"
             style={{ color: absent ? 'var(--mk-ink-3)' : 'var(--mk-pass)' }}>
            {absent ? 'Not built' : 'In the codebase'}
          </p>

          <p className="mt-3.5 text-[14px] leading-relaxed text-[var(--mk-ink-2)]">{item.body}</p>

          {item.where ? (
            <p className="mk-mono mt-4 flex items-center gap-2 text-[11.5px] text-[var(--mk-ink-3)]">
              <FileCode2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span className="truncate">{item.where}</span>
            </p>
          ) : null}
        </div>
      </div>
    </Reveal>
  )
}
