import { useMemo, useState } from 'react'
import { Check, Lock, ShieldAlert, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Reveal, SplitHeading } from '../Reveal'
import { Eyebrow } from '../ui'

/**
 * The gate, made playable.
 *
 * The verdict panel below is not a mock-up: `evaluate` is a faithful port of
 * `policy_service.evaluate_deploy` and `check_changes` — the same severity
 * ranks, the same 100-minus-weighted-penalty review score, the same reason
 * strings, the same glob matching on protected paths. It runs against one
 * fixed sample run so the visitor can turn each rule on and watch a deploy
 * that was about to happen stop happening.
 *
 * Showing the actual decision logic is a stronger argument than describing it,
 * and it is falsifiable: anyone can open `app/services/policy_service.py` and
 * check that this agrees with it.
 */

/** Mirrors `policy_service.SEVERITY_RANK`. */
const SEVERITY_RANK: Record<string, number> = {
  info: 0,
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
}

/** Mirrors the weights in `policy_service.review_score`. */
const SEVERITY_WEIGHT: Record<string, number> = {
  info: 0,
  low: 3,
  medium: 8,
  high: 20,
  critical: 40,
}

type Finding = { severity: keyof typeof SEVERITY_WEIGHT; message: string }

/** One fixed, clearly-labelled sample run. */
const SAMPLE = {
  ticket: 'ADLC-482 · Add per-project usage caps',
  branch: 'agent/adlc-482-usage-caps',
  files: [
    'app/services/metering_service.py',
    'app/routers/billing.py',
    'app/models/billing.py',
    'infra/terraform/prod/quotas.tf',
    'frontend/src/pages/billing/BillingPage.tsx',
    'tests/test_metering.py',
  ],
  approvals: 1,
  findings: [
    { severity: 'high', message: 'Quota check runs after the first model call, not before' },
    { severity: 'medium', message: 'Overage price read as float; the rest of billing is integer cents' },
    { severity: 'low', message: 'Missing docstring on apply_project_cap' },
  ] as Finding[],
  costCents: 118,
}

/** Mirrors `policy_service.review_score`: 100 = clean. */
function reviewScore(findings: Finding[]) {
  const penalty = findings.reduce((sum, f) => sum + (SEVERITY_WEIGHT[f.severity] ?? 0), 0)
  return Math.max(0, 100 - penalty)
}

/** Minimal glob matcher — enough for the `dir/**` and `*.tf` shapes fnmatch
 *  handles on the server for these patterns. */
function globMatch(pattern: string, path: string) {
  const escaped = pattern
    .replace(/[.+^${}()|[\]\\]/g, '\\$&')
    .replace(/\*\*/g, ' ')
    .replace(/\*/g, '[^/]*')
    .replace(/ /g, '.*')
  return new RegExp(`^${escaped}$`).test(path)
}

type Rules = {
  twoApprovers: boolean
  requireReviewPass: boolean
  blockOnHigh: boolean
  protectInfra: boolean
  costCap: boolean
}

const RULES: Array<{ key: keyof Rules; label: string; detail: string }> = [
  {
    key: 'twoApprovers',
    label: 'Require 2 approvers',
    detail: 'min_approvers = 2',
  },
  {
    key: 'requireReviewPass',
    label: 'Require a reviewer score of 80',
    detail: 'require_review_pass, min_review_score = 80',
  },
  {
    key: 'blockOnHigh',
    label: 'Block on high-severity findings',
    detail: "block_on_severity = 'high'",
  },
  {
    key: 'protectInfra',
    label: 'Protect infrastructure paths',
    detail: "protected_paths = ['infra/**']",
  },
  {
    key: 'costCap',
    label: 'Cap the run at $1.00',
    detail: 'max_run_cost_cents = 100',
  },
]

/** Faithful port of the server's decision, for this one sample run. */
function evaluate(rules: Rules) {
  const reasons: string[] = []
  const score = reviewScore(SAMPLE.findings)

  const need = rules.twoApprovers ? 2 : 1
  if (SAMPLE.approvals < need) {
    reasons.push(`${SAMPLE.approvals}/${need} required approvals`)
  }

  if (rules.requireReviewPass && score < 80) {
    reasons.push(`Review score ${score} is below the required 80`)
  }

  if (rules.blockOnHigh) {
    const threshold = SEVERITY_RANK.high
    const blocking = SAMPLE.findings.filter((f) => (SEVERITY_RANK[f.severity] ?? 0) >= threshold)
    if (blocking.length) {
      reasons.push(
        `${blocking.length} unresolved high+ finding(s): ${blocking.map((f) => f.message).join('; ')}`,
      )
    }
  }

  if (rules.protectInfra) {
    const hits = SAMPLE.files.filter((p) => globMatch('infra/**', p))
    if (hits.length) {
      reasons.push(`Protected path 'infra/**' would be modified: ${hits.join(', ')}`)
    }
  }

  if (rules.costCap && SAMPLE.costCents > 100) {
    reasons.push(`Run cost $${(SAMPLE.costCents / 100).toFixed(2)} exceeds the $1.00 cap`)
  }

  return { allowed: reasons.length === 0, reasons, score }
}

