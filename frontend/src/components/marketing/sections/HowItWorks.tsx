import {
  Code2,
  Cpu,
  FlaskConical,
  Lock,
  Rocket,
  ScanEye,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Reveal, SplitHeading, DrawRule } from '../Reveal'
import { Eyebrow } from '../ui'

interface AgentStep {
  n: string
  role: string
  name: string
  icon: typeof Code2
  title: string
  body: string
  tag: string
  snippet: string
  isGate?: boolean
}

/**
 * The six-step run, with the codenames the redesign gave each agent kept as
 * flavour. The titles, bodies and tags below are the same claims
 * `PIPELINE_STEPS` in `content.ts` makes — plan naming files, a real PR, a
 * test suite that has to run, a scored review, a human gate, a promoted
 * deploy — not the sandbox-container/AST/Kubernetes claims Antigravity's
 * first pass invented, none of which exist in this codebase.
 */
const STEPS: AgentStep[] = [
  {
    n: '01',
    role: 'Planner',
    name: 'Ada',
    icon: Cpu,
    title: 'A ticket becomes a file-level plan',
    body: 'Reads the ticket from Jira or Linear, reads the codebase memory for this project, and writes an explicit plan naming the files it intends to touch. Nothing is generated until the plan exists.',
    tag: 'LangGraph Planner',
    snippet: 'plan = planner.decompose(ticket, project_memory)',
  },
  {
    n: '02',
    role: 'Coder',
    name: 'Turing',
    icon: Code2,
    title: 'The plan becomes a branch',
    body: 'Works to your skills — markdown files you write that define how your team builds. Checks out a branch and opens a real pull request on GitHub or GitLab, not a patch in a chat window.',
    tag: 'Skills-driven code generation',
    snippet: 'git checkout -b agent/adlc-482-usage-caps && git commit -m "feat: token bucket"',
  },
  {
    n: '03',
    role: 'QA',
    name: 'Euler',
    icon: FlaskConical,
    title: 'The branch has to prove itself',
    body: 'Verifies that tests exist, that they run, and that they actually cover the change. A failure sends the work back to the Coder with the output attached, not to you.',
    tag: 'Test verification',
    snippet: 'pytest tests/ -q  # sent back to Coder on failure, not to you',
  },
  {
    n: '04',
    role: 'Reviewer',
    name: 'Sentinel',
    icon: ScanEye,
    title: 'The diff is scored against your rubric',
    body: 'Posts structured findings with severities and a 0–100 score (100 minus a weighted penalty per finding). It never fails a run on its own — advisory and enforcement stay separate, and only a policy turns a finding into a block.',
    tag: 'Structured review findings',
    snippet: 'score = 100 - sum(weight[f.severity] for f in findings)',
  },
  {
    n: '05',
    role: 'Human Gatekeeper',
    name: 'You / tech lead',
    icon: Lock,
    title: 'Everything stops here',
    body: 'The run holds at the approval gate. A policy decides whether the approval in front of it is even sufficient: how many approvers, what reviewer score, which paths the agent was allowed to touch, how much the run was allowed to cost.',
    tag: 'Human-in-the-loop, always',
    snippet: 'approve_run(run_id, approver="lead.engineer@yourteam.com")',
    isGate: true,
  },
  {
    n: '06',
    role: 'DevOps',
    name: 'Hermes',
    icon: Rocket,
    title: 'Then, and only then, it ships',
    body: 'Merges and promotes across dev, qa and prod, pausing for a fresh approval at every environment you have marked as gated. Every step is written to the audit log.',
    tag: 'Multi-environment promotion',
    snippet: 'promote(run_id, env="prod")  # pauses for approval if gated',
  },
]

