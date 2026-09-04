import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Atmosphere, MarketingFooter, MarketingNav } from '@/components/marketing/Chrome'
import { useMarketingSurface } from '@/components/marketing/hooks'
import { MkButton } from '@/components/marketing/ui'
import { Seo } from '@/components/Seo'
import { isAuthenticated } from '@/lib/auth'

/**
 * A real 404.
 *
 * The catch-all route used to be `<Navigate to="/dashboard" />`, which meant a
 * signed-out visitor who mistyped a URL or followed a stale link was bounced
 * through /dashboard to /login and shown a sign-in form with no explanation of
 * why. It also told crawlers that every wrong URL on the site was a valid
 * redirect, which is the textbook soft-404.
 */
export default function NotFoundPage() {
  useMarketingSurface()
  const authed = isAuthenticated()

  return (
    <div className="mk-root relative min-h-screen bg-[var(--mk-ground)] text-[var(--mk-ink)]">
      <Seo
        title="Page not found — Evolune OS"
        description="That page does not exist."
        /* Nothing here should ever be indexed, and a 404 must not present
           itself as the canonical version of anything. */
        noIndex
      />
      <Atmosphere />
      <MarketingNav />

      <main className="mk-shell flex min-h-screen flex-col items-center justify-center py-32 text-center">
        <p className="mk-mono text-[11px] uppercase tracking-[0.22em] text-[var(--mk-ember-lit)]">
          404
        </p>
        <h1 className="mk-display mt-6 text-[clamp(34px,6vw,68px)]">
          No such
          <br />
          route.
        </h1>
        <p className="mt-6 max-w-[46ch] text-[15px] leading-relaxed text-[var(--mk-ink-2)]">
          The page you asked for is not here. It may have moved, or the link that sent you may be
          out of date.
        </p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <MkButton to="/">
            <ArrowLeft className="h-3.5 w-3.5" /> Back to the home page
          </MkButton>
          <MkButton to={authed ? '/dashboard' : '/login'} variant="ghost">
            {authed ? 'Open the dashboard' : 'Sign in'}
          </MkButton>
        </div>

        <div className="mk-rule mt-16 w-full max-w-md" />

        <nav className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
          {[
            { label: 'How it works', to: '/how-it-works' },
            { label: 'The approval gate', to: '/the-gate' },
            { label: 'Platform', to: '/platform' },
            { label: 'Pricing', to: '/pricing' },
            { label: 'Security', to: '/security' },
          ].map((link) => (
            <Link
              key={link.label}
              to={link.to}
              className="text-sm text-[var(--mk-ink-3)] transition-colors hover:text-[var(--mk-ember-lit)]"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </main>

      <MarketingFooter />
    </div>
  )
}
