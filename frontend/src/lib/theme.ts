import { createContext, useContext } from 'react'

/**
 * One theme preference for the whole product.
 *
 * Evolune OS has two design surfaces — the dark "foundry" marketing site and the
 * light cream product UI — and until now each one was hard-wired to a single
 * palette. That is a defensible brand decision and an indefensible product one:
 * a reviewer who works nights cannot use a permanently cream dashboard, and a
 * visitor whose machine is in light mode should not be handed a black page
 * because we liked it better.
 *
 * So there is exactly **one** preference, stored once, honoured on both
 * surfaces. Each surface then decides what light and dark *mean* for it:
 *
 *   - marketing dark  → the foundry at night (near-black, one ember light)
 *   - marketing light → the drafting table  (warm cream, the same ember, ink
 *                       inverted rather than the palette inverted)
 *   - product light   → the existing cream shadcn theme, unchanged
 *   - product dark    → the `.dark` shadcn token set in index.css
 *
 * `system` is the default and follows the OS live, which is what the platform
 * conventions expect and what accessibility guidance asks for. An explicit
 * choice wins over the OS in both directions and survives a reload.
 */

export type ThemeChoice = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

/** Also read by the inline boot script in index.html. Change both together. */
export const THEME_STORAGE_KEY = 'adlc-theme'

const DARK_QUERY = '(prefers-color-scheme: dark)'

function readStoredChoice(): ThemeChoice {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  } catch {
    // Safari private mode throws on localStorage access. A themeless session is
    // a far smaller problem than a blank page.
  }
  return 'system'
}

function systemTheme(): ResolvedTheme {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light'
  return window.matchMedia(DARK_QUERY).matches ? 'dark' : 'light'
}

/**
 * The single place the DOM is touched.
 *
 * Three things, because three different consumers need to know:
 *   - `data-theme` — what the `mk-*` marketing tokens key off
 *   - `.dark` class — what Tailwind's `darkMode: ['class']` keys off
 *   - `color-scheme` — what the *browser* keys off, for form controls,
 *     scrollbars and the canvas it paints behind the page
 */
export function applyTheme(resolved: ResolvedTheme) {
  const root = document.documentElement
  root.dataset.theme = resolved
  root.classList.toggle('dark', resolved === 'dark')
  root.style.colorScheme = resolved
}

export type ThemeContextValue = {
  /** What the user asked for, including 'system'. */
  choice: ThemeChoice
  /** What that resolves to right now. Never 'system'. */
  resolved: ResolvedTheme
  setChoice: (choice: ThemeChoice) => void
  /** light → dark → system → light. What the toggle button calls. */
  cycle: () => void
}

/** The provider that fills this lives in components/ThemeProvider.tsx — kept
 *  apart so neither file mixes a component with plain exports, which is what
 *  breaks fast refresh. */
export const ThemeContext = createContext<ThemeContextValue | null>(null)

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>')
  return ctx
}

export { readStoredChoice, systemTheme, DARK_QUERY }
