import { useState } from 'react'
import { Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Reveal } from '../Reveal'
import { FAQS } from '../content'

/**
 * Questions, answered at length.
 *
 * Built on native <details>/<summary> rather than a disclosure library: it is
 * keyboard-accessible, findable by the browser's in-page search even while
 * collapsed, and works before hydration. The only JavaScript here is the
 * rotation of the plus sign.
 */
export function Faq() {
  return (
    <div className="divide-y divide-[var(--mk-hairline)] border-y border-[var(--mk-hairline)]">
      {FAQS.map((faq, i) => (
        <Reveal key={faq.q} delay={Math.min(i, 4) * 0.05}>
          <FaqItem q={faq.q} a={faq.a} />
        </Reveal>
      ))}
    </div>
  )
}

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)

  return (
    <details
      className="group"
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
    >
      <summary className="flex cursor-pointer list-none items-start justify-between gap-6 py-6 [&::-webkit-details-marker]:hidden">
        <span className="text-[16px] font-medium leading-snug text-[var(--mk-ink)]">{q}</span>
        <Plus
          aria-hidden="true"
          className={cn(
            'mt-1 h-4 w-4 shrink-0 text-[var(--mk-ink-3)] transition-transform duration-300',
            open && 'rotate-45 text-[var(--mk-ember-lit)]',
          )}
        />
      </summary>
      <p className="max-w-[72ch] pb-7 text-[14.5px] leading-relaxed text-[var(--mk-ink-2)]">{a}</p>
    </details>
  )
}
