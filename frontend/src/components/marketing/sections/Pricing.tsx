import { Fragment, useState } from 'react'
import { Check, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Reveal, SplitHeading } from '../Reveal'
import { Eyebrow, MkButton } from '../ui'
import { PLANS, PRICING_NOTES, formatInrWithGst, INDIA_GST_RATE } from '../content'

type Currency = 'usd' | 'inr'

/**
 * Pricing, argued rather than listed.
 *
 * The plan cards are followed by why the numbers are what they are, including
 * our own worst-case inference cost per run. Publishing the number a buyer
 * would otherwise reverse-engineer is cheap, and the alternative — being
 * caught having hidden it — is not.
 */

export function PricingPlans({ compact = false }: { compact?: boolean }) {
  const [currency, setCurrency] = useState<Currency>('usd')

  return (
    <div className="mx-auto max-w-3xl">
      {compact ? null : (
        <div className="mb-5 flex items-center justify-end gap-1">
          <span className="mk-mono mr-2 text-[10.5px] uppercase tracking-[0.14em] text-[var(--mk-ink-3)]">
            Currency
          </span>
          {(['usd', 'inr'] as const).map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCurrency(c)}
              className={cn(
                'mk-mono rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.1em] transition-colors',
                currency === c
                  ? 'border-[var(--mk-ember)] bg-[var(--mk-ember)]/10 text-[var(--mk-ember-lit)]'
                  : 'border-[var(--mk-hairline)] text-[var(--mk-ink-3)] hover:text-[var(--mk-ink-2)]',
              )}
            >
              {c === 'usd' ? 'USD' : 'INR incl. GST'}
            </button>
          ))}
        </div>
      )}
      <div
        className={cn(
          'grid gap-px overflow-hidden rounded-2xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)]',
          'grid-cols-1 sm:grid-cols-2',
        )}
      >
      {PLANS.map((plan, i) => (
        <Reveal
          key={plan.id}
          delay={i * 0.06}
          className={cn(
            'relative flex flex-col p-7',
            plan.featured ? 'bg-[var(--mk-panel-2)]' : 'bg-[var(--mk-panel)]',
          )}
        >
          {plan.featured ? (
            <>
              {/* A hairline of heat along the top edge, rather than a badge
                  floating over the card. */}
              <span
                aria-hidden="true"
                className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[var(--mk-ember)] to-transparent"
              />
              <span className="mk-mono absolute right-6 top-6 text-[10px] uppercase tracking-[0.16em] text-[var(--mk-ember-lit)]">
                Most teams
              </span>
            </>
          ) : null}

          <div className="mk-display text-[20px]">{plan.name}</div>

          <div className="mt-5 flex items-baseline gap-2">
            <span className="mk-readout-value text-[clamp(30px,3.4vw,40px)]">
              {currency === 'inr' && plan.priceUsd !== null
                ? formatInrWithGst(plan.priceUsd)
                : plan.price}
            </span>
            <span className="text-[13px] text-[var(--mk-ink-3)]">{plan.cadence}</span>
          </div>
          {currency === 'inr' && plan.priceUsd !== null ? (
            <div className="mk-mono mt-1 text-[10.5px] text-[var(--mk-ink-3)]">
              {plan.priceUsd === 0 ? 'No GST on a free plan' : `Includes ${Math.round(INDIA_GST_RATE * 100)}% GST · billed via Razorpay`}
            </div>
          ) : null}

          {/* Fixed height, not min-height: the summaries wrap to two lines or
              three depending on the column, and without this the Runs/Overage/
              Seats plate — the thing a buyer scans across — sat at a different
              baseline in every card. */}
          <p className="mt-4 h-[4.5rem] text-[13.5px] leading-relaxed text-[var(--mk-ink-2)]">
            {plan.summary}
          </p>

          <div className="mt-5 space-y-1.5 border-y border-[var(--mk-hairline)] py-4">
            <Line label="Runs" value={plan.runs} />
            <Line label="Overage" value={plan.overage} />
            <Line label="Seats" value={plan.seats} />
          </div>

          {compact ? null : (
            <ul className="mt-5 flex-1 space-y-2.5">
              {plan.features.map((feature) => (
                <li key={feature} className="flex items-start gap-2.5">
                  <Check
                    className="mt-[3px] h-3.5 w-3.5 shrink-0 text-[var(--mk-ember-lit)]"
                    strokeWidth={3}
                  />
                  <span className="text-[13.5px] leading-snug text-[var(--mk-ink-2)]">
                    {feature}
                  </span>
                </li>
              ))}
            </ul>
          )}

          <MkButton
            to={plan.ctaTo}
            variant={plan.featured ? 'primary' : 'ghost'}
            className="mt-7 w-full"
          >
            {plan.cta}
          </MkButton>
        </Reveal>
      ))}
      </div>
    </div>
  )
}

function Line({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="mk-mono text-[10.5px] uppercase tracking-[0.14em] text-[var(--mk-ink-3)]">
        {label}
      </span>
      <span className="mk-mono text-right text-[12px] text-[var(--mk-ink)]">{value}</span>
    </div>
  )
}

