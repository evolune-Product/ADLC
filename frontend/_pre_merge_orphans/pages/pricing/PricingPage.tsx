import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, X, ArrowRight, Zap, ChevronDown } from 'lucide-react'

// ─── Types ─────────────────────────────────────────────────────────────────────

interface Tier {
  name: string
  monthlyPrice: number | null
  annualPrice: number | null
  priceLabel: string
  popular: boolean
  features: string[]
  cta: string
  ctaHref: string
  ctaExternal: boolean
}

// ─── Data ──────────────────────────────────────────────────────────────────────

const TIERS: Tier[] = [
  {
    name: 'Free',
    monthlyPrice: 0,
    annualPrice: 0,
    priceLabel: 'Free',
    popular: false,
    features: [
      '1 project',
      '5 agents, 1 pod, 10 skills',
      '1 GitHub + 1 Jira connection',
      'Deploy 1 project',
      'Bring Your Own LLM Key',
      'Community support',
    ],
    cta: 'Get started free',
    ctaHref: '/register',
    ctaExternal: false,
  },
  {
    name: 'Teams',
    monthlyPrice: null,
    annualPrice: null,
    priceLabel: 'Contact us',
    popular: true,
    features: [
      'Unlimited projects',
      'Unlimited agents & pods',
      'Unlimited connections',
      'Deploy all projects',
      'Org-level LLM config',
      'Email support',
    ],
    cta: 'Contact sales',
    ctaHref: 'mailto:hello@agentic-sdlc.com',
    ctaExternal: true,
  },
  {
    name: 'Enterprise',
    monthlyPrice: null,
    annualPrice: null,
    priceLabel: 'Contact us',
    popular: false,
    features: [
      'Everything in Teams',
      'Custom team permissions',
      'White-glove onboarding',
      'Dedicated support',
      'Custom SLA',
      'Priority features',
    ],
    cta: 'Contact sales',
    ctaHref: 'mailto:hello@agentic-sdlc.com',
    ctaExternal: true,
  },
]

const FEATURE_MATRIX: { feature: string; starter: string | boolean; growth: string | boolean; enterprise: string | boolean }[] = [
  { feature: 'Projects',                starter: '1',           growth: 'Unlimited',   enterprise: 'Unlimited' },
  { feature: 'Agents',                  starter: '5',           growth: 'Unlimited',   enterprise: 'Unlimited' },
  { feature: 'Pods',                    starter: '1',           growth: 'Unlimited',   enterprise: 'Unlimited' },
  { feature: 'Skills',                  starter: '10',          growth: 'Unlimited',   enterprise: 'Unlimited' },
  { feature: 'GitHub connections',      starter: '1',           growth: 'Unlimited',   enterprise: 'Unlimited' },
  { feature: 'Jira connections',        starter: '1',           growth: 'Unlimited',   enterprise: 'Unlimited' },
  { feature: 'Deployments',             starter: '1 project',   growth: 'All projects', enterprise: 'All projects' },
  { feature: 'LLM Configuration',       starter: 'BYOK',        growth: 'Org-level',   enterprise: 'Org-level' },
  { feature: 'Team members',            starter: 'Solo',        growth: 'Up to 10',    enterprise: 'Unlimited' },
  { feature: 'Custom permissions',      starter: false,         growth: false,         enterprise: true        },
  { feature: 'Human approval gate',     starter: true,          growth: true,          enterprise: true        },
  { feature: 'Auto PR + branch',        starter: true,          growth: true,          enterprise: true        },
  { feature: 'QA agent review',         starter: true,          growth: true,          enterprise: true        },
  { feature: 'Multi-env deploy',        starter: true,          growth: true,          enterprise: true        },
  { feature: 'Audit log',               starter: true,          growth: true,          enterprise: true        },
  { feature: 'Support',                 starter: 'Community',   growth: 'Email',       enterprise: 'Dedicated' },
]

