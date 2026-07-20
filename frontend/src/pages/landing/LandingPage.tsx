import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, Check, X, ChevronRight, Menu,
  Zap, Bot, ShieldCheck, LineChart, Code2, Eye, Rocket,
} from 'lucide-react'

// ─── Navbar ────────────────────────────────────────────────────────────────────

function LandingNav() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', fn, { passive: true })
    return () => window.removeEventListener('scroll', fn)
  }, [])

  const links = [
    { label: 'Product',      href: '#features' },
    { label: 'How it works', href: '#how-it-works' },
    { label: 'Workflow',     href: '#workflow' },
  ]

  return (
    <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-150 ${
      scrolled ? 'bg-background/95 backdrop-blur-sm border-b border-border shadow-sm' : 'bg-background'
    }`}>
      <div className="max-w-6xl mx-auto px-6 h-12 flex items-center gap-8">
        {/* Logo */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="w-5 h-5 rounded bg-foreground flex items-center justify-center">
            <span className="text-background text-[9px] font-black">A</span>
          </div>
          <span className="text-sm font-bold tracking-tight text-foreground">Agentic SDLC</span>
        </div>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-6 mx-auto">
          {links.map((l) => (
            <a key={l.label} href={l.href}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              {l.label}
            </a>
          ))}
        </nav>

        {/* Desktop CTA */}
        <div className="hidden md:flex items-center gap-3 shrink-0 ml-auto">
          <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Sign in
          </Link>
          <Link to="/register"
            className="flex items-center gap-1.5 px-4 py-1.5 bg-foreground text-background text-sm font-semibold rounded hover:opacity-85 transition-opacity">
            Get started <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Mobile */}
        <button onClick={() => setMobileOpen(v => !v)}
          className="md:hidden ml-auto p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors">
          {mobileOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="md:hidden bg-background border-t border-border px-6 py-4 space-y-1">
          {links.map((l) => (
            <a key={l.label} href={l.href} onClick={() => setMobileOpen(false)}
              className="block py-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
              {l.label}
            </a>
          ))}
          <div className="pt-3 border-t border-border space-y-2">
            <Link to="/login"
              className="block w-full text-center py-2 text-sm font-medium border border-border rounded text-foreground hover:bg-muted/40 transition-colors">
              Sign in
            </Link>
            <Link to="/register"
              className="block w-full text-center py-2 text-sm font-semibold bg-foreground text-background rounded hover:opacity-85 transition-opacity">
              Get started
            </Link>
          </div>
        </div>
      )}
    </header>
  )
}

// ─── Terminal mockup (animated) ────────────────────────────────────────────────

// Each entry: [delayMs, jsx renderer]
const TERM_LINES: [number, (key: string) => React.ReactNode][] = [
  [0,    (k) => (
    <p key={k} className="animate-land-fade-up" style={{ animationDuration: '0.25s' }}>
      <span className="text-[#E8632A]">$</span>{' '}
      <span className="text-white/70">agentic run --ticket PROJ-42</span>
    </p>
  )],
  [900,  (k) => (
    <p key={k} className="text-white/35 animate-land-fade-up" style={{ animationDuration: '0.25s' }}>
      → Loading project context…
    </p>
  )],
  [1700, (k) => (
    <p key={k} className="text-emerald-400 flex items-center gap-2 animate-land-fade-up" style={{ animationDuration: '0.2s' }}>
      <span className="shrink-0">✓</span> Ticket: &quot;Add OAuth 2.0 login flow&quot;
    </p>
  )],
  [2500, (k) => (
    <p key={k} className="text-emerald-400 flex items-center gap-2 animate-land-fade-up" style={{ animationDuration: '0.2s' }}>
      <span className="shrink-0">✓</span> Sprint plan: 4 tasks generated
    </p>
  )],
  [3200, (k) => (
    <p key={k} className="text-emerald-400 flex items-center gap-2 animate-land-fade-up" style={{ animationDuration: '0.2s' }}>
      <span className="shrink-0">✓</span> Branch: agent/PROJ-42-oauth-login
    </p>
  )],
  [4100, (k) => (
    <p key={k} className="text-emerald-400 flex items-center gap-2 animate-land-fade-up" style={{ animationDuration: '0.2s' }}>
      <span className="shrink-0">✓</span> 11 files committed to GitHub
    </p>
  )],
  [4900, (k) => (
    <p key={k} className="text-emerald-400 flex items-center gap-2 animate-land-fade-up" style={{ animationDuration: '0.2s' }}>
      <span className="shrink-0">✓</span> QA review: PASSED
    </p>
  )],
  [5600, (k) => (
    <p key={k} className="text-emerald-400 flex items-center gap-2 animate-land-fade-up" style={{ animationDuration: '0.2s' }}>
      <span className="shrink-0">✓</span> PR #187 opened
    </p>
  )],
  [6400, (k) => (
    <p key={k} className="text-blue-400 flex items-center gap-2 pt-0.5 animate-land-fade-up" style={{ animationDuration: '0.3s' }}>
      <span className="relative flex h-1.5 w-1.5 shrink-0">
        <span className="animate-land-ping-slow absolute inline-flex h-full w-full rounded-full bg-blue-400" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-blue-400" />
      </span>
      Awaiting your approval…
    </p>
  )],
]

const LOOP_AFTER = 10000 // ms before resetting

function TerminalCard() {
  const [visible, setVisible] = useState(0)
  const [cycle, setCycle] = useState(0)

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = []

    // reveal each line at its scheduled delay
    TERM_LINES.forEach(([delay], i) => {
      timers.push(setTimeout(() => setVisible(i + 1), delay))
    })

    // after full cycle + pause, reset to loop
    timers.push(setTimeout(() => {
      setVisible(0)
      setCycle((c) => c + 1)
    }, LOOP_AFTER))

    return () => timers.forEach(clearTimeout)
  }, [cycle])

  return (
    <div className="rounded-lg overflow-hidden border border-border shadow-xl">
      {/* Title bar */}
      <div className="flex items-center gap-1.5 px-4 py-2.5 bg-[#1c1c1c] border-b border-white/8">
        <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
        <div className="w-2.5 h-2.5 rounded-full bg-[#febc2e]" />
        <div className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
        <span className="ml-auto font-mono text-[10px] text-white/25 tracking-wide">
          agentic-sdlc — run
        </span>
      </div>

      {/* Terminal body — fixed height so layout doesn't jump on reset */}
      <div className="bg-[#0d0d0d] px-5 pt-4 pb-5 font-mono text-xs space-y-2 min-h-[230px]">
        {TERM_LINES.slice(0, visible).map(([, render], i) =>
          render(`${cycle}-${i}`)
        )}
      </div>
    </div>
  )
}

// ─── Hero ──────────────────────────────────────────────────────────────────────

function HeroSection() {
  return (
    <section className="bg-background pt-20 pb-14">
      <div className="max-w-6xl mx-auto px-6">
        <div className="max-w-3xl animate-land-fade-up">
          <p className="onto-label mb-5">Powered by Claude · Built for engineering teams</p>
          <h1 className="text-5xl sm:text-6xl font-bold text-foreground leading-[1.08] tracking-tight mb-4">
            Your software ships<br />
            <span style={{ color: '#E8632A' }}>by AI agents.</span>
          </h1>
          <p className="text-base text-muted-foreground max-w-xl leading-relaxed mb-8">
            Agentic SDLC connects your Jira, GitHub, and AI agents to autonomously plan sprints,
            write code, run QA, and open PRs — with your approval on every deploy.
          </p>

          <div className="flex items-center gap-3 flex-wrap mb-10">
            <Link to="/register"
              className="flex items-center gap-2 px-5 py-2.5 bg-foreground text-background text-sm font-semibold rounded hover:opacity-85 transition-opacity">
              <Zap className="w-4 h-4" />
              Get started free
            </Link>
            <Link to="/login"
              className="flex items-center gap-2 px-5 py-2.5 border border-border text-foreground text-sm font-medium rounded hover:bg-muted/40 transition-colors">
              Sign in to dashboard
              <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
            </Link>
          </div>

          <div className="flex items-center gap-6 flex-wrap">
            {['GitHub & Jira integration', 'Human approval gate', 'Full audit trail'].map(item => (
              <span key={item} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />{item}
              </span>
            ))}
          </div>
        </div>

        {/* Terminal preview */}
        <div className="mt-12 max-w-xl animate-land-fade-up delay-200">
          <TerminalCard />
        </div>
      </div>
    </section>
  )
}

// ─── Divider ──────────────────────────────────────────────────────────────────

function SectionDivider({ number, label }: { number: string; label: string }) {
  return (
    <div className="border-t border-border py-5 px-6">
      <p className="onto-label">{number} — {label}</p>
    </div>
  )
}

// ─── Problem / Before-After ────────────────────────────────────────────────────

function ProblemSection() {
  const withoutList = [
    'Manual sprint planning per ticket',
    'Developer writes boilerplate code',
    'No automated QA review',
    'Untracked deployment decisions',
    'Zero visibility into agent actions',
  ]
  const withList = [
    'AI-generated sprint plan in seconds',
    'Production-ready code committed automatically',
    'QA agent reviews every PR diff',
    'Every approval logged with full context',
    'Real-time run trace & audit log',
  ]

  return (
    <section className="bg-background pb-14">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid md:grid-cols-2 gap-6">
          {/* Without */}
          <div className="bg-card border border-border rounded-lg p-6">
            <div className="flex items-center gap-2 mb-5">
              <span className="text-xs font-bold text-red-500 uppercase tracking-wide">Without Agentic SDLC</span>
              <X className="w-3.5 h-3.5 text-red-400" />
            </div>
            <ul className="space-y-3">
              {withoutList.map(item => (
                <li key={item} className="flex items-start gap-2.5">
                  <X className="w-3.5 h-3.5 text-muted-foreground/50 mt-0.5 shrink-0" />
                  <span className="text-sm text-muted-foreground">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* With */}
          <div className="bg-card border border-[#E8632A]/30 rounded-lg p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-0.5 bg-[#E8632A]" />
            <div className="flex items-center gap-2 mb-5">
              <span className="text-xs font-bold text-[#E8632A] uppercase tracking-wide">With Agentic SDLC</span>
              <Check className="w-3.5 h-3.5 text-[#E8632A]" />
            </div>
            <ul className="space-y-3">
              {withList.map(item => (
                <li key={item} className="flex items-start gap-2.5">
                  <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                  <span className="text-sm text-foreground">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── Features ──────────────────────────────────────────────────────────────────

const FEATURES = [
  {
    icon: Bot,
    title: 'AI Sprint Planning',
    desc: 'Converts Jira tickets into structured sprint plans with task breakdowns, effort estimates, and technical specs — in seconds.',
    layer: 'Layer 01',
    status: 'Live',
  },
  {
    icon: Code2,
    title: 'Autonomous Code Generation',
    desc: 'Claude writes production-ready code, commits to a feature branch, and opens a PR — with your full project context baked in.',
    layer: 'Layer 02',
    status: 'Live',
  },
  {
    icon: ShieldCheck,
    title: 'Intelligent QA Review',
    desc: 'A dedicated QA agent reviews every PR diff before it reaches you. Issues found? It automatically retries the dev cycle.',
    layer: 'Layer 03',
    status: 'Live',
  },
  {
    icon: Eye,
    title: 'Human-in-the-loop',
    desc: 'Nothing ships without your eyes on it. Review the diff in our UI, approve or request changes — then the platform handles the rest.',
    layer: 'Gate',
    status: 'Always on',
  },
  {
    icon: Rocket,
    title: 'Automated Deployment',
    desc: 'Once you approve, the DevOps agent squash-merges the PR and triggers your configured deploy pipeline automatically.',
    layer: 'Layer 04',
    status: 'Live',
  },
  {
    icon: LineChart,
    title: 'Full Audit Trail',
    desc: 'Every action — sprint plan to deploy — is logged with timestamps, decisions, and diffs. Complete traceability, forever.',
    layer: 'Observe',
    status: 'Live',
  },
]

function FeaturesSection() {
  return (
    <section id="features" className="bg-background pb-14">
      <div className="max-w-6xl mx-auto px-6">
        <div className="mb-8 max-w-lg">
          <h2 className="text-3xl font-bold text-foreground tracking-tight mb-2">
            Everything your team needs.
          </h2>
          <p className="text-sm text-muted-foreground">
            Six specialized AI agents working together as a coordinated engineering team.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-border rounded-lg overflow-hidden border border-border">
          {FEATURES.map((f) => {
            const Icon = f.icon
            return (
              <div key={f.title} className="bg-card p-5 hover:bg-muted/20 transition-colors">
                <div className="flex items-start justify-between mb-4">
                  <div className="w-8 h-8 rounded bg-foreground/6 border border-border flex items-center justify-center">
                    <Icon className="w-4 h-4 text-foreground" />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="onto-label">{f.layer}</span>
                    <span className="px-1.5 py-0.5 bg-foreground text-background text-[10px] font-semibold rounded">
                      {f.status}
                    </span>
                  </div>
                </div>
                <h3 className="text-sm font-semibold text-foreground mb-1.5">{f.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

// ─── How it works ──────────────────────────────────────────────────────────────

const STEPS = [
  { n: '01', title: 'Connect your stack',   desc: 'Link GitHub and Jira with OAuth. Your repos, tickets, and branches — all in one place.' },
  { n: '02', title: 'Build your AI pod',    desc: 'Assemble Sprint, Dev, QA, and DevOps agents. Give each one skills and context from your codebase.' },
  { n: '03', title: 'Pick a ticket',        desc: 'Open any Jira ticket and hit "Run with Pod". That\'s your only input.' },
  { n: '04', title: 'AI plans & codes',     desc: 'Sprint agent creates the plan. Dev agent writes code and opens a PR. QA agent reviews it.' },
  { n: '05', title: 'You approve & ship',   desc: 'Review the PR diff in the UI. Approve and the DevOps agent merges and deploys automatically.' },
]

function HowItWorksSection() {
  return (
    <section id="how-it-works" className="bg-background pb-14">
      <div className="max-w-6xl mx-auto px-6">
        <div className="mb-8 max-w-lg">
          <h2 className="text-3xl font-bold text-foreground tracking-tight mb-2">
            Ticket to production in five steps.
          </h2>
          <p className="text-sm text-muted-foreground">
            You make two decisions: which ticket to run, and whether to approve the PR.
          </p>
        </div>

        <div className="space-y-0 border border-border rounded-lg overflow-hidden">
          {STEPS.map((step, i) => (
            <div key={step.n}
              className={`flex items-start gap-5 px-5 py-4 bg-card hover:bg-muted/20 transition-colors ${i < STEPS.length - 1 ? 'border-b border-border' : ''}`}>
              <span className="font-mono text-xs text-muted-foreground/50 w-7 pt-0.5 shrink-0">{step.n}</span>
              <div>
                <p className="text-sm font-semibold text-foreground mb-0.5">{step.title}</p>
                <p className="text-xs text-muted-foreground leading-relaxed">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Workflow pipeline ─────────────────────────────────────────────────────────

function WorkflowSection() {
  const agents = [
    { label: 'Sprint Agent', role: 'Plans' },
    { label: 'Dev Agent',    role: 'Codes' },
    { label: 'QA Agent',     role: 'Reviews' },
    { label: 'You',          role: '✓ Approve', highlight: true },
    { label: 'DevOps Agent', role: 'Deploys' },
  ]

  return (
    <section id="workflow" className="bg-background pb-14">
      <div className="max-w-6xl mx-auto px-6">
        <div className="mb-8 max-w-lg">
          <h2 className="text-3xl font-bold text-foreground tracking-tight mb-2">
            Your AI engineering team at work.
          </h2>
          <p className="text-sm text-muted-foreground">
            Each agent is a specialist. Together they form a complete SDLC pipeline.
          </p>
        </div>

        {/* Pipeline */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-0 sm:gap-0 border border-border rounded-lg overflow-hidden mb-5">
          {agents.map((a, i) => (
            <div key={a.label} className="flex sm:flex-col items-center gap-3 sm:gap-1.5 flex-1 relative">
              <div className={`flex-1 w-full px-4 py-4 text-center ${a.highlight ? 'bg-[#E8632A]/10 border-[#E8632A]/30' : 'bg-card'} ${i < agents.length - 1 ? 'border-b sm:border-b-0 sm:border-r border-border' : ''}`}>
                <p className="text-xs font-semibold text-foreground">{a.label}</p>
                <p className={`text-[11px] mt-0.5 font-medium ${a.highlight ? 'text-[#E8632A]' : 'text-muted-foreground'}`}>{a.role}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Callout */}
        <div className="bg-card border border-border rounded-lg p-5 flex items-start gap-4">
          <div className="w-1 h-full bg-[#E8632A] rounded-full self-stretch shrink-0" />
          <div>
            <p className="text-sm font-semibold text-foreground mb-1">You stay in control. Always.</p>
            <p className="text-xs text-muted-foreground leading-relaxed max-w-xl">
              The approval gate after QA is mandatory — no code ships to production without
              a human reviewer seeing the diff and clicking Approve. AI does the work, you make the call.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── CTA ───────────────────────────────────────────────────────────────────────

function CTASection() {
  return (
    <section className="bg-foreground py-14">
      <div className="max-w-6xl mx-auto px-6">
        <div className="max-w-xl">
          <p className="text-xs font-semibold text-white/40 uppercase tracking-widest mb-4">
            Ready to ship faster?
          </p>
          <h2 className="text-4xl font-bold text-white tracking-tight mb-3 leading-tight">
            Let your AI team<br />
            <span style={{ color: '#E8632A' }}>handle the sprint.</span>
          </h2>
          <p className="text-sm text-white/55 mb-8 leading-relaxed">
            Connect your repo and Jira, build your pod, and watch your backlog
            turn into merged PRs — with your approval on every single one.
          </p>

          <div className="flex flex-wrap gap-3">
            <Link to="/register"
              className="flex items-center gap-2 px-5 py-2.5 bg-white text-foreground text-sm font-semibold rounded hover:bg-white/90 transition-colors">
              <Zap className="w-4 h-4" />
              Start building free
            </Link>
            <Link to="/login"
              className="flex items-center gap-2 px-5 py-2.5 border border-white/20 text-white text-sm font-medium rounded hover:bg-white/8 transition-colors">
              I already have an account
              <ChevronRight className="w-3.5 h-3.5 opacity-60" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── Footer ────────────────────────────────────────────────────────────────────

function Footer() {
  return (
    <footer className="bg-background border-t border-border">
      <div className="max-w-6xl mx-auto px-6 h-11 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-foreground flex items-center justify-center">
            <span className="text-background text-[8px] font-black">A</span>
          </div>
          <span className="text-xs font-semibold text-foreground">Agentic SDLC</span>
          <span className="text-xs text-muted-foreground ml-2 hidden sm:inline">
            AI-powered development lifecycle platform.
          </span>
        </div>
        <div className="flex items-center gap-5">
          <Link to="/login"    className="text-xs text-muted-foreground hover:text-foreground transition-colors">Sign in</Link>
          <Link to="/register" className="text-xs text-muted-foreground hover:text-foreground transition-colors">Register</Link>
        </div>
      </div>
    </footer>
  )
}

// ─── Page ──────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <div className="bg-background min-h-screen">
      <LandingNav />

      <HeroSection />

      <div className="max-w-6xl mx-auto">
        <SectionDivider number="01" label="THE PROBLEM" />
      </div>
      <ProblemSection />

      <div className="max-w-6xl mx-auto">
        <SectionDivider number="02" label="CAPABILITIES" />
      </div>
      <FeaturesSection />

      <div className="max-w-6xl mx-auto">
        <SectionDivider number="03" label="HOW IT WORKS" />
      </div>
      <HowItWorksSection />

      <div className="max-w-6xl mx-auto">
        <SectionDivider number="04" label="PIPELINE" />
      </div>
      <WorkflowSection />

      <CTASection />
      <Footer />
    </div>
  )
}
