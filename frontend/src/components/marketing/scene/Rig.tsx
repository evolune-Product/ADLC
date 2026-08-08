import { useRef } from 'react'
import type { RefObject } from 'react'
import * as THREE from 'three'
import { useFrame, useThree } from '@react-three/fiber'
import { graphExtent } from './pipelineTimeline'

/**
 * Camera. Two jobs:
 *
 * 1. **Fit the graph to the frame, whatever shape the frame is.** The stage is
 *    a wide, short band on a desktop and a nearly square one on a phone, and a
 *    diagram that runs off the edge on one of them is worse than no diagram.
 *    The distance is solved from the graph's bounding box on every frame, so
 *    it holds at any viewport rather than at two guessed breakpoints.
 * 2. **Keep it alive.** A shallow pointer parallax so the band reads as a
 *    volume, and a permanent, almost imperceptible drift so a page nobody is
 *    touching is still never quite still.
 *
 * Damping is frame-rate independent (1 − e^(−k·dt)), so a 120 Hz display and a
 * throttled background tab arrive at the same position at the same wall-clock
 * moment.
 */
export function Rig({
  pointer,
  strength = 1,
  vertical = false,
}: {
  pointer: RefObject<{ x: number; y: number }>
  strength?: number
  vertical?: boolean
}) {
  const { camera, size } = useThree()
  const target = useRef(new THREE.Vector3())
  const lookAt = useRef(new THREE.Vector3())

  const extent = graphExtent(vertical)
  const centreX = (extent.minX + extent.maxX) / 2
  const centreY = (extent.minY + extent.maxY) / 2

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime
    const p = pointer.current ?? { x: 0, y: 0 }

    const perspective = camera as THREE.PerspectiveCamera
    const halfFov = (perspective.fov * Math.PI) / 360
    const aspect = size.width / Math.max(size.height, 1)

    // The distance at which the box's height fits, and the distance at which
    // its width fits. Whichever is further back is the one that frames both.
    const halfWidth = (extent.maxX - extent.minX) / 2
    const halfHeight = (extent.maxY - extent.minY) / 2
    const fitZ = Math.max(halfHeight / Math.tan(halfFov), halfWidth / (aspect * Math.tan(halfFov)))

    target.current.set(
      centreX + p.x * 0.55 * strength + Math.sin(t * 0.11) * 0.12,
      // Lifted above the graph's centre so the plane it stands on is visible
      // underneath it — dead-on, the grid collapses to a single line.
      centreY + (vertical ? 0.2 : 0.9) + -p.y * 0.28 * strength + Math.cos(t * 0.09) * 0.08,
      fitZ * 1.04,
    )

    const damp = 1 - Math.exp(-2.6 * delta)
    camera.position.lerp(target.current, damp)

    // The look-at target drifts against the parallax, which widens the
    // apparent movement without moving the camera far enough to distort the
    // composition or push a node out of frame.
    lookAt.current.set(centreX - p.x * 0.18, centreY + (vertical ? 0 : 0.12) + p.y * 0.07, 0)
    camera.lookAt(lookAt.current)
  })

  return null
}