export function PricingSection() {
  return (
    <section className="mk-section" id="pricing">
      <div className="mk-shell">
        <div className="max-w-3xl">
          <Eyebrow n="06">Pricing</Eyebrow>
          <SplitHeading
            text="Pay for runs. Buy seats for governance."
            highlight={['governance.']}
            className="mk-display mt-6 text-[clamp(30px,4.6vw,58px)]"
          />
          <Reveal delay={0.15}>
            <p className="mt-7 max-w-[62ch] text-[clamp(15px,1.6vw,18px)] leading-relaxed text-[var(--mk-ink-2)]">
              A run is one ticket taken through one pod — plan, code, QA, review, approval, deploy.
              Retries inside a run are not a second run. Seats decide who can approve and who can
              read the audit log, which is what an organisation is actually buying.
            </p>
          </Reveal>
        </div>

        <div className="mt-14">
          <PricingPlans />
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
          <p className="text-[13px] text-[var(--mk-ink-3)]">
            All prices in USD, excluding tax. Annual billing and committed-use terms on request.
          </p>
          <a
            href="/pricing"
            className="mk-mono text-[12px] uppercase tracking-[0.14em] text-[var(--mk-ember-lit)] hover:underline"
          >
            Full comparison and questions →
          </a>
        </div>
      </div>
    </section>
  )
}

export function PricingNotes() {
  return (
    <div className="grid gap-px overflow-hidden rounded-2xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)] md:grid-cols-2">
      {PRICING_NOTES.map((note, i) => (
        <Reveal key={note.title} delay={i * 0.06} className="bg-[var(--mk-panel)] p-7">
          <h3 className="text-[16px] font-semibold text-[var(--mk-ink)]">{note.title}</h3>
          <p className="mt-3 text-[14px] leading-relaxed text-[var(--mk-ink-2)]">{note.body}</p>
        </Reveal>
      ))}
    </div>
  )
}

/* ─────────────────────────────────────────────────────── comparison table */

type Row = { feature: string; values: [string | boolean, string | boolean] }

const COMPARISON: Array<{ group: string; rows: Row[] }> = [
  {
    group: 'Running work',
    rows: [
      { feature: 'Included runs per month', values: ['25', 'Custom'] },
      { feature: 'Overage per run', values: ['—', 'Committed'] },
      { feature: 'Projects', values: ['1', 'Unlimited'] },
      { feature: 'Agent pipeline with approval gate', values: [true, true] },
      { feature: 'Multi-environment promotion', values: [false, true] },
    ],
  },
  {
    group: 'Governance',
    rows: [
      { feature: 'Approval policies', values: [false, true] },
      { feature: 'Reviewer agent and findings', values: [false, true] },
      { feature: 'Per-environment policy scoping', values: [false, true] },
      { feature: 'Two-approver policies and RBAC', values: [false, true] },
      { feature: 'Audit log', values: ['30 days', 'Configurable'] },
      { feature: 'Compliance evidence export', values: [false, true] },
    ],
  },
  {
    group: 'Intelligence',
    rows: [
      { feature: 'Skills and pods', values: [true, true] },
      { feature: 'Template library', values: [true, true] },
      { feature: 'Codebase memory', values: [false, true] },
      { feature: 'Marketplace publishing', values: [false, true] },
      { feature: 'ROI analytics and scorecards', values: [false, true] },
    ],
  },
  {
    group: 'Platform',
    rows: [
      { feature: 'Bring your own model key', values: ['Required', true] },
      { feature: 'Public API and signed webhooks', values: [false, true] },
      { feature: 'Slack and email notifications', values: [false, true] },
      { feature: 'Self-hosted or VPC', values: [false, true] },
      { feature: 'SLA and named contact', values: [false, true] },
    ],
  },
]

export function PricingComparison() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-left">
        <thead>
          <tr>
            <th className="mk-readout-label w-[38%] py-4 pr-4 align-bottom">Feature</th>
            {PLANS.map((plan) => (
              <th key={plan.id} className="py-4 pr-4 align-bottom">
                <div className="mk-display text-[15px]">{plan.name}</div>
                <div className="mk-mono mt-1 text-[11px] text-[var(--mk-ink-3)]">{plan.price}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {COMPARISON.map((section) => (
            <Fragment key={section.group}>
              <tr>
                <td colSpan={3} className="pb-2 pt-8">
                  <div className="mk-eyebrow text-[var(--mk-ember-lit)]">{section.group}</div>
                </td>
              </tr>
              {section.rows.map((row) => (
                <tr key={row.feature} className="border-t border-[var(--mk-hairline)]">
                  <td className="py-3.5 pr-4 text-[14px] text-[var(--mk-ink-2)]">{row.feature}</td>
                  {row.values.map((value, i) => (
                    <td key={i} className="py-3.5 pr-4">
                      <Cell value={value} />
                    </td>
                  ))}
                </tr>
              ))}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Cell({ value }: { value: string | boolean }) {
  if (value === true) {
    return (
      <>
        <Check className="h-4 w-4 text-[var(--mk-ember-lit)]" strokeWidth={2.5} aria-hidden="true" />
        <span className="sr-only">Included</span>
      </>
    )
  }
  if (value === false) {
    return (
      <>
        <Minus className="h-4 w-4 text-[var(--mk-ink-3)] opacity-50" aria-hidden="true" />
        <span className="sr-only">Not included</span>
      </>
    )
  }
  return <span className="mk-mono text-[12.5px] text-[var(--mk-ink)]">{value}</span>
}
