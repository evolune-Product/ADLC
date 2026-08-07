import { useEffect, useRef, useState } from 'react'

/**
 * Turns the marketing design system on for as long as a page is mounted.
 *
 * The product UI is a light, warm-cream surface whose shadcn tokens live on
 * `:root`. The marketing tokens are scoped to `[data-surface="marketing"]` on
 * `<html>` instead of overriding those, so a user who signs in and lands on the
 * dashboard is never briefly shown a dark app — the attribute is gone before
 * the dashboard paints.
 */
export function useMarketingSurface() {
  useEffect(() => {
    const root = document.documentElement
    const previous = root.getAttribute('data-surface')
    root.setAttribute('data-surface', 'marketing')
    return () => {
      if (previous) root.setAttribute('data-surface', previous)
      else root.removeAttribute('data-surface')
    }
  }, [])
}

/**
 * Reduced motion, tracked live rather than sampled once — macOS and Windows
 * both let this change without a reload, and the WebGL scene has to be able to
 * stand down mid-session when it does.
 */
export function useReducedMotion() {
  const [reduced, setReduced] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReduced(mq.matches)
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  return reduced
}

export function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia(query)
    setMatches(mq.matches)
    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [query])

  return matches
}

/**
 * Normalised pointer position in a ref, never in state.
 *
 * The render loop reads this every frame; putting it in state would re-render
 * the whole React tree on every mouse move for a value only the camera cares
 * about.
 */
export function usePointer() {
  const pointer = useRef({ x: 0, y: 0 })

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      pointer.current.x = (e.clientX / window.innerWidth) * 2 - 1
      pointer.current.y = (e.clientY / window.innerHeight) * 2 - 1
    }
    window.addEventListener('pointermove', onMove, { passive: true })
    return () => window.removeEventListener('pointermove', onMove)
  }, [])

  return pointer
}

/** Scroll progress 0→1 across the first viewport, written on a passive
 *  listener so nothing reads layout inside the render loop. */
export function useScrollProgress() {
  const progress = useRef(0)

  useEffect(() => {
    const onScroll = () => {
      const max = window.innerHeight
      progress.current = Math.min(1, Math.max(0, window.scrollY / max))
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return progress
}

/** True once the element has entered the viewport. Latches by default: a
 *  reveal that replays every time you scroll past it becomes noise. */
export function useInView<T extends HTMLElement>(
  options?: { once?: boolean; rootMargin?: string },
) {
  const { once = true, rootMargin = '-10% 0px -10% 0px' } = options ?? {}
  const ref = useRef<T>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    // No IntersectionObserver (or a JSDOM-shaped environment): show the
    // content rather than leaving the page permanently blank.
    if (typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return
    }

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true)
          if (once) io.disconnect()
        } else if (!once) {
          setInView(false)
        }
      },
      { rootMargin },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [once, rootMargin])

  return { ref, inView }
}
