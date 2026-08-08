import { Monitor, Moon, Sun } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTheme } from '@/lib/theme'
import type { ThemeChoice } from '@/lib/theme'

/**
 * Theme controls, in the two shapes a product actually needs.
 *
 * `ThemeToggle` is the compact one for a nav bar: a single icon button that
 * cycles light → dark → system. `ThemeChoices` is the explicit one for a
 * settings page, where the point is to *show* that three options exist rather
 * than to save 60px.
 *
 * Both show the **choice**, not the resolved theme. A button that renders a sun
 * while the preference is "system" is lying about state — and it makes the
 * third option invisible, which is how people end up believing a site ignores
 * their OS setting.
 */

const OPTIONS: Array<{ value: ThemeChoice; icon: LucideIcon; label: string }> = [
  { value: 'light', icon: Sun, label: 'Light' },
  { value: 'dark', icon: Moon, label: 'Dark' },
  { value: 'system', icon: Monitor, label: 'System' },
]

const NEXT: Record<ThemeChoice, ThemeChoice> = {
  light: 'dark',
  dark: 'system',
  system: 'light',
}

export function ThemeToggle({
  surface = 'app',
  className,
}: {
  /** 'marketing' uses the `mk-*` tokens; 'app' uses the shadcn ones. */
  surface?: 'app' | 'marketing'
  className?: string
}) {
  const { choice, resolved, setChoice } = useTheme()
  const current = OPTIONS.find((o) => o.value === choice) ?? OPTIONS[2]
  const Icon = current.icon
  const next = NEXT[choice]

  return (
    <button
      type="button"
      onClick={() => setChoice(next)}
      // The accessible name states the current setting; the tooltip states what
      // pressing it will do. Screen reader users get the state they are in, not
      // a guess at what a sun icon means.
      aria-label={`Theme: ${current.label}${choice === 'system' ? ` (${resolved})` : ''}. Switch to ${next}.`}
      title={`Theme: ${current.label} — switch to ${next}`}
      className={cn(
        'inline-flex h-8 w-8 items-center justify-center rounded-md transition-colors',
        surface === 'marketing'
          ? 'text-[var(--mk-ink-2)] hover:bg-[var(--mk-wash-1)] hover:text-[var(--mk-ink)]'
          : 'text-muted-foreground hover:bg-foreground/5 hover:text-foreground',
        className,
      )}
    >
      <Icon className="h-4 w-4" strokeWidth={2} />
    </button>
  )
}

/** The three-way segmented control. Used on the settings page. */
export function ThemeChoices({ className }: { className?: string }) {
  const { choice, resolved, setChoice } = useTheme()

  return (
    <div
      role="radiogroup"
      aria-label="Colour theme"
      className={cn('inline-flex rounded-md border border-border bg-card p-0.5', className)}
    >
      {OPTIONS.map(({ value, icon: Icon, label }) => {
        const active = choice === value
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => setChoice(value)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs transition-colors',
              active
                ? 'bg-foreground font-medium text-background'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
            {value === 'system' && active ? (
              <span className="text-[10px] opacity-70">({resolved})</span>
            ) : null}
          </button>
        )
      })}
    </div>
  )
}