const FAQS = [
  {
    q: 'What does BYOK mean?',
    a: 'Bring Your Own Key — you provide your own Anthropic (or OpenAI) API key. The platform uses your key for all AI operations, so you control costs and usage directly.',
  },
  {
    q: 'How much does the LLM usage cost?',
    a: 'On the Free plan, you pay only for your Anthropic API usage (directly to Anthropic). Teams and Enterprise plans can use org-level keys for centralized billing. Check Anthropic pricing for Claude costs.',
  },
  {
    q: 'What are the Free tier limits?',
    a: 'Free tier: 1 project, 5 agents, 1 pod, 10 skills, 1 GitHub connection, 1 Jira connection, and deployment for 1 project. Perfect for trying out the platform or solo developers.',
  },
  {
    q: 'How do I upgrade to Teams or Enterprise?',
    a: 'Contact us at hello@agentic-sdlc.com. Teams is for small teams (up to 10 members), Enterprise is for larger organizations with custom needs.',
  },
  {
    q: 'Do I need Jira to use this?',
    a: 'No. Jira is optional. You can create and run tickets manually from inside the platform. Jira integration just automates the ticket import step.',
  },
  {
    q: 'Can org members use their personal accounts?',
    a: 'No. When you accept an organization invitation, your account is locked to that organization. To use a personal workspace, create a separate account with a different email.',
  },
]

// ─── Components ────────────────────────────────────────────────────────────────

function TierCard({ tier, annual }: { tier: Tier; annual: boolean }) {
  const displayPrice = tier.monthlyPrice === null
    ? tier.priceLabel
    : tier.monthlyPrice === 0
    ? 'Free'
    : annual
    ? `$${tier.annualPrice}`
    : `$${tier.monthlyPrice}`

  const showPriceUnit = tier.monthlyPrice !== null && tier.monthlyPrice !== 0

  return (
    <div
      className={`bg-card rounded-lg border p-6 flex flex-col gap-5 relative ${
        tier.popular ? 'border-[#E8632A]/50' : 'border-border'
      }`}
    >
      {tier.popular && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-[#E8632A] rounded-t-lg" />
      )}
      {tier.popular && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-2.5 py-0.5 bg-[#E8632A] text-white text-[10px] font-bold rounded-full uppercase tracking-wide">
          Most popular
        </span>
      )}

      <div>
        <p className="onto-label mb-2">{tier.name}</p>
        <div className="flex items-baseline gap-1.5">
          <span className="text-4xl font-bold text-foreground">{displayPrice}</span>
          {showPriceUnit && (
            <span className="text-xs text-muted-foreground">/ month{annual ? ', billed annually' : ''}</span>
          )}
        </div>
        {tier.popular && annual && tier.monthlyPrice && tier.annualPrice && (
          <p className="text-xs text-[#E8632A] mt-1 font-medium">
            Save ${(tier.monthlyPrice - tier.annualPrice) * 12}/year
          </p>
        )}
      </div>

      <ul className="space-y-2.5 flex-1">
        {tier.features.map((f) => (
          <li key={f} className="flex items-start gap-2">
            <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
            <span className="text-xs text-muted-foreground">{f}</span>
          </li>
        ))}
      </ul>

      {tier.ctaExternal ? (
        <a
          href={tier.ctaHref}
          className={`block w-full text-center py-2.5 text-xs font-semibold rounded transition-opacity ${
            tier.popular
              ? 'bg-foreground text-background hover:opacity-85'
              : 'border border-border text-foreground hover:bg-muted/40'
          }`}
        >
          {tier.cta}
        </a>
      ) : (
        <Link
          to={tier.ctaHref}
          className={`block w-full text-center py-2.5 text-xs font-semibold rounded transition-opacity ${
            tier.popular
              ? 'bg-foreground text-background hover:opacity-85'
              : 'border border-border text-foreground hover:bg-muted/40'
          }`}
        >
          {tier.cta}
        </Link>
      )}
    </div>
  )
}

function FeatureCell({ value }: { value: string | boolean }) {
  if (typeof value === 'boolean') {
    return value
      ? <Check className="w-4 h-4 mx-auto text-emerald-600" />
      : <X className="w-4 h-4 mx-auto text-muted-foreground/30" />
  }
  return <span className="text-xs text-foreground font-medium">{value}</span>
}

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border-b border-border last:border-0">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between gap-4 py-4 text-left"
      >
        <span className="text-sm font-medium text-foreground">{q}</span>
        <ChevronDown className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <p className="text-xs text-muted-foreground leading-relaxed pb-4">{a}</p>
      )}
    </div>
  )
}

// ─── Page ──────────────────────────────────────────────────────────────────────

