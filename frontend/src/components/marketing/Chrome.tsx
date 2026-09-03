import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ArrowRight, Menu, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ThemeToggle } from '@/components/ThemeToggle'

/** Grain, plus two soft multi-temperature glows drifting behind the page.
 *  Purely optical — fixed, no pointer events, sits below content (z -10). */
export function Atmosphere() {
  return (
    <>
      <div className="mk-atmosphere" aria-hidden="true" />
      <div
        aria-hidden="true"
        className="pointer-events-none fixed -top-40 left-1/4 h-[600px] w-[600px] rounded-full blur-[150px] opacity-20 -z-10"
        style={{ background: 'radial-gradient(circle, #e8632a 0%, #8b5cf6 60%, transparent 80%)' }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none fixed top-1/2 -right-40 h-[500px] w-[500px] rounded-full blur-[160px] opacity-15 -z-10"
        style={{ background: 'radial-gradient(circle, #06b6d4 0%, #3b82f6 50%, transparent 80%)' }}
      />
    </>
  )
}

/**
 * The mark. Three inputs — three agents working in parallel — converge onto
 * one node before the line continues out the other side. That node is the
 * only one drawn in the brand orange: everything upstream of it can run
 * unattended, and only what reaches it is what a human is ever asked to
 * look at.
 *
 * The nodes and lines are `currentColor` rather than a marketing token, so
 * the same component works on the dark marketing surface and on the
 * product's cream ground without a second copy. Only the centre node is
 * fixed — it is legible on both, and it is the one thing this mark is
 * actually about. The soft glow ring behind it is the one purely decorative
 * addition from the redesign.
 */
export function AdlcMark({ className }: { className?: string }) {
  return (
    <div className={cn('relative flex items-center justify-center', className)}>
      <div
        aria-hidden="true"
        className="absolute -inset-1 rounded-full bg-[var(--mk-ember)]/30 blur-sm pointer-events-none"
      />
      <svg viewBox="0 0 24 24" className="h-6 w-6 relative z-10" aria-hidden="true">
        <path
          d="M4.6 6.3C8 6 11 6.5 14.1 10.3"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
          strokeLinecap="round"
        />
        <path
          d="M4.6 17.7C8 18 11 17.5 14.1 13.7"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
          strokeLinecap="round"
        />
        <path d="M3.1 12H13.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M17.5 12H20.6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="3.4" cy="5.6" r="1.4" fill="currentColor" />
        <circle cx="1.8" cy="12" r="1.4" fill="currentColor" />
        <circle cx="3.4" cy="18.4" r="1.4" fill="currentColor" />
        <circle cx="22" cy="12" r="1.4" fill="currentColor" />
        <circle cx="15.6" cy="12" r="2.1" fill="#E8632A" />
      </svg>
    </div>
  )
}

const NAV_LINKS = [
  { label: 'How it works', href: '/#how-it-works' },
  { label: 'The gate', href: '/#the-gate' },
  { label: 'Platform', href: '/#platform' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'Security', href: '/security' },
]

/** Floating pill navigation. */
export function MarketingNav() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => setOpen(false), [location.pathname, location.hash])

  return (
    <header className="mk-floating-nav">
      <nav
        className={cn(
          'mk-floating-pill px-3 py-2 sm:px-4 sm:py-2.5 transition-all duration-300',
          scrolled ? 'scale-[0.98] shadow-[0_20px_50px_rgba(0,0,0,0.35)]' : '',
        )}
      >
        <div className="flex items-center justify-between gap-2 sm:gap-6">
          <Link to="/" className="flex shrink-0 items-center gap-2.5 group">
            <AdlcMark className="transition-transform duration-200 group-hover:scale-105" />
            <span className="mk-display text-[15.5px] font-bold tracking-tight text-[var(--mk-ink)]">
              Evolune <span className="text-[var(--mk-ember-lit)]">OS</span>
            </span>
          </Link>

          <div className="hidden items-center gap-1 md:flex">
            {NAV_LINKS.map((link) => {
              const isHash = link.href.startsWith('/#')
              const isCurrent = location.pathname === link.href || (isHash && location.hash === link.href.slice(1))

              return isHash ? (
                <a
                  key={link.label}
                  href={link.href}
                  className={cn(
                    'rounded-full px-3 py-1.5 text-[13px] font-medium transition-all duration-200',
                    isCurrent
                      ? 'bg-[color-mix(in_srgb,var(--mk-ink)_10%,transparent)] text-[var(--mk-ink)]'
                      : 'text-[var(--mk-ink-2)] hover:bg-[color-mix(in_srgb,var(--mk-ink)_6%,transparent)] hover:text-[var(--mk-ink)]',
                  )}
                >
                  {link.label}
                </a>
              ) : (
                <Link
                  key={link.label}
                  to={link.href}
                  className={cn(
                    'rounded-full px-3 py-1.5 text-[13px] font-medium transition-all duration-200',
                    location.pathname === link.href
                      ? 'bg-[color-mix(in_srgb,var(--mk-ink)_10%,transparent)] text-[var(--mk-ink)]'
                      : 'text-[var(--mk-ink-2)] hover:bg-[color-mix(in_srgb,var(--mk-ink)_6%,transparent)] hover:text-[var(--mk-ink)]',
                  )}
                >
                  {link.label}
                </Link>
              )
            })}
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <ThemeToggle surface="marketing" />

            <Link
              to="/login"
              className="hidden sm:inline-flex px-3 py-1.5 text-[13px] font-medium text-[var(--mk-ink-2)] transition-colors hover:text-[var(--mk-ink)]"
            >
              Sign in
            </Link>

            <Link
              to="/register"
              className="mk-btn-luxury bg-[var(--mk-ember)] text-[#0a0508] px-4 py-1.5 sm:px-4.5 sm:py-2 text-[12.5px] sm:text-[13px] font-semibold shadow-md"
            >
              Start Free <ArrowRight className="h-3.5 w-3.5 ml-1" />
            </Link>

            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-label={open ? 'Close menu' : 'Open menu'}
              className="inline-flex h-8 w-8 items-center justify-center rounded-full text-[var(--mk-ink-2)] hover:bg-[color-mix(in_srgb,var(--mk-ink)_10%,transparent)] transition-colors md:hidden ml-1"
            >
              {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {open && (
          <div className="mt-3 pt-3 border-t border-[var(--mk-hairline)] flex flex-col gap-1 pb-2 md:hidden animate-in fade-in duration-200">
            {NAV_LINKS.map((link) =>
              link.href.startsWith('/#') ? (
                <a
                  key={link.label}
                  href={link.href}
                  className="rounded-lg px-3 py-2 text-sm text-[var(--mk-ink-2)] hover:bg-[color-mix(in_srgb,var(--mk-ink)_10%,transparent)] hover:text-[var(--mk-ink)]"
                >
                  {link.label}
                </a>
              ) : (
                <Link
                  key={link.label}
                  to={link.href}
                  className="rounded-lg px-3 py-2 text-sm text-[var(--mk-ink-2)] hover:bg-[color-mix(in_srgb,var(--mk-ink)_10%,transparent)] hover:text-[var(--mk-ink)]"
                >
                  {link.label}
                </Link>
              ),
            )}
            <div className="mt-2 pt-2 border-t border-[var(--mk-hairline)] flex items-center justify-between px-2">
              <Link to="/login" className="text-sm font-medium text-[var(--mk-ink-2)] hover:text-[var(--mk-ink)]">
                Sign in
              </Link>
              <Link
                to="/register"
                className="mk-btn-luxury bg-[var(--mk-ember)] text-[#0a0508] px-4 py-1.5 text-xs font-semibold"
              >
                Start free
              </Link>
            </div>
          </div>
        )}
      </nav>
    </header>
  )
}

