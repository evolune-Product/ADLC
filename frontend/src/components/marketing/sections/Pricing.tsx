import { Fragment, useState } from 'react'
import { Check, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Reveal } from '../Reveal'
import { MkButton } from '../ui'
import { PLANS, PRICING_NOTES, formatInrWithGst } from '../content'

type Currency = 'usd' | 'inr'

/**
 * Pricing, argued rather than listed.
 *
 * The plan cards are followed by why the numbers are what they are, including
 * our own worst-case inference cost per run. Publishing the number a buyer
 * would otherwise reverse-engineer is cheap, and the alternative — being
 * caught having hidden it — is not.
 *
 * There is deliberately no annual/monthly toggle here: `PLANS` in
 * `content.ts` mirrors the pricing model in `documents/BUSINESS_PLAN_2026.md`
 * and none of the three payment gateways (`stripe_service` /
 * `razorpay_service` / `paypal_service`) support annual billing today —
 * showing a discounted price the checkout flow cannot honour is a bug, not a
 * feature.
 */

export function PricingPlans({ compact = false }: { compact?: boolean }) {
  const [currency, setCurrency] = useState<Currency>('usd')

  return (
    <div className="mx-auto max-w-5xl">
      {compact ? null : (
        <div className="mb-8 flex flex-wrap items-center justify-end gap-4">
          <div className="flex items-center gap-1.5">
            <span className="mk-mono text-[10.5px] uppercase tracking-[0.14em] text-[var(--mk-ink-3)]">
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
                    ? 'border-[var(--mk-ember)] bg-[var(--mk-ember)]/15 text-[var(--mk-ember-lit)]'
                    : 'border-[var(--mk-hairline)] text-[var(--mk-ink-3)] hover:text-[var(--mk-ink-2)]',
                )}
              >
                {c === 'usd' ? 'USD ($)' : 'INR (₹)'}
              </button>
            ))}
          </div>
        </div>
      )}

      <div
        className={cn(
          'grid gap-6',
          'grid-cols-1 md:grid-cols-3',
        )}
      >
        {PLANS.map((plan, i) => {
          const displayPrice =
            plan.priceUsd === null
              ? plan.price
              : currency === 'inr'
                ? formatInrWithGst(plan.priceUsd)
                : `$${plan.priceUsd}`

          return (
            <Reveal
              key={plan.id}
              delay={i * 0.06}
              className={cn(
                'relative flex flex-col rounded-2xl border p-7 sm:p-8 transition-all duration-300',
                plan.featured
                  ? 'border-[var(--mk-ember)]/60 bg-[var(--mk-panel-2)] shadow-[0_0_35px_rgba(232,99,42,0.12)] scale-[1.02]'
                  : 'border-[var(--mk-hairline)] bg-[var(--mk-panel)] hover:border-[var(--mk-hairline-lit)]',
              )}
            >
              {plan.featured && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                  <span className="mk-mono rounded-full bg-[var(--mk-ember)] px-3.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] text-[#0a0508] shadow-[0_0_12px_rgba(232,99,42,0.5)]">
                    Most teams
                  </span>
                </div>
              )}

              <div className="text-xl font-bold text-[var(--mk-ink)]">{plan.name}</div>

              <div className="mt-5 flex items-baseline gap-2">
                <span className="mk-readout-value text-[clamp(32px,3.6vw,44px)]">
                  {displayPrice}
                </span>
                <span className="text-[13px] text-[var(--mk-ink-3)]">{plan.cadence}</span>
              </div>

              <p className="mt-4 min-h-[3rem] text-[13.5px] leading-relaxed text-[var(--mk-ink-2)]">
                {plan.summary}
              </p>

              <div className="mt-6 space-y-2 border-y border-[var(--mk-hairline)] py-4">
                <Line label="Included runs" value={plan.runs} />
                <Line label="Overage" value={plan.overage} />
                <Line label="Seats" value={plan.seats} />
              </div>

              {!compact && (
                <ul className="mt-6 flex-1 space-y-2.5">
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
                className={cn('mt-8 w-full', plan.featured && 'mk-btn-luxury')}
              >
                {plan.cta}
              </MkButton>
            </Reveal>
          )
        })}
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
      <span className="mk-mono text-right text-[12px] font-semibold text-[var(--mk-ink)]">{value}</span>
    </div>
  )
}

/**
 * Interactive ROI estimator. Distinct from the fabricated-benchmark problem
 * elsewhere: the assumptions (team size, hours per ticket, blended rate) are
 * all visible and user-driven, and the output is explicitly framed as an
 * estimate the visitor computed, not a measured claim about this platform.
 */
