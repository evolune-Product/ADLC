import type { CSSProperties, ReactNode } from 'react'
import { Fragment } from 'react'
import { cn } from '@/lib/utils'
import { useInView } from './hooks'

/** The elements a Reveal is allowed to render as. Deliberately a closed union
 *  rather than `ElementType`: a generic tag makes the ref and style props
 *  unresolvable, and these four cover every use on the page. */
type RevealTag = 'div' | 'span' | 'li' | 'section'

/**
 * The page's single arrival gesture: rise, unblur, settle.
 *
 * Used everywhere so the whole page shares one physical language instead of a
 * different effect per section. The animation itself lives in marketing.css —
 * this only flips `data-shown`, which means it costs no JavaScript per frame
 * and stops entirely under `prefers-reduced-motion` at the stylesheet level.
 */
export function Reveal({
  children,
  delay = 0,
  y = 26,
  blur = 8,
  className,
  as: Tag = 'div',
}: {
  children: ReactNode
  delay?: number
  y?: number
  blur?: number
  className?: string
  as?: RevealTag
}) {
  const { ref, inView } = useInView<HTMLDivElement>()

  // A union of intrinsic tags intersects their prop types, which leaves `ref`
  // unassignable to all four at once. The rendered tag is still whatever the
  // caller passed; this only tells the checker which element's props to use.
  const Component = Tag as 'div'

  return (
    <Component
      ref={ref}
      data-shown={inView}
      className={cn('mk-reveal', className)}
      style={
        {
          '--mk-reveal-delay': `${delay}s`,
          '--mk-reveal-y': `${y}px`,
          '--mk-reveal-blur': `${blur}px`,
        } as CSSProperties
      }
    >
      {children}
    </Component>
  )
}

/**
 * Word-by-word headline reveal: each word rises from behind the line above it.
 *
 * Splits on words rather than characters — character splits shred screen-reader
 * output and, at display sizes, read as a gimmick. The complete string is kept
 * in the accessibility tree via `aria-label`, and the per-word spans are hidden
 * from it.
 */
export function SplitHeading({
  text,
  className,
  as: Tag = 'h2',
  delay = 0,
  stagger = 0.055,
  highlight,
}: {
  text: string
  className?: string
  as?: 'h1' | 'h2' | 'h3'
  delay?: number
  stagger?: number
  /** Words (case-insensitive, punctuation ignored) set in the lit gradient. */
  highlight?: string[]
}) {
  const { ref, inView } = useInView<HTMLHeadingElement>({ rootMargin: '-12% 0px' })
  const words = text.split(' ')
  const normalise = (w: string) => w.toLowerCase().replace(/[^a-z0-9]/g, '')
  const lit = new Set((highlight ?? []).map(normalise))

  return (
    <Tag ref={ref} className={className} aria-label={text}>
      {words.map((word, i) => (
        <Fragment key={`${word}-${i}`}>
          <span className="mk-word-clip" aria-hidden="true">
            <span
              className={cn('mk-word', lit.has(normalise(word)) && 'mk-lit')}
              data-shown={inView}
              style={{ '--mk-word-delay': `${delay + i * stagger}s` } as CSSProperties}
            >
              {word}
            </span>
          </span>
          {/* The separator has to sit outside the clipping wrapper: inside it,
              the space lands at the end of that inline-block's only line box
              and CSS drops trailing whitespace there, running every heading
              together into one word. */}
          {i < words.length - 1 ? ' ' : ''}
        </Fragment>
      ))}
    </Tag>
  )
}

/** A hairline that draws itself in when its beat begins. The structural
 *  divider between narrative sections. */
export function DrawRule({ className, delay = 0 }: { className?: string; delay?: number }) {
  const { ref, inView } = useInView<HTMLDivElement>({ rootMargin: '-8% 0px' })

  return (
    <div ref={ref} className={cn('relative h-px w-full overflow-hidden', className)}>
      <div
        data-shown={inView}
        className="mk-draw-rule h-px w-full bg-gradient-to-r from-transparent via-[var(--mk-hairline-lit)] to-transparent"
        style={{ '--mk-reveal-delay': `${delay}s` } as CSSProperties}
      />
    </div>
  )
}
