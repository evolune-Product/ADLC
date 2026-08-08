import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  DARK_QUERY,
  THEME_STORAGE_KEY,
  ThemeContext,
  applyTheme,
  readStoredChoice,
  systemTheme,
} from '@/lib/theme'
import type { ResolvedTheme, ThemeChoice } from '@/lib/theme'

/**
 * Owns the theme preference for the whole document. See src/lib/theme.ts for
 * why there is exactly one of these and what light and dark mean on each of
 * the product's two surfaces.
 *
 * Mounted in main.tsx, outside the router: the theme is a property of the
 * document, not of a route, and it must not be torn down on navigation.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  // Initialised from storage rather than from a default, so the first React
  // paint already agrees with what the boot script in index.html put on <html>.
  // Starting at a default and correcting in an effect is precisely the flash
  // that script exists to prevent.
  const [choice, setChoiceState] = useState<ThemeChoice>(readStoredChoice)
  const [system, setSystem] = useState<ResolvedTheme>(systemTheme)

  // The OS preference can change mid-session — macOS and Windows both switch on
  // a schedule — so it is tracked, not sampled once.
  useEffect(() => {
    if (!window.matchMedia) return
    const mq = window.matchMedia(DARK_QUERY)
    const onChange = (e: MediaQueryListEvent) => setSystem(e.matches ? 'dark' : 'light')
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const resolved: ResolvedTheme = choice === 'system' ? system : choice

  useEffect(() => {
    applyTheme(resolved)
  }, [resolved])

  const setChoice = useCallback((next: ThemeChoice) => {
    setChoiceState(next)
    try {
      // 'system' is written rather than removed, so "follow my OS" is itself a
      // recorded decision and not indistinguishable from never having chosen.
      localStorage.setItem(THEME_STORAGE_KEY, next)
    } catch {
      /* Safari private mode. See readStoredChoice. */
    }
  }, [])

  const cycle = useCallback(() => {
    setChoice(choice === 'light' ? 'dark' : choice === 'dark' ? 'system' : 'light')
  }, [choice, setChoice])

  const value = useMemo(
    () => ({ choice, resolved, setChoice, cycle }),
    [choice, resolved, setChoice, cycle],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