const FOOTER_GROUPS = [
  {
    title: 'Product',
    links: [
      { label: 'How it works', to: '/#how-it-works' },
      { label: 'The approval gate', to: '/#the-gate' },
      { label: 'Platform', to: '/#platform' },
      { label: 'Pricing', to: '/pricing' },
    ],
  },
  {
    title: 'Platform',
    links: [
      { label: 'Model providers', to: '/#models' },
      { label: 'Integrations', to: '/#integrations' },
      { label: 'Security & data', to: '/security' },
      { label: 'Questions', to: '/#faq' },
    ],
  },
  {
    title: 'Get started',
    links: [
      { label: 'Create an account', to: '/register' },
      { label: 'Sign in', to: '/login' },
    ],
  },
]

export function MarketingFooter() {
  return (
    <footer className="relative overflow-hidden border-t border-[var(--mk-hairline)] pb-14 pt-16">
      <span aria-hidden="true" className="mk-display mk-footer-watermark">
        Evolune OS
      </span>
      <div className="mk-shell relative">
        <div className="grid gap-12 md:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div>
            <Link to="/" className="flex items-center gap-2.5">
              <AdlcMark />
              <span className="mk-display text-[15px] tracking-tight">Evolune OS</span>
            </Link>
            <p className="mt-4 max-w-[36ch] text-sm leading-relaxed text-[var(--mk-ink-3)]">
              The governed execution layer for AI software delivery. Ticket to production, with a
              gate in the middle that a human controls.
            </p>
            <p className="mk-mono mt-6 text-[11px] uppercase tracking-[0.16em] text-[var(--mk-ink-3)]">
              Evolune EdgeTech LLP
            </p>
          </div>

          {FOOTER_GROUPS.map((group) => (
            <div key={group.title}>
              <div className="mk-readout-label">{group.title}</div>
              <ul className="mt-4 space-y-2.5">
                {group.links.map((link) => (
                  <li key={link.label}>
                    {link.to.startsWith('/#') ? (
                      <a
                        href={link.to}
                        className="text-sm text-[var(--mk-ink-2)] transition-colors hover:text-[var(--mk-ember-lit)]"
                      >
                        {link.label}
                      </a>
                    ) : (
                      <Link
                        to={link.to}
                        className="text-sm text-[var(--mk-ink-2)] transition-colors hover:text-[var(--mk-ember-lit)]"
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mk-rule my-10" />

        <div className="flex flex-col gap-4 text-[12px] text-[var(--mk-ink-3)] sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} Evolune EdgeTech LLP. All rights reserved.</p>
          {/* Stated plainly rather than buried: this is a new product, and a
              page that pretends otherwise is the fastest way to lose the kind
              of buyer it is written for. */}
          <p className="max-w-[52ch] sm:text-right">
            Every figure on this site is counted from the codebase, taken from our published
            pricing model, or attributed to a named source.
          </p>
        </div>
      </div>
    </footer>
  )
}