export function RoiCalculator() {
  const [teamSize, setTeamSize] = useState(8)
  const ticketsPerEngineerPerMonth = 12
  const hoursSavedPerTicket = 3.5
  const totalHoursSaved = teamSize * ticketsPerEngineerPerMonth * hoursSavedPerTicket
  const estimatedSavingsDollars = totalHoursSaved * 75 // $75/hr blended dev rate, stated assumption

  return (
    <div className="mt-16 rounded-2xl border border-[var(--mk-hairline)] bg-[var(--mk-panel)] p-6 sm:p-8 backdrop-blur-md">
      <div className="max-w-2xl">
        <span className="mk-mono text-[11px] font-semibold text-[var(--mk-pass)] uppercase tracking-wider">
          Estimate, not a measurement
        </span>
        <h3 className="text-xl sm:text-2xl font-bold text-[var(--mk-ink)] mt-1">
          Calculate your engineering velocity gain
        </h3>
        <p className="text-sm text-[var(--mk-ink-2)] mt-2">
          A rough model from stated assumptions — tickets per engineer, hours saved per ticket, a
          blended dev rate — not a benchmark of this platform. Adjust the team size and see how the
          assumptions scale.
        </p>
      </div>

      <div className="mt-8 grid gap-8 md:grid-cols-12 items-center">
        <div className="md:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-[var(--mk-ink)]">Full-time software engineers:</span>
            <span className="mk-mono text-lg font-bold text-[var(--mk-ember-lit)]">{teamSize} engineers</span>
          </div>
          <input
            type="range"
            min="2"
            max="60"
            value={teamSize}
            onChange={(e) => setTeamSize(Number(e.target.value))}
            className="w-full h-2 bg-[var(--mk-hairline)] rounded-lg appearance-none cursor-pointer accent-[var(--mk-ember)]"
          />
          <div className="flex justify-between text-[11px] mk-mono text-[var(--mk-ink-3)]">
            <span>2 devs (seed)</span>
            <span>25 devs (Series B)</span>
            <span>60+ devs (enterprise)</span>
          </div>
        </div>

        <div className="md:col-span-5 grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] p-4 text-center">
            <div className="mk-mono text-[10px] text-[var(--mk-ink-3)] uppercase">Hours / mo (assumed)</div>
            <div className="text-2xl font-bold text-[var(--mk-ink)] mt-1 mk-mono">{totalHoursSaved.toLocaleString()} hrs</div>
          </div>
          <div className="rounded-xl border border-[var(--mk-pass)]/30 bg-[var(--mk-pass)]/10 p-4 text-center">
            <div className="mk-mono text-[10px] text-[var(--mk-pass)] uppercase">Value at $75/hr</div>
            <div className="text-2xl font-bold text-[var(--mk-pass)] mt-1 mk-mono">${estimatedSavingsDollars.toLocaleString()}</div>
          </div>
        </div>
      </div>
    </div>
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

type Row = { feature: string; values: [string | boolean, string | boolean, string | boolean] }

const COMPARISON: Array<{ group: string; rows: Row[] }> = [
  {
    group: 'Running work',
    rows: [
      { feature: 'Included runs per month', values: ['25', '25', 'Custom'] },
      { feature: 'Overage per run', values: ['—', '—', 'Committed'] },
      { feature: 'Projects', values: ['1', '1', 'Unlimited'] },
      { feature: 'Agent pipeline with approval gate', values: [true, true, true] },
      { feature: 'Multi-environment promotion', values: [false, false, true] },
    ],
  },
  {
    group: 'Governance',
    rows: [
      { feature: 'Approval policies', values: [false, false, true] },
      { feature: 'Reviewer agent and findings', values: [false, false, true] },
      { feature: 'Per-environment policy scoping', values: [false, false, true] },
      { feature: 'Two-approver policies and RBAC', values: [false, false, true] },
      { feature: 'Audit log', values: ['30 days', '30 days', 'Configurable'] },
      { feature: 'Compliance evidence export', values: [false, false, true] },
    ],
  },
  {
    group: 'Intelligence',
    rows: [
      { feature: 'Skills and pods', values: [true, true, true] },
      { feature: 'Template library', values: [true, true, true] },
      { feature: 'Codebase memory', values: [false, false, true] },
      { feature: 'Marketplace publishing', values: [false, false, true] },
      { feature: 'ROI analytics and scorecards', values: [false, false, true] },
    ],
  },
  {
    group: 'Platform',
    rows: [
      { feature: 'Bring your own model key', values: ['Required', 'Required', true] },
      { feature: 'Public API and signed webhooks', values: [false, false, true] },
      { feature: 'Slack and email notifications', values: [false, false, true] },
      { feature: 'Self-hosted or VPC', values: [false, false, true] },
      { feature: 'SLA and named contact', values: [false, false, true] },
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
                <td colSpan={4} className="pb-2 pt-8">
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
