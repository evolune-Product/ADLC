import type { ReactNode } from 'react'
import { Cloud, Cpu, GitBranch, Webhook } from 'lucide-react'
import { MODEL_PROVIDERS, INTEGRATIONS } from '../content'

interface BrandItem {
  name: string
  category: string
  icon: ReactNode
}

/**
 * The trust strip: a slow, continuous drift of what this platform actually
 * plugs into, immediately under the hero.
 *
 * Deliberately not a "trusted by" customer-logo wall — this product does not
 * have customers to name yet, and a page that invents them fails the same
 * honesty test the Trust section is built around. The names and categories
 * below are `MODEL_PROVIDERS` and `INTEGRATIONS` from `content.ts` verbatim —
 * an earlier pass of this redesign named specific model versions ("Claude
 * 3.7", "GPT-4o") and vendors this codebase doesn't integrate (Docker, AWS
 * ECS); both go stale or go false in a way "Anthropic" and "GitHub" do not.
 */
const BRAND_ICON: Record<string, ReactNode> = {
  GitHub: (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
      <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  ),
  GitLab: <GitBranch className="h-4 w-4" strokeWidth={2} />,
  Linear: (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
      <path d="M3 3h4.5L19.5 15H15L3 3zm1.5 18l16.5-16.5v4.5L7.5 21H4.5z" />
    </svg>
  ),
  Jira: (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
      <path d="M11.53 2c0 2.4-1.97 4.35-4.4 4.35H2.8a.8.8 0 0 0-.8.8v4.33c0 2.4 1.97 4.35 4.4 4.35h4.33a.8.8 0 0 0 .8-.8V2z" />
      <path d="M21.2 11.48h-4.33a.8.8 0 0 0-.8.8v8.92a.8.8 0 0 0 .8.8h4.33c2.4 0 4.4-1.95 4.4-4.35v-1.82c0-2.4-1.97-4.35-4.4-4.35z" />
    </svg>
  ),
  Slack: (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
      <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z" />
    </svg>
  ),
  Webhooks: <Webhook className="h-4 w-4" strokeWidth={2} />,
  Anthropic: (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2L9.5 9.5 2 12l7.5 2.5L12 22l2.5-7.5L22 12l-7.5-2.5z" />
    </svg>
  ),
  OpenAI: (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.259 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7466-7.0729z" />
    </svg>
  ),
  'Azure OpenAI': <Cloud className="h-4 w-4" strokeWidth={2} />,
  'OpenAI-compatible': <Cpu className="h-4 w-4" strokeWidth={2} />,
  Ollama: <Cpu className="h-4 w-4" strokeWidth={2} />,
}

const BRANDS: BrandItem[] = [
  ...MODEL_PROVIDERS.map((p) => ({ name: p.name, category: p.detail, icon: BRAND_ICON[p.name] })),
  ...INTEGRATIONS.map((i) => ({ name: i.name, category: i.kind, icon: BRAND_ICON[i.name] })),
]

export function Marquee() {
  return (
    <div
      className="mk-marquee border-y border-[var(--mk-hairline)] bg-[var(--mk-panel-2)] py-5 backdrop-blur-sm"
      style={{ '--mk-marquee-duration': `${BRANDS.length * 3.2}s` } as React.CSSProperties}
    >
      <div className="mk-marquee-track">
        {[0, 1].map((copy) => (
          <div className="mk-marquee-group flex items-center gap-6" key={copy} aria-hidden={copy === 1}>
            {BRANDS.map((b, i) => (
              <div
                key={`${copy}-${b.name}-${i}`}
                className="flex items-center gap-2.5 rounded-full border border-[var(--mk-hairline)] bg-[color-mix(in_srgb,var(--mk-ink)_2%,transparent)] px-4 py-1.5 transition-all duration-300 hover:border-[var(--mk-ember)]/40 hover:bg-[color-mix(in_srgb,var(--mk-ink)_6%,transparent)]"
              >
                <span className="text-[var(--mk-ember-lit)] opacity-90">{b.icon}</span>
                <span className="text-[13px] font-medium text-[var(--mk-ink)] whitespace-nowrap">{b.name}</span>
                <span className="text-[10px] text-[var(--mk-ink-3)] uppercase mk-mono tracking-wider ml-1">
                  {b.category}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
