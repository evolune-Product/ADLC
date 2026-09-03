import { useState } from 'react'
import {
  Check,
  Code2,
  FileCode2,
  GitBranch,
  Lock,
  RotateCcw,
  ShieldCheck,
  Terminal,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface Scenario {
  id: string
  title: string
  branch: string
  file: string
  score: number
  cost: string
  latency: string
  tokens: string
  diff: Array<{ type: 'add' | 'del' | 'ctx'; code: string; lineNo?: number }>
  logs: string[]
}

/**
 * A visitor-triggered interactive demo — three fixed sample tickets, the same
 * "illustrative, not live data" category as `TheGate`'s `SAMPLE` run. Nothing
 * here reads from the backend; the diff, the score and the telemetry numbers
 * are fixed per scenario so the visitor can click through plan → gate →
 * logs and see the shape of a run without one actually happening.
 */
const SCENARIOS: Scenario[] = [
  {
    id: 'ADLC-482',
    title: 'Implement Token-Bucket Rate Limiter & Project Quotas',
    branch: 'feat/adlc-482-rate-limiter',
    file: 'services/rate_limiter.py',
    score: 98,
    cost: '$0.041',
    latency: '340ms',
    tokens: '164 t/s',
    diff: [
      { type: 'ctx', code: 'class ProjectRateLimiter:', lineNo: 24 },
      { type: 'ctx', code: '    def __init__(self, redis_client: Redis):', lineNo: 25 },
      { type: 'del', code: '        self.default_rpm = 60  # static fallback', lineNo: 26 },
      { type: 'add', code: '        self.quota_engine = TenantQuotaEngine(redis_client)', lineNo: 26 },
      { type: 'add', code: '        self.audit_logger = AuditLogger()', lineNo: 27 },
      { type: 'ctx', code: '', lineNo: 28 },
      { type: 'ctx', code: '    async def check_allowance(self, tenant_id: str, cost_cents: int) -> bool:', lineNo: 29 },
      { type: 'add', code: '        allowed, remaining = await self.quota_engine.consume_tokens(', lineNo: 30 },
      { type: 'add', code: '            tenant_id=tenant_id, amount=cost_cents, window_sec=60', lineNo: 31 },
      { type: 'add', code: '        )', lineNo: 32 },
      { type: 'add', code: '        if not allowed:', lineNo: 33 },
      { type: 'add', code: '            await self.audit_logger.record_throttled_event(tenant_id)', lineNo: 34 },
      { type: 'ctx', code: '        return allowed', lineNo: 35 },
    ],
    logs: [
      '[Planner:Ada] Read ticket + project memory, wrote a file-level plan.',
      '[Coder:Turing] Generated services/rate_limiter.py, opened a pull request.',
      '[QA:Euler] Ran the test suite: 32 tests, 100% pass, 0 regressions.',
      '[Reviewer:Sentinel] Posted structured findings. Score: 98/100.',
      '[Gatekeeper] Staged at the approval gate. Awaiting human review.',
    ],
  },
  {
    id: 'ADLC-355',
    title: 'Rotate Webhook Signing Keys with Zero-Downtime',
    branch: 'security/adlc-355-key-rotation',
    file: 'services/webhook_service.py',
    score: 100,
    cost: '$0.028',
    latency: '290ms',
    tokens: '188 t/s',
    diff: [
      { type: 'ctx', code: 'def rotate_webhook_secret(org_id: str, grace_period_sec: int = 3600):', lineNo: 88 },
      { type: 'del', code: '    db.secrets.update(org_id, new_key)  # instant invalidation', lineNo: 89 },
      { type: 'add', code: '    new_secret = secrets.token_hex(32)', lineNo: 89 },
      { type: 'add', code: '    db.secrets.stage_secondary_key(org_id, new_secret, ttl=grace_period_sec)', lineNo: 90 },
      { type: 'add', code: '    notify_webhooks_key_staged(org_id, expires_in=grace_period_sec)', lineNo: 91 },
      { type: 'ctx', code: '    return {"status": "rotation_staged", "dual_verify": True}', lineNo: 92 },
    ],
    logs: [
      '[Planner:Ada] Plan: stage a secondary key with a dual-verify window.',
      '[Coder:Turing] Implemented secondary key staging in webhook_service.py.',
      '[QA:Euler] Verified zero dropped deliveries across the existing webhook test suite.',
      '[Reviewer:Sentinel] Score: 100/100.',
      '[Gatekeeper] Human authorization required before this ships.',
    ],
  },
  {
    id: 'ADLC-601',
    title: 'Real-Time Workspace Presence via Redis Pub/Sub',
    branch: 'perf/adlc-601-presence',
    file: 'services/workspace_service.py',
    score: 95,
    cost: '$0.052',
    latency: '410ms',
    tokens: '152 t/s',
    diff: [
      { type: 'ctx', code: 'async def broadcast_presence_pulse(channel_id: str, payload: dict):', lineNo: 42 },
      { type: 'del', code: '    for conn in active_connections: await conn.send_json(payload)', lineNo: 43 },
      { type: 'add', code: '    await redis_client.publish(f"presence:{channel_id}", json.dumps(payload))', lineNo: 43 },
      { type: 'ctx', code: '    metrics.increment("presence.dispatched", 1)', lineNo: 45 },
    ],
    logs: [
      '[Planner:Ada] Identified the broadcast bottleneck on a single-process socket loop.',
      '[Coder:Turing] Replaced the connection loop with Redis pub/sub.',
      '[QA:Euler] Load tested against the existing socket test suite.',
      '[Reviewer:Sentinel] Score: 95/100.',
      '[Gatekeeper] Canary release prepared. Requires deployment approval.',
    ],
  },
]

export function HeroCockpit() {
  const [scenarioIndex, setScenarioIndex] = useState(0)
  const [activeTab, setActiveTab] = useState<'diff' | 'gate' | 'logs'>('diff')
  const [isApproved, setIsApproved] = useState(false)
  const [deployHash, setDeployHash] = useState<string | null>(null)
  const [isDeploying, setIsDeploying] = useState(false)

  const scenario = SCENARIOS[scenarioIndex]

  const handleScenarioChange = (idx: number) => {
    setScenarioIndex(idx)
    setIsApproved(false)
    setDeployHash(null)
    setIsDeploying(false)
  }

  const handleApprove = () => {
    setIsDeploying(true)
    setTimeout(() => {
      setIsDeploying(false)
      setIsApproved(true)
      // Generated client-side, on the spot, as part of this interactive demo —
      // not a claim that a real audit system produced it. See the "Example
      // ledger entry" label below.
      setDeployHash(`0x${Math.random().toString(16).substring(2, 10)}${Math.random().toString(16).substring(2, 10)}`)
    }, 850)
  }

  const handleReset = () => {
    setIsApproved(false)
    setDeployHash(null)
    setIsDeploying(false)
  }

  return (
    <div className="mk-cockpit-stage mx-auto w-full max-w-5xl">
      <div className="mk-cockpit-body flex flex-col text-left">
        {/* Title / Chrome Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--mk-hairline)] bg-[var(--mk-panel-2)] px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex gap-1.5">
              <span className="h-3 w-3 rounded-full bg-[var(--mk-hold)]/80" />
              <span className="h-3 w-3 rounded-full bg-[var(--mk-amber)]/80" />
              <span className="h-3 w-3 rounded-full bg-[var(--mk-pass)]/80" />
            </div>

            <div className="hidden sm:flex items-center gap-2 border-l border-[var(--mk-hairline)] pl-3">
              <span className="mk-mono text-[11px] text-[var(--mk-ink-3)]">evolune-os</span>
              <span className="text-[var(--mk-ink-3)] opacity-50">/</span>
              <span className="mk-mono text-[11px] font-semibold text-[var(--mk-ink)]">demo-pod</span>
              <span className="text-[var(--mk-ink-3)] opacity-50">/</span>
              <span className="mk-mono text-[11px] text-[var(--mk-ember-lit)]">{scenario.id}</span>
            </div>
          </div>

          {/* Scenario Selector Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto">
            <span className="hidden lg:inline text-[11px] text-[var(--mk-ink-3)] mr-1">Demo ticket:</span>
            {SCENARIOS.map((sc, i) => (
              <button
                key={sc.id}
                type="button"
                onClick={() => handleScenarioChange(i)}
                className={cn(
                  'rounded-md px-2.5 py-1 text-[11px] font-medium transition-all duration-200 mk-mono',
                  scenarioIndex === i
                    ? 'bg-[var(--mk-ember)] text-[#0a0508] shadow-[0_0_12px_rgba(232,99,42,0.4)]'
                    : 'bg-[color-mix(in_srgb,var(--mk-ink)_4%,transparent)] text-[var(--mk-ink-2)] hover:bg-[color-mix(in_srgb,var(--mk-ink)_8%,transparent)] hover:text-[var(--mk-ink)]',
                )}
              >
                {sc.id}
              </button>
            ))}
          </div>
        </div>

        {/* Cockpit Main Grid: Pod Sidebar + Main Stage */}
        <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[460px]">
          {/* Left Column: Autonomous Agent Pod */}
          <div className="lg:col-span-4 border-b lg:border-b-0 lg:border-r border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] p-4 sm:p-5 flex flex-col justify-between gap-4">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-[var(--mk-hairline)]">
                <div className="flex items-center gap-2">
                  <div className="relative flex h-2.5 w-2.5">
                    <span className="mk-radar-ping absolute inline-flex h-full w-full rounded-full bg-[var(--mk-pass)] opacity-75" />
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[var(--mk-pass)]" />
                  </div>
                  <span className="text-[12px] font-semibold tracking-wide text-[var(--mk-ink)] uppercase mk-mono">
                    Pod Alpha (active)
                  </span>
                </div>
                <span className="text-[10.5px] rounded bg-[var(--mk-panel-2)] px-2 py-0.5 text-[var(--mk-ink-2)] mk-mono">
                  4 agents
                </span>
              </div>

              {/* Agent Cards */}
              <div className="mt-4 space-y-2.5">
                <div className="rounded-xl border border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] p-2.5 transition-colors hover:border-[var(--mk-hairline-lit)]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-[var(--mk-ember)]/15 text-[var(--mk-ember-lit)] text-[11px] font-bold">
                        A
                      </span>
                      <div>
                        <div className="text-[12px] font-medium text-[var(--mk-ink)]">Ada (Planner)</div>
                        <div className="text-[10px] text-[var(--mk-ink-3)]">Spec &amp; decomposition</div>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1 rounded bg-[var(--mk-pass)]/10 px-1.5 py-0.5 text-[9.5px] text-[var(--mk-pass)] font-medium">
                      <Check className="h-2.5 w-2.5" /> Plan ready
                    </span>
                  </div>
                </div>

                <div className="rounded-xl border border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] p-2.5 transition-colors hover:border-[var(--mk-hairline-lit)]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-cyan-500/15 text-cyan-400 text-[11px] font-bold">
                        T
                      </span>
                      <div>
                        <div className="text-[12px] font-medium text-[var(--mk-ink)]">Turing (Coder)</div>
                        <div className="text-[10px] text-[var(--mk-ink-3)]">Branch &amp; PR</div>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1 rounded bg-[var(--mk-pass)]/10 px-1.5 py-0.5 text-[9.5px] text-[var(--mk-pass)] font-medium">
                      <Check className="h-2.5 w-2.5" /> PR created
                    </span>
                  </div>
                </div>

                <div className="rounded-xl border border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] p-2.5 transition-colors hover:border-[var(--mk-hairline-lit)]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-purple-500/15 text-purple-400 text-[11px] font-bold">
                        E
                      </span>
                      <div>
                        <div className="text-[12px] font-medium text-[var(--mk-ink)]">Euler (QA)</div>
                        <div className="text-[10px] text-[var(--mk-ink-3)]">Test verification</div>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1 rounded bg-[var(--mk-pass)]/10 px-1.5 py-0.5 text-[9.5px] text-[var(--mk-pass)] font-medium">
                      <Check className="h-2.5 w-2.5" /> 32 passed
                    </span>
                  </div>
                </div>

                <div className={cn(
                  'rounded-xl border p-2.5 transition-all duration-300',
                  isApproved
                    ? 'border-[var(--mk-pass)]/40 bg-[var(--mk-pass)]/5'
                    : 'border-[var(--mk-ember)]/40 bg-[var(--mk-ember)]/5'
                )}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-amber-500/15 text-amber-400 text-[11px] font-bold">
                        S
                      </span>
                      <div>
                        <div className="text-[12px] font-medium text-[var(--mk-ink)]">Sentinel (Reviewer)</div>
                        <div className="text-[10px] text-[var(--mk-ink-3)]">Findings &amp; score</div>
                      </div>
                    </div>
                    <span className={cn(
                      'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9.5px] font-semibold mk-mono',
                      isApproved ? 'bg-[var(--mk-pass)]/15 text-[var(--mk-pass)]' : 'bg-[var(--mk-ember)]/15 text-[var(--mk-ember-lit)]'
                    )}>
                      {isApproved ? 'Approved ✓' : 'Gate armed'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Demo telemetry */}
            <div className="rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-panel-2)] p-3 mk-mono">
              <div className="flex items-center justify-between text-[10.5px] text-[var(--mk-ink-3)] mb-2">
                <span>DEMO TELEMETRY</span>
                <Zap className="h-3 w-3 text-[var(--mk-ember-lit)]" />
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] p-1.5">
                  <div className="text-[9px] text-[var(--mk-ink-3)]">SPEED</div>
                  <div className="text-[11.5px] font-bold text-[var(--mk-ink)] mt-0.5">{scenario.tokens}</div>
                </div>
                <div className="rounded bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] p-1.5">
                  <div className="text-[9px] text-[var(--mk-ink-3)]">LATENCY</div>
                  <div className="text-[11.5px] font-bold text-[var(--mk-ink)] mt-0.5">{scenario.latency}</div>
                </div>
                <div className="rounded bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] p-1.5">
                  <div className="text-[9px] text-[var(--mk-ink-3)]">COST</div>
                  <div className="text-[11.5px] font-bold text-[var(--mk-pass)] mt-0.5">{scenario.cost}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Stage: Interactive Tabbed Workspace */}
          <div className="lg:col-span-8 flex flex-col justify-between bg-[color-mix(in_srgb,var(--mk-ink)_1%,transparent)]">
            {/* Tab Bar & Status Pill */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--mk-hairline)] px-4 py-2.5 sm:px-6 bg-[color-mix(in_srgb,var(--mk-ink)_1%,transparent)]">
              <div className="flex items-center gap-1 rounded-lg bg-[color-mix(in_srgb,var(--mk-ink)_4%,transparent)] p-1">
                <button
                  type="button"
                  onClick={() => setActiveTab('diff')}
                  className={cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-1 text-[11.5px] font-medium transition-colors',
                    activeTab === 'diff'
                      ? 'bg-[color-mix(in_srgb,var(--mk-ink)_10%,transparent)] text-[var(--mk-ink)] shadow-sm'
                      : 'text-[var(--mk-ink-2)] hover:text-[var(--mk-ink)]',
                  )}
                >
                  <Code2 className="h-3.5 w-3.5 text-cyan-400" />
                  Code diff
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('gate')}
                  className={cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-1 text-[11.5px] font-medium transition-colors',
                    activeTab === 'gate'
                      ? 'bg-[color-mix(in_srgb,var(--mk-ink)_10%,transparent)] text-[var(--mk-ink)] shadow-sm'
                      : 'text-[var(--mk-ink-2)] hover:text-[var(--mk-ink)]',
                  )}
                >
                  <Lock className="h-3.5 w-3.5 text-[var(--mk-ember-lit)]" />
                  Approval gate
                  {!isApproved && (
                    <span className="h-1.5 w-1.5 rounded-full bg-[var(--mk-hold)] animate-pulse" />
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('logs')}
                  className={cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-1 text-[11.5px] font-medium transition-colors',
                    activeTab === 'logs'
                      ? 'bg-[color-mix(in_srgb,var(--mk-ink)_10%,transparent)] text-[var(--mk-ink)] shadow-sm'
                      : 'text-[var(--mk-ink-2)] hover:text-[var(--mk-ink)]',
                  )}
                >
                  <Terminal className="h-3.5 w-3.5 text-emerald-400" />
                  Agent logs
                </button>
              </div>

              {/* Status Badge */}
              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1.5 text-[11px] mk-mono text-[var(--mk-ink-2)]">
                  <GitBranch className="h-3 w-3 text-[var(--mk-ink-3)]" />
                  {scenario.branch}
                </span>
                <span className={cn(
                  'rounded-full px-2.5 py-0.5 text-[10px] font-semibold mk-mono',
                  isApproved
                    ? 'bg-[var(--mk-pass)]/15 text-[var(--mk-pass)] border border-[var(--mk-pass)]/30'
                    : 'bg-[var(--mk-ember)]/15 text-[var(--mk-ember-lit)] border border-[var(--mk-ember)]/30'
                )}>
                  {isApproved ? 'READY FOR PROD' : 'GATE HOLDING'}
                </span>
              </div>
            </div>

            {/* Main Stage Content */}
            <div className="flex-1 p-4 sm:p-6 overflow-hidden">
              {activeTab === 'diff' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-[var(--mk-hairline)]">
                    <div className="flex items-center gap-2 text-[12px] text-[var(--mk-ink-2)] mk-mono">
                      <FileCode2 className="h-4 w-4 text-[var(--mk-ember-lit)]" />
                      <span>{scenario.file}</span>
                    </div>
                    <div className="text-[11px] text-[var(--mk-ink-3)] mk-mono">
                      <span className="text-[var(--mk-pass)]">+7</span> / <span className="text-[var(--mk-hold)]">-2</span>
                    </div>
                  </div>

                  {/* Code Block */}
                  <div className="overflow-x-auto rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-panel-2)] p-3 mk-mono text-[12px] leading-relaxed">
                    {scenario.diff.map((line, idx) => (
                      <div
                        key={idx}
                        className={cn(
                          'flex items-start px-2 py-0.5 rounded font-mono',
                          line.type === 'add' && 'mk-diff-add',
                          line.type === 'del' && 'mk-diff-del',
                          line.type === 'ctx' && 'mk-diff-ctx',
                        )}
                      >
                        <span className="w-8 shrink-0 select-none text-[10px] opacity-30 text-right pr-3">
                          {line.lineNo ?? ''}
                        </span>
                        <span className="w-4 shrink-0 select-none font-bold">
                          {line.type === 'add' ? '+' : line.type === 'del' ? '-' : ' '}
                        </span>
                        <pre className="whitespace-pre overflow-x-auto text-[11.5px]">{line.code}</pre>
                      </div>
                    ))}
                  </div>

                  {/* Reviewer Note */}
                  <div className="rounded-xl border border-[var(--mk-pass)]/20 bg-[var(--mk-pass)]/[0.04] p-3 text-[12px] flex items-start gap-2.5">
                    <ShieldCheck className="h-4 w-4 text-[var(--mk-pass)] shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold text-[var(--mk-ink)]">Reviewer score: {scenario.score}/100</span>
                      <p className="text-[var(--mk-ink-2)] text-[11.5px] mt-0.5">
                        No blocking findings on this change. See the Agent logs tab for the full run.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'gate' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-[15px] font-semibold text-[var(--mk-ink)]">Policy enforcement gate</h4>
                      <p className="text-[12px] text-[var(--mk-ink-3)]">Human approval is mandatory before code touches staging or production.</p>
                    </div>
                    <span className="text-[12px] mk-mono px-2.5 py-1 rounded bg-[var(--mk-panel-2)] text-[var(--mk-ink-2)]">
                      Rulepack: standard-gate
                    </span>
                  </div>

                  {/* Policy Checklist */}
                  <div className="grid gap-2 text-[12px]">
                    <div className="flex items-center justify-between rounded-lg border border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] p-2.5">
                      <span className="text-[var(--mk-ink-2)]">1. Secret and credential scan</span>
                      <span className="text-[var(--mk-pass)] flex items-center gap-1 font-semibold mk-mono">
                        <Check className="h-3 w-3" /> PASSED
                      </span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg border border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] p-2.5">
                      <span className="text-[var(--mk-ink-2)]">2. Tests exist, run, and cover the change</span>
                      <span className="text-[var(--mk-pass)] flex items-center gap-1 font-semibold mk-mono">
                        <Check className="h-3 w-3" /> PASSED
                      </span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg border border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] p-2.5">
                      <span className="text-[var(--mk-ink-2)]">3. Reviewer score threshold &gt;= 80</span>
                      <span className="text-[var(--mk-pass)] flex items-center gap-1 font-semibold mk-mono">
                        <Check className="h-3 w-3" /> SCORE: {scenario.score}
                      </span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg border border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] p-2.5">
                      <span className="text-[var(--mk-ink-2)]">4. Run budget cap enforcement (&lt; $2.00)</span>
                      <span className="text-[var(--mk-pass)] flex items-center gap-1 font-semibold mk-mono">
                        <Check className="h-3 w-3" /> {scenario.cost} USED
                      </span>
                    </div>
                  </div>

                  {/* Deploy confirmation banner */}
                  {isApproved && deployHash ? (
                    <div className="rounded-xl border border-[var(--mk-pass)]/30 bg-[var(--mk-pass)]/10 p-4 animate-in fade-in duration-300">
                      <div className="flex items-center gap-2 text-[var(--mk-pass)] font-semibold text-[13px]">
                        <Check className="h-4 w-4" /> Production gate unlocked &amp; deployed
                      </div>
                      <div className="mt-1 text-[11.5px] text-[var(--mk-ink-2)] mk-mono break-all">
                        Example ledger entry: <span className="text-[var(--mk-ink)]">{deployHash}</span>
                      </div>
                    </div>
                  ) : null}
                </div>
              )}

              {activeTab === 'logs' && (
                <div className="rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-panel-2)] p-3 mk-mono text-[11.5px] space-y-2 h-[260px] overflow-y-auto">
                  <div className="text-[var(--mk-ink-3)] flex items-center gap-2 pb-1 border-b border-[var(--mk-hairline)]">
                    <Terminal className="h-3 w-3" />
                    <span>AGENT EXECUTION STREAM // DEMO SESSION</span>
                  </div>
                  {scenario.logs.map((log, i) => (
                    <div key={i} className="text-[var(--mk-ink-2)] leading-relaxed font-mono">
                      <span className="text-[var(--mk-ember-lit)] mr-2">&gt;</span>
                      {log}
                    </div>
                  ))}
                  {isApproved && (
                    <div className="text-[var(--mk-pass)] font-bold animate-in fade-in">
                      &gt; [Human Gatekeeper] APPROVED by lead.engineer@yourteam.com. Promoting to production.
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Bottom Action Footer with Interactive Sign-off */}
            <div className="border-t border-[var(--mk-hairline)] bg-[var(--mk-panel-2)] px-4 py-3 sm:px-6 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-[12px] text-[var(--mk-ink-3)]">
                <Lock className="h-3.5 w-3.5 text-[var(--mk-ember-lit)]" />
                <span>One-click human authorization required</span>
              </div>

              <div className="flex items-center gap-2.5">
                {isApproved ? (
                  <>
                    <span className="text-[12px] text-[var(--mk-pass)] font-medium mk-mono flex items-center gap-1">
                      <Check className="h-3.5 w-3.5" /> Deployed to production
                    </span>
                    <button
                      type="button"
                      onClick={handleReset}
                      className="inline-flex items-center gap-1.5 rounded-full border border-[var(--mk-hairline-lit)] bg-[color-mix(in_srgb,var(--mk-ink)_5%,transparent)] px-3 py-1.5 text-[11px] font-medium text-[var(--mk-ink)] hover:bg-[color-mix(in_srgb,var(--mk-ink)_10%,transparent)] transition-colors"
                    >
                      <RotateCcw className="h-3 w-3" /> Reset demo
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={handleApprove}
                    disabled={isDeploying}
                    className="mk-btn-luxury inline-flex items-center gap-2 rounded-full bg-[var(--mk-ember)] px-5 py-2 text-[13px] font-semibold text-[#0a0508] shadow-lg transition-all hover:bg-[var(--mk-ember-lit)]"
                  >
                    {isDeploying ? (
                      <>
                        <span className="h-3 w-3 animate-spin rounded-full border-2 border-[#0a0508] border-t-transparent" />
                        Processing approval...
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="h-4 w-4" />
                        Approve &amp; deploy to prod
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
