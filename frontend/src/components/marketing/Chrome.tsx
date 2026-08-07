import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ArrowRight, Menu, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { MkButton } from './ui'

/** Grain and vignette over the whole surface. Purely optical — it sits above
 *  everything and takes no pointer events. */
export function Atmosphere() {
  return <div className="mk-atmosphere" aria-hidden="true" />
}

/** The mark. A gate glyph: two posts and the bar that holds work between
 *  them, which is the one idea the product is built around. */
export function AdlcMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={cn('h-6 w-6', className)} aria-hidden="true">
      <rect x="2" y="3" width="2.6" height="18" rx="1" fill="var(--mk-ink)" opacity="0.55" />
      <rect x="19.4" y="3" width="2.6" height="18" rx="1" fill="var(--mk-ink)" opacity="0.55" />
      <rect x="6" y="10.7" width="12" height="2.6" rx="1.3" fill="var(--mk-ember)" />
      <circle cx="12" cy="6" r="2.1" fill="var(--mk-amber)" />
    </svg>
  )
}

const NAV_LINKS = [
  { label: 'How it works', href: '/#how-it-works' },
  { label: 'The gate', href: '/#the-gate' },
  { label: 'Platform', href: '/#platform' },
  { label: 'Pricing', href: '/pricing' },
]

export function MarketingNav() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // A menu left open across a navigation covers the page you just asked for.
  useEffect(() => setOpen(false), [location.pathname, location.hash])

  return (
    <header
      className={cn(
        'fixed inset-x-0 top-0 z-50 transition-all duration-300',
        scrolled
          ? 'border-b border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ground)_86%,transparent)] backdrop-blur-xl'
          : 'border-b border-transparent',
      )}
    >
      <div className="mk-shell flex h-16 items-center gap-8">
        <Link to="/" className="flex shrink-0 items-center gap-2.5">
          <AdlcMark />
          <span className="mk-display text-[15px] tracking-tight text-[var(--mk-ink)]">ADLC</span>
        </Link>

        <nav className="mx-auto hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) =>
            link.href.startsWith('/#') ? (
              <a
                key={link.label}
                href={link.href}
                className="text-sm text-[var(--mk-ink-2)] transition-colors hover:text-[var(--mk-ink)]"
              >
                {link.label}
              </a>
            ) : (
              <Link
                key={link.label}
                to={link.href}
                className="text-sm text-[var(--mk-ink-2)] transition-colors hover:text-[var(--mk-ink)]"
              >
                {link.label}
              </Link>
            ),
          )}
        </nav>

        <div className="ml-auto hidden shrink-0 items-center gap-4 md:flex">
          <Link
            to="/login"
            className="text-sm text-[var(--mk-ink-2)] transition-colors hover:text-[var(--mk-ink)]"
          >
            Sign in
          </Link>
          <MkButton to="/register" className="px-4 py-2">
            Start free <ArrowRight className="h-3.5 w-3.5" />
          </MkButton>
        </div>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label={open ? 'Close menu' : 'Open menu'}
          className="ml-auto rounded p-2 text-[var(--mk-ink-2)] transition-colors hover:text-[var(--mk-ink)] md:hidden"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open ? (
        <div className="border-t border-[var(--mk-hairline)] bg-[var(--mk-ground)] px-[var(--mk-gutter)] py-5 md:hidden">
          <nav className="flex flex-col gap-1">
            {NAV_LINKS.map((link) =>
              link.href.startsWith('/#') ? (
                <a
                  key={link.label}
                  href={link.href}
                  className="py-2.5 text-sm text-[var(--mk-ink-2)]"
                >
                  {link.label}
                </a>
              ) : (
                <Link key={link.label} to={link.href} className="py-2.5 text-sm text-[var(--mk-ink-2)]">
                  {link.label}
                </Link>
              ),
            )}
          </nav>
          <div className="mt-4 flex flex-col gap-2 border-t border-[var(--mk-hairline)] pt-4">
            <MkButton to="/login" variant="ghost">
              Sign in
            </MkButton>
            <MkButton to="/register">Start free</MkButton>
          </div>
        </div>
      ) : null}
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
      { label: 'Security posture', to: '/#trust' },
      { label: 'Questions', to: '/pricing#faq' },
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
    <footer className="relative border-t border-[var(--mk-hairline)] pb-14 pt-16">
      <div className="mk-shell">
        <div className="grid gap-12 md:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div>
            <Link to="/" className="flex items-center gap-2.5">
              <AdlcMark />
              <span className="mk-display text-[15px] tracking-tight">ADLC</span>
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
