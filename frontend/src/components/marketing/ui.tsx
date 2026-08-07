import type { CSSProperties, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'

/** "01 — SECTION" plate. The page's structural labelling grammar, carried over
 *  from the product UI's `.onto-label`. */
export function Eyebrow({ n, children }: { n?: string; children: ReactNode }) {
  return (
    <div className="mk-eyebrow flex items-center gap-3">
      {n ? (
        <>
          <span className="text-[var(--mk-ember-lit)]">{n}</span>
          <span aria-hidden="true" className="h-px w-6 bg-[var(--mk-hairline-lit)]" />
        </>
      ) : null}
      <span>{children}</span>
    </div>
  )
}

/** An instrument readout. Every real number on this surface uses it, so the
 *  reader learns that mono type means "this is measured". */
export function Readout({
  label,
  value,
  note,
  className,
}: {
  label: string
  value: string
  note?: string
  className?: string
}) {
  return (
    <div className={cn('px-5 py-5', className)}>
      <div className="mk-readout-label">{label}</div>
      <div className="mk-readout-value mt-2 text-[clamp(20px,2.4vw,28px)]">{value}</div>
      {note ? <div className="mt-2 text-[13px] leading-snug text-[var(--mk-ink-3)]">{note}</div> : null}
    </div>
  )
}

type ButtonProps = {
  children: ReactNode
  to?: string
  href?: string
  variant?: 'primary' | 'ghost'
  className?: string
  style?: CSSProperties
}

/**
 * The page's two buttons. Primary is the only filled, glowing element on the
 * surface — spending the accent anywhere else would cost it its meaning.
 */
export function MkButton({ children, to, href, variant = 'primary', className, style }: ButtonProps) {
  const classes = cn(
    'inline-flex items-center justify-center gap-2 rounded-md px-5 py-2.5 text-sm font-semibold transition-all duration-200',
    variant === 'primary'
      ? 'bg-[var(--mk-ember)] text-[#0a0508] hover:bg-[var(--mk-ember-lit)] mk-glow-ember'
      : 'border border-[var(--mk-hairline-lit)] text-[var(--mk-ink)] hover:border-[var(--mk-ember)] hover:text-[var(--mk-ember-lit)]',
    className,
  )

  if (to) {
    return (
      <Link to={to} className={classes} style={style}>
        {children}
      </Link>
    )
  }
  return (
    <a href={href} className={classes} style={style}>
      {children}
    </a>
  )
}

/** Section header: eyebrow, headline slot, and an optional standfirst. Used by
 *  every section so vertical rhythm is decided once. */
export function SectionHead({
  n,
  eyebrow,
  children,
  standfirst,
  align = 'left',
}: {
  n?: string
  eyebrow: string
  children: ReactNode
  standfirst?: ReactNode
  align?: 'left' | 'center'
}) {
  return (
    <div className={cn('max-w-3xl', align === 'center' && 'mx-auto text-center')}>
      <div className={cn(align === 'center' && 'flex justify-center')}>
        <Eyebrow n={n}>{eyebrow}</Eyebrow>
      </div>
      <div className="mt-6">{children}</div>
      {standfirst ? (
        <p className="mt-6 max-w-[62ch] text-[clamp(15px,1.6vw,18px)] leading-relaxed text-[var(--mk-ink-2)]">
          {standfirst}
        </p>
      ) : null}
    </div>
  )
}

/** Display headline. One class so every heading on the page shares an optical
 *  size ramp rather than each section inventing its own. */
export function Headline({
  children,
  className,
  as: Tag = 'h2',
}: {
  children: ReactNode
  className?: string
  as?: 'h1' | 'h2' | 'h3'
}) {
  return (
    <Tag className={cn('mk-display text-[clamp(30px,4.4vw,56px)]', className)}>{children}</Tag>
  )
}