export function HowItWorks() {
  return (
    <section className="mk-section relative" id="how-it-works">
      {/* Background radial glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute top-1/3 -right-24 h-[500px] w-[500px] rounded-full blur-[140px] opacity-15"
        style={{ background: 'radial-gradient(circle, #e8632a 0%, transparent 70%)' }}
      />

      <div className="mk-shell relative z-10">
        <div className="max-w-3xl">
          <Eyebrow>How a run works</Eyebrow>
          <SplitHeading
            as="h1"
            text="One ticket. Six steps. One of them is a person."
            highlight={['person.']}
            className="mk-display mt-6 text-[clamp(32px,4.8vw,60px)] font-bold tracking-tight"
          />
          <Reveal delay={0.15}>
            <p className="mt-6 text-[clamp(15px,1.6vw,18px)] leading-relaxed text-[var(--mk-ink-2)]">
              Every step streams live over a websocket, and every step writes to the audit log. You
              can watch a run happen, or you can read exactly what happened three months later —
              they are the same record.
            </p>
          </Reveal>
        </div>

        <DrawRule className="mt-14" />

        {/* Banner artwork */}
        <div className="mt-12 overflow-hidden rounded-2xl border border-[var(--mk-hairline)] bg-[var(--mk-panel)] shadow-2xl relative">
          <div className="absolute inset-0 bg-gradient-to-r from-[var(--mk-ground)] via-[color-mix(in_srgb,var(--mk-ground)_80%,transparent)] to-transparent z-10 p-8 sm:p-12 flex flex-col justify-center max-w-xl">
            <span className="mk-mono text-[11px] font-semibold text-[var(--mk-ember-lit)] uppercase tracking-widest">
              Autonomous pod engine
            </span>
            <h3 className="mk-display text-2xl sm:text-3xl font-bold text-[var(--mk-ink)] mt-2">
              Agents collaborate. You make the call.
            </h3>
            <p className="text-sm text-[var(--mk-ink-2)] mt-3 leading-relaxed">
              Every agent role is governed by declarative markdown skill files stored right inside
              your repository.
            </p>
          </div>
          <img
            src="/assets/neural-core.jpg"
            alt="Autonomous AI agent pod"
            className="w-full h-[280px] sm:h-[340px] object-cover object-right opacity-70"
          />
        </div>

        {/* The 6 Steps Grid */}
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((s, idx) => {
            const Icon = s.icon
            const isGate = s.isGate

            return (
              <Reveal
                key={s.n}
                delay={idx * 0.06}
                className={cn(
                  'mk-bento-card group flex flex-col justify-between',
                  isGate
                    ? 'border-[var(--mk-ember)]/50 bg-[var(--mk-ember)]/[0.04] hover:border-[var(--mk-ember)] shadow-[0_0_24px_rgba(232,99,42,0.12)]'
                    : 'hover:border-[var(--mk-hairline-lit)]',
                )}
              >
                <div>
                  <div className="flex items-center justify-between pb-4 border-b border-[var(--mk-hairline)]">
                    <div className="flex items-center gap-2.5">
                      <span className={cn(
                        'flex h-8 w-8 items-center justify-center rounded-lg text-xs font-bold',
                        isGate
                          ? 'bg-[var(--mk-ember)]/20 text-[var(--mk-ember-lit)]'
                          : 'bg-[color-mix(in_srgb,var(--mk-ink)_10%,transparent)] text-[var(--mk-ink)]',
                      )}>
                        <Icon className="h-4 w-4" />
                      </span>
                      <div>
                        <div className="text-[13px] font-semibold text-[var(--mk-ink)]">{s.role} ({s.name})</div>
                        <div className="text-[10px] mk-mono text-[var(--mk-ink-3)]">{s.tag}</div>
                      </div>
                    </div>
                    <span className={cn(
                      'mk-mono text-xs font-bold',
                      isGate ? 'text-[var(--mk-ember-lit)]' : 'text-[var(--mk-ink-3)]',
                    )}>
                      {s.n}
                    </span>
                  </div>

                  <h4 className="mt-4 text-[16px] font-semibold text-[var(--mk-ink)] leading-snug">
                    {s.title}
                  </h4>
                  <p className="mt-2.5 text-[13.5px] leading-relaxed text-[var(--mk-ink-2)]">
                    {s.body}
                  </p>
                </div>

                <div className="mt-5 pt-3 border-t border-[var(--mk-hairline)]">
                  <div className="rounded-lg bg-[var(--mk-panel-2)] p-2.5 mk-mono text-[11px] text-[var(--mk-ink-2)] overflow-x-auto">
                    <span className="text-[var(--mk-ember-lit)] mr-1.5">$</span>
                    {s.snippet}
                  </div>
                </div>
              </Reveal>
            )
          })}
        </div>
      </div>
    </section>
  )
}