export function TheGate() {
  const [rules, setRules] = useState<Rules>({
    twoApprovers: false,
    requireReviewPass: true,
    blockOnHigh: true,
    protectInfra: false,
    costCap: false,
  })

  const decision = useMemo(() => evaluate(rules), [rules])

  return (
    <section className="mk-section" id="the-gate">
      <div className="mk-shell">
        <div className="max-w-3xl">
          <Eyebrow>The approval gate</Eyebrow>
          <SplitHeading
            as="h1"
            text="An approval that anyone can give is not a control."
            highlight={['control.']}
            className="mk-display mt-6 text-[clamp(30px,4.6vw,58px)]"
          />
          <Reveal delay={0.15}>
            <p className="mt-7 max-w-[64ch] text-[clamp(15px,1.6vw,18px)] leading-relaxed text-[var(--mk-ink-2)]">
              Most platforms stop at "a human clicked approve". A policy decides whether that click
              was <em className="not-italic text-[var(--mk-ink)]">enough</em> — how many people, at
              what reviewer score, with which severities outstanding, on files the agent was
              permitted to touch, under a cost ceiling.
            </p>
          </Reveal>
        </div>

        {/* Banner artwork */}
        <div className="mt-12 overflow-hidden rounded-2xl border border-[var(--mk-hairline)] bg-[var(--mk-panel)] shadow-2xl relative">
          <div className="absolute inset-0 bg-gradient-to-r from-[var(--mk-ground)] via-[color-mix(in_srgb,var(--mk-ground)_80%,transparent)] to-transparent z-10 p-8 sm:p-12 flex flex-col justify-center max-w-xl">
            <span className="mk-mono text-[11px] font-semibold text-[var(--mk-pass)] uppercase tracking-widest flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-[var(--mk-pass)]" />
              Policy engine
            </span>
            <h3 className="mk-display text-2xl sm:text-3xl font-bold text-[var(--mk-ink)] mt-2">
              Policy decisions are law. Not recommendations.
            </h3>
            <p className="text-sm text-[var(--mk-ink-2)] mt-3 leading-relaxed">
              A violation returns the run to the approval gate — it never silently proceeds and it
              never fails the run outright.
            </p>
          </div>
          <img
            src="/assets/security-vault.jpg"
            alt="Cryptographic security approval vault"
            className="w-full h-[280px] sm:h-[340px] object-cover object-right opacity-70"
          />
        </div>

        <div className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)] lg:grid-cols-[1fr_1.1fr]">
          {/* The rules */}
          <Reveal className="bg-[var(--mk-panel)] p-7 sm:p-9">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--mk-hairline)]">
              <div className="mk-readout-label text-[var(--mk-ink-2)]">Policy engine — rule toggles</div>
              <span className="text-[10px] rounded bg-[var(--mk-panel-2)] px-2 py-0.5 text-[var(--mk-ink-2)] mk-mono">
                Interactive
              </span>
            </div>
            <div className="mt-6 space-y-2.5">
              {RULES.map((rule) => {
                const on = rules[rule.key]
                return (
                  <button
                    key={rule.key}
                    type="button"
                    onClick={() => setRules((r) => ({ ...r, [rule.key]: !r[rule.key] }))}
                    aria-pressed={on}
                    className={cn(
                      'flex w-full items-start gap-3.5 rounded-xl border p-3.5 text-left transition-all duration-200',
                      on
                        ? 'border-[var(--mk-ember)]/60 bg-[var(--mk-ember)]/[0.08] shadow-[0_0_15px_rgba(232,99,42,0.15)]'
                        : 'border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] hover:border-[var(--mk-hairline-lit)] hover:bg-[color-mix(in_srgb,var(--mk-ink)_4%,transparent)]',
                    )}
                  >
                    <span
                      aria-hidden="true"
                      className={cn(
                        'mt-0.5 flex shrink-0 items-center justify-center rounded-md border transition-all',
                        on
                          ? 'border-[var(--mk-ember)] bg-[var(--mk-ember)] shadow-[0_0_8px_rgba(232,99,42,0.6)]'
                          : 'border-[var(--mk-hairline-lit)] bg-[var(--mk-panel-2)]',
                      )}
                      style={{ height: 20, width: 20 }}
                    >
                      {on ? <Check className="h-3 w-3 text-[#0a0508]" strokeWidth={3} /> : null}
                    </span>
                    <span className="min-w-0">
                      <span
                        className={cn(
                          'block text-[14.5px] font-medium transition-colors',
                          on ? 'text-[var(--mk-ink)]' : 'text-[var(--mk-ink-2)]',
                        )}
                      >
                        {rule.label}
                      </span>
                      <span className="mk-mono mt-1 block text-[11px] text-[var(--mk-ink-3)]">
                        {rule.detail}
                      </span>
                    </span>
                  </button>
                )
              })}
            </div>

            <p className="mt-6 text-[12.5px] leading-relaxed text-[var(--mk-ink-3)]">
              Policies scope per environment: allow flexible rapid development on staging while
              mandating 2 peer sign-offs and zero high-severity findings for production.
            </p>
          </Reveal>

          {/* The run and the verdict */}
          <div className="flex flex-col bg-[var(--mk-panel-2)]">
            <Reveal delay={0.1} className="border-b border-[var(--mk-hairline)] p-7 sm:p-9">
              <div className="flex items-center justify-between gap-4">
                <div className="mk-readout-label text-[var(--mk-ink-2)]">Candidate run inspection</div>
                <div className="mk-mono text-[11px] text-[var(--mk-ink-3)]">
                  illustrative · not live data
                </div>
              </div>

              <div className="mk-mono mt-4 text-[14px] font-semibold text-[var(--mk-ink)]">{SAMPLE.ticket}</div>
              <div className="mk-mono mt-1.5 text-[12px] text-[var(--mk-ink-3)]">
                {SAMPLE.branch}
              </div>

              <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
                <Metric label="Files Changed" value={String(SAMPLE.files.length)} />
                <Metric label="Signatures" value={`${SAMPLE.approvals} / ${rules.twoApprovers ? 2 : 1}`} />
                <Metric label="Review Score" value={`${decision.score}/100`} />
                <Metric label="Run Cost" value={`$${(SAMPLE.costCents / 100).toFixed(2)}`} />
              </div>

              <ul className="mt-6 space-y-2">
                {SAMPLE.findings.map((f) => (
                  <li key={f.message} className="flex items-start gap-2.5 text-[13px] rounded-lg border border-[var(--mk-hairline)] bg-[var(--mk-panel)] p-2">
                    <span
                      className={cn(
                        'mk-mono mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] uppercase font-bold tracking-wider',
                        f.severity === 'high'
                          ? 'bg-[var(--mk-hold)]/20 text-[var(--mk-hold)]'
                          : f.severity === 'medium'
                            ? 'bg-[var(--mk-amber)]/20 text-[var(--mk-amber)]'
                            : 'bg-[color-mix(in_srgb,var(--mk-ink)_10%,transparent)] text-[var(--mk-ink-2)]',
                      )}
                    >
                      {f.severity}
                    </span>
                    <span className="text-[var(--mk-ink-2)]">{f.message}</span>
                  </li>
                ))}
              </ul>
            </Reveal>

            {/* Verdict */}
            <Reveal delay={0.16} className="flex flex-1 flex-col justify-center p-7 sm:p-9">
              <div
                className={cn(
                  'flex items-center gap-3 p-3 rounded-xl border transition-all duration-300',
                  decision.allowed
                    ? 'border-[var(--mk-pass)]/30 bg-[var(--mk-pass)]/10 text-[var(--mk-pass)]'
                    : 'border-[var(--mk-hold)]/30 bg-[var(--mk-hold)]/10 text-[var(--mk-hold)]',
                )}
              >
                {decision.allowed ? (
                  <Check className="h-5 w-5" strokeWidth={2.5} />
                ) : (
                  <Lock className="h-5 w-5" strokeWidth={2.5} />
                )}
                <span className="mk-mono text-[13px] font-bold uppercase tracking-[0.16em]">
                  {decision.allowed ? 'VERDICT: DEPLOY PERMITTED' : 'VERDICT: HELD AT GATE'}
                </span>
              </div>

              {decision.allowed ? (
                <div className="mt-4">
                  <p className="text-[14.5px] leading-relaxed text-[var(--mk-ink-2)]">
                    All policy assertions are met. The deploy promotes and the decision — who,
                    under which policy, against which reviewer score — is written to the audit log.
                  </p>
                </div>
              ) : (
                <>
                  <p className="mt-4 text-[14.5px] leading-relaxed text-[var(--mk-ink-2)]">
                    Execution is halted safely at the gate. The run is preserved for resolution:
                  </p>
                  <ul className="mt-3 space-y-2">
                    {decision.reasons.map((reason) => (
                      <li key={reason} className="flex items-start gap-2.5">
                        <X
                          className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--mk-hold)]"
                          strokeWidth={3}
                        />
                        <span className="mk-mono text-[12px] leading-relaxed text-[var(--mk-ink-2)]">
                          {reason}
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              )}

              <div className="mt-6 flex items-start gap-2.5 rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-panel)] p-3.5">
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mk-ember-lit)]" />
                <p className="text-[12px] leading-relaxed text-[var(--mk-ink-3)]">
                  The default policy ships permissive — one approver, no reviewer gate. Governance a
                  team did not ask for, blocking their first run, is how a pilot dies. Tightening it
                  is an explicit act.
                </p>
              </div>
            </Reveal>
          </div>
        </div>
      </div>
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="mk-readout-label">{label}</div>
      <div className="mk-readout-value mt-1.5 text-[20px]">{value}</div>
    </div>
  )
}
