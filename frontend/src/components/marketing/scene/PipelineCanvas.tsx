import { Suspense, lazy, useEffect, useRef, useState } from 'react'
import { StaticPipeline } from './StaticPipeline'
import type { PipelinePhase, ProjectFn } from './pipelineTimeline'
import { useReducedMotion } from '../hooks'
import { useTheme } from '@/lib/theme'

// ~500 kB of three plus the post-processing chain never reaches a visitor who
// cannot use it, and never blocks the ones who can — see the boot sequence
// below.
const PipelineScene = lazy(() => import('./PipelineScene'))

function hasWebGL() {
  try {
    const canvas = document.createElement('canvas')
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext('webgl2') || canvas.getContext('webgl')),
    )
  } catch {
    return false
  }
}

/**
 * Whether this device should be asked to run the full scene.
 *
 * Parsing three.js and then holding 60fps is a real cost; on a low-core,
 * low-memory phone that is several hundred milliseconds of blocking time for
 * an effect that would then run badly. Those devices get the static pipeline
 * instead, which carries the same information at zero animation cost.
 *
 * Both hints are advisory and absent in some browsers; missing means "assume
 * capable" rather than "assume weak".
 */
function isCapableDevice() {
  type CapabilityNavigator = Navigator & { deviceMemory?: number }
  const nav = navigator as CapabilityNavigator
  const cores = nav.hardwareConcurrency
  const memory = nav.deviceMemory
  if (typeof cores === 'number' && cores > 0 && cores < 4) return false
  if (typeof memory === 'number' && memory > 0 && memory < 4) return false
  return true
}

export function PipelineCanvas({
  className,
  onPhase,
  onProject,
}: {
  className?: string
  onPhase?: (phase: PipelinePhase) => void
  onProject?: ProjectFn
}) {
  const reduced = useReducedMotion()
  const { resolved: theme } = useTheme()
  const [webgl, setWebgl] = useState<boolean | null>(null)
  const [active, setActive] = useState(true)
  const [booted, setBooted] = useState(false)
  const hostRef = useRef<HTMLDivElement>(null)

  useEffect(() => setWebgl(hasWebGL() && isCapableDevice()), [])

  /**
   * Boot sequence. The static pipeline paints immediately; three.js is only
   * fetched and initialised once the browser is idle, so the renderer never
   * sits between the visitor and an interactive page, and the headline's LCP
   * never queues behind it.
   *
   * It is also the honest version of the story the hero tells: the system is
   * drawn first, and then it starts running.
   */
  useEffect(() => {
    if (reduced || webgl !== true) return
    type IdleWindow = Window & {
      requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => number
    }
    const w = window as IdleWindow
    if (typeof w.requestIdleCallback === 'function') {
      const id = w.requestIdleCallback(() => setBooted(true), { timeout: 1800 })
      return () => window.cancelIdleCallback?.(id)
    }
    const timer = setTimeout(() => setBooted(true), 900)
    return () => clearTimeout(timer)
  }, [reduced, webgl])

  // The render loop stops the moment the hero leaves the viewport, and when the
  // tab is backgrounded. Everything below the fold runs against an idle GPU.
  useEffect(() => {
    const el = hostRef.current
    if (!el) return

    const io = new IntersectionObserver(([entry]) => setActive(entry.isIntersecting), {
      threshold: 0,
    })
    io.observe(el)

    const onVisibility = () => {
      // Resume animation when tab becomes visible again
      setActive(!document.hidden)
    }
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      io.disconnect()
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])

  const showScene = webgl === true && !reduced && booted

  return (
    <div ref={hostRef} className={className} aria-hidden="true">
      {/* The instant first frame, and the safety net if WebGL context creation
          fails after the capability check passed. It cross-fades out as the
          real scene arrives rather than staying underneath it: both draw the
          same graph, and leaving both up rendered the pipeline twice. */}
      <div
        className="absolute inset-0 transition-opacity duration-1000"
        style={{ opacity: showScene ? 0 : 1 }}
      >
        <StaticPipeline />
      </div>

      {showScene ? (
        <Suspense fallback={null}>
          {/*
            Keyed on the theme, so switching it rebuilds the scene from scratch.

            The palette is read from CSS custom properties once, at mount, and
            then baked into three.js Color instances, material blend modes and
            the post-processing chain. Several of those cannot be changed on a
            live material without a manual `needsUpdate` dance, and a half-
            updated scene — new colours, old blending — looks worse than either
            theme. A full remount costs one WebGL context recreation on a rare,
            deliberate user action, and is simply correct.
          */}
          <div key={theme} className="mk-animate-fade-in absolute inset-0">
            <PipelineScene active={active} onPhase={onPhase} onProject={onProject} />
          </div>
        </Suspense>
      ) : null}
    </div>
  )
}
