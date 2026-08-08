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
  const target = useRef(new THREE.Vector3(1.0, 1.9, baseZ))
  const lookAt = useRef(new THREE.Vector3(0, 0, 0))

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime
    const p = pointer.current ?? { x: 0, y: 0 }
    const scroll = scrollProgress.current ?? 0

    target.current.set(
      // Tracks a little way down the line as the hero leaves, so the camera
      // follows the direction the work travels rather than pulling straight
      // back from it.
      1.0 + scroll * 1.8 + p.x * 0.9 * strength + Math.sin(t * 0.11) * 0.16,
      1.9 + scroll * 0.9 + -p.y * 0.4 * strength + Math.cos(t * 0.09) * 0.12,
      baseZ - scroll * 3.2,
    )

    const damp = 1 - Math.exp(-2.6 * delta)
    camera.position.lerp(target.current, damp)

    // Aimed *above* the trunk, not at it. Looking straight down the line put
    // the graph across the middle of the frame, which is where the headline
    // lives; sighting high drops the whole structure into the lower third.
    lookAt.current.set(
      1.4 - p.x * 0.3,
      1.3 - scroll * 0.7 + p.y * 0.12,
      0,
    )
    camera.lookAt(lookAt.current)
  })

  return null
}
