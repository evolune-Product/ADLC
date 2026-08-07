import { useRef } from 'react'
import type { RefObject } from 'react'
import * as THREE from 'three'
import { useFrame, useThree } from '@react-three/fiber'

/**
 * Camera movement. Three inputs, all damped, all additive:
 *
 *   pointer  — a shallow parallax that makes the scene feel like a volume you
 *              are standing inside rather than a picture of one
 *   scroll   — a dolly that pushes the camera through the system and drops it
 *              below the orbital plane as the hero leaves, so the ring opens
 *              from edge-on into a readable circle
 *   idle     — a permanent, almost imperceptible drift, so a page nobody is
 *              touching is still never quite still
 *
 * Damping is frame-rate independent (1 − e^(−k·dt)), so a 120 Hz display and a
 * throttled background tab arrive at the same position at the same wall-clock
 * moment.
 */
export function Rig({
  pointer,
  scrollProgress,
  strength = 1,
  baseZ = 8.6,
}: {
  pointer: RefObject<{ x: number; y: number }>
  scrollProgress: RefObject<number>
  strength?: number
  /** Standing distance. Pulled further back on narrow screens, where the same
   *  scene fills a much taller, narrower frame. */
  baseZ?: number
}) {
  const { camera } = useThree()
  const target = useRef(new THREE.Vector3(0, 0.6, baseZ))
  const lookAt = useRef(new THREE.Vector3(0, 0, 0))

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime
    const p = pointer.current ?? { x: 0, y: 0 }
    const scroll = scrollProgress.current ?? 0

    target.current.set(
      p.x * 0.8 * strength + Math.sin(t * 0.11) * 0.16,
      0.6 + scroll * 1.6 + -p.y * 0.4 * strength + Math.cos(t * 0.09) * 0.12,
      baseZ - scroll * 3.0,
    )

    const damp = 1 - Math.exp(-2.6 * delta)
    camera.position.lerp(target.current, damp)

    // The look-at target drifts against the parallax, which widens the
    // apparent movement without moving the camera far enough to distort the
    // composition behind the headline.
    lookAt.current.set(-p.x * 0.26, -scroll * 0.55 + p.y * 0.13, 0)
    camera.lookAt(lookAt.current)
  })

  return null
}
