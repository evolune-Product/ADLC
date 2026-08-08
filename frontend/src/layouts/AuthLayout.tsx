import { Outlet, Link } from 'react-router-dom'
import { Check } from 'lucide-react'
import { Atmosphere, AdlcMark } from '@/components/marketing/Chrome'
import { ThemeToggle } from '@/components/ThemeToggle'
import { useMarketingSurface } from '@/components/marketing/hooks'
import { PLATFORM_FACTS } from '@/components/marketing/content'

/**
 * The seam between the marketing site and the product.
 *
 * It belongs to the marketing surface, not the app: someone arriving here has
 * just been reading a dark, cinematic page, and dropping them onto a blank
 * cream form makes it feel like they left. The form itself is unchanged — the
 * `.mk-auth` class redefines the shadcn tokens its markup already uses, so it
 * simply resolves dark (see marketing.css).
 *
 * The left column exists because a lone form on a 1440px canvas is mostly
 * empty space. It carries the one claim that matters at the moment of signing
 * up, and the reasons not to hesitate: no card, no clock, your own key.
 */

const REASSURANCES = [
  'Free forever tier — no card, no trial clock',
  'Bring your own model key, or use ours',
  'Every production deploy waits for a human',
]

export default function AuthLayout() {
  useMarketingSurface()

  return (
    <div className="mk-root mk-auth relative min-h-screen bg-[var(--mk-ground)] text-[var(--mk-ink)]">
      <Atmosphere />

      <div className="relative grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
        {/* ── Left: the argument ─────────────────────────────────────────── */}
        <aside className="relative hidden flex-col justify-between overflow-hidden border-r border-[var(--mk-hairline)] p-12 lg:flex xl:p-16">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                'radial-gradient(60% 50% at 20% 12%, rgba(232, 99, 42, 0.16) 0%, transparent 68%)',
            }}
          />

          <Link to="/" className="relative flex items-center gap-2.5">
            <AdlcMark />
            <span className="mk-display text-[15px] tracking-tight">ADLC</span>
          </Link>

          <div className="relative max-w-[26ch]">
            <h2 className="mk-display text-[clamp(30px,3.4vw,44px)]">
              Ship agent work you can <span className="mk-lit">actually approve.</span>
            </h2>

            <ul className="mt-9 space-y-3.5">
              {REASSURANCES.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <Check
                    className="mt-[3px] h-3.5 w-3.5 shrink-0 text-[var(--mk-ember-lit)]"
                    strokeWidth={3}
                  />
                  <span className="text-[14.5px] leading-snug text-[var(--mk-ink-2)]">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Counted from the codebase, same as the landing page's strip. */}
          <div className="relative grid grid-cols-3 gap-px overflow-hidden rounded-xl border border-[var(--mk-hairline)] bg-[var(--mk-hairline)]">
            {[
              { label: 'Agent roles', value: String(PLATFORM_FACTS.agentRoles) },
              { label: 'Templates', value: String(PLATFORM_FACTS.templates) },
              { label: 'Providers', value: String(PLATFORM_FACTS.modelProviders) },
            ].map((stat) => (
              <div key={stat.label} className="bg-[var(--mk-panel)] px-4 py-4">
                <div className="mk-readout-label">{stat.label}</div>
                <div className="mk-readout-value mt-1.5 text-[20px]">{stat.value}</div>
              </div>
            ))}
          </div>
        </aside>

        {/* ── Right: the form ────────────────────────────────────────────── */}
        <main className="flex flex-col">
          {/* Only shown where the left column is not — otherwise the mark
              would appear twice on the same screen. */}
          <header className="flex h-16 shrink-0 items-center border-b border-[var(--mk-hairline)] px-6 lg:hidden">
            <Link to="/" className="flex items-center gap-2.5">
              <AdlcMark />
              <span className="mk-display text-[15px] tracking-tight">ADLC</span>
            </Link>
          </header>

          <div className="flex flex-1 items-center justify-center p-6 sm:p-10">
            <div className="w-full max-w-sm">
              <Outlet />
            </div>
          </div>

          <footer className="flex shrink-0 items-center justify-between gap-4 border-t border-[var(--mk-hairline)] px-6 py-3">
            <p className="text-[11.5px] text-[var(--mk-ink-3)]">
              The governed execution layer for AI software delivery.
            </p>
            <div className="flex shrink-0 items-center gap-2">
              <Link
                to="/pricing"
                className="mk-mono text-[11px] uppercase tracking-[0.14em] text-[var(--mk-ink-3)] transition-colors hover:text-[var(--mk-ember-lit)]"
              >
                Pricing
              </Link>
              {/* Sign-in is often the first page someone lands on from a
                  bookmark, so the preference has to be reachable here too. */}
              <ThemeToggle surface="marketing" />
            </div>
          </footer>
        </main>
      </div>
    </div>
  )
}