export default function PricingPage() {
  const [annual, setAnnual] = useState(false)

  return (
    <div className="bg-background min-h-screen">
      {/* Minimal nav */}
      <header className="border-b border-border bg-background/95 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 h-12 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-foreground flex items-center justify-center">
              <span className="text-background text-[9px] font-black">A</span>
            </div>
            <span className="text-sm font-bold tracking-tight text-foreground">Agentic SDLC</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Sign in
            </Link>
            <Link to="/register"
              className="flex items-center gap-1.5 px-4 py-1.5 bg-foreground text-background text-sm font-semibold rounded hover:opacity-85 transition-opacity">
              Get started <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-16 space-y-20">

        {/* Header */}
        <div className="text-center max-w-2xl mx-auto">
          <p className="onto-label mb-4">Pricing</p>
          <h1 className="text-5xl font-bold text-foreground tracking-tight mb-4 leading-tight">
            Simple, transparent pricing.
          </h1>
          <p className="text-base text-muted-foreground leading-relaxed">
            Start free. Scale as you grow. No hidden fees, no per-seat surprises on the base tier.
          </p>
        </div>

        {/* Billing toggle */}
        <div className="flex items-center justify-center gap-3">
          <span className={`text-sm ${!annual ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
            Monthly
          </span>
          <button
            onClick={() => setAnnual(v => !v)}
            className={`relative w-10 h-5 rounded-full transition-colors ${annual ? 'bg-foreground' : 'bg-border'}`}
          >
            <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-background shadow-sm transition-all duration-200 ${annual ? 'left-5' : 'left-0.5'}`} />
          </button>
          <span className={`text-sm ${annual ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
            Annual
          </span>
          {annual && (
            <span className="px-2 py-0.5 bg-[#E8632A]/10 text-[#E8632A] text-[10px] font-bold rounded uppercase tracking-wide">
              Save 20%
            </span>
          )}
        </div>

        {/* Tier cards */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5 mt-0">
          {TIERS.map((tier) => (
            <TierCard key={tier.name} tier={tier} annual={annual} />
          ))}
        </div>

        {/* Feature matrix */}
        <div>
          <div className="mb-6">
            <p className="onto-label mb-1">Full comparison</p>
            <h2 className="text-2xl font-bold text-foreground tracking-tight">Everything in detail.</h2>
          </div>
          <div className="bg-card border border-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-5 py-3 w-[40%]">
                    <span className="onto-label">Feature</span>
                  </th>
                  {TIERS.map((t) => (
                    <th key={t.name} className={`text-center px-3 py-3 ${t.popular ? 'bg-[#E8632A]/8' : ''}`}>
                      <span className={`onto-label ${t.popular ? 'text-[#E8632A]' : ''}`}>{t.name}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {FEATURE_MATRIX.map((row, i) => (
                  <tr key={row.feature} className={`${i < FEATURE_MATRIX.length - 1 ? 'border-b border-border' : ''} hover:bg-muted/20 transition-colors`}>
                    <td className="px-5 py-3 text-xs font-medium text-foreground">{row.feature}</td>
                    <td className="px-3 py-3 text-center">
                      <FeatureCell value={row.starter} />
                    </td>
                    <td className="px-3 py-3 text-center bg-[#E8632A]/5">
                      <FeatureCell value={row.growth} />
                    </td>
                    <td className="px-3 py-3 text-center">
                      <FeatureCell value={row.enterprise} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* FAQ */}
        <div>
          <div className="mb-6">
            <p className="onto-label mb-1">FAQ</p>
            <h2 className="text-2xl font-bold text-foreground tracking-tight">Common questions.</h2>
          </div>
          <div className="bg-card border border-border rounded-lg px-6">
            {FAQS.map((faq) => (
              <FaqItem key={faq.q} q={faq.q} a={faq.a} />
            ))}
          </div>
        </div>

        {/* CTA strip */}
        <div className="bg-foreground rounded-lg px-8 py-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
          <div>
            <p className="text-white font-bold text-xl mb-1">Still deciding?</p>
            <p className="text-white/60 text-sm">Start free — no credit card required. Upgrade when you need more runs.</p>
          </div>
          <Link
            to="/register"
            className="flex items-center gap-2 px-5 py-2.5 bg-white text-foreground text-sm font-semibold rounded hover:bg-white/90 transition-colors shrink-0"
          >
            <Zap className="w-4 h-4" />
            Get started free
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-background">
        <div className="max-w-5xl mx-auto px-6 h-11 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">© {new Date().getFullYear()} Agentic SDLC</p>
          <div className="flex items-center gap-4">
            <Link to="/" className="text-xs text-muted-foreground hover:text-foreground transition-colors">Home</Link>
            <Link to="/login" className="text-xs text-muted-foreground hover:text-foreground transition-colors">Sign in</Link>
            <Link to="/register" className="text-xs text-muted-foreground hover:text-foreground transition-colors">Register</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
