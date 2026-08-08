import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import type { ScenePalette } from './palette'

/**
 * The ground the delivery line runs on.
 *
 * This replaced a star field, and the reason is the whole point of the scene:
 * a sphere surrounded by orbiting bodies reads as a solar system no matter
 * what you label it. A ruled plane receding into fog reads as an engineering
 * drawing — a bench, a schematic, a CI dashboard — which is what the subject
 * actually is.
 *
 * The grid scrolls toward the camera by exactly one cell per cycle, so the
 * motion is continuous and the plane never appears to jump.
 */
export function GridField({
  palette,
  size = 90,
  divisions = 60,
  y = -1.9,
}: {
  palette: ScenePalette
  size?: number
  divisions?: number
  y?: number
}) {
  const group = useRef<THREE.Group>(null)
  const cell = size / divisions
  // The light theme sets this to 0 and gets no ground plane at all — see the
  // note in marketing.css. Bailing out here rather than drawing an invisible
  // one saves the draw call and the per-frame scroll.
  const hidden = palette.gridOpacity <= 0

  const grid = useMemo(() => {
    const positions: number[] = []
    const half = size / 2

    for (let i = 0; i <= divisions; i++) {
      const offset = -half + i * cell
      // Lines along Z (the direction of travel)
      positions.push(offset, 0, -half, offset, 0, half)
      // Lines across
      positions.push(-half, 0, offset, half, 0, offset)
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    return geo
  }, [size, divisions, cell])

  useEffect(() => () => grid.dispose(), [grid])

  useFrame((_, delta) => {
    if (!group.current || hidden) return
    group.current.position.z = (group.current.position.z + delta * 0.55) % cell
  })

  if (hidden) return null

  return (
    <group ref={group} position={[0, y, 0]}>
      <lineSegments geometry={grid}>
        {/* Opacity comes from the theme: a hairline that reads as a whisper on
            near-black is invisible on cream, and one that reads on cream is a
            cage on near-black. */}
        <lineBasicMaterial
          color={palette.grid}
          transparent
          opacity={palette.gridOpacity}
          depthWrite={false}
        />
      </lineSegments>
    </group>
  )
}

/**
 * Sparse motes drifting through the working volume. Parallax needs something
 * near the camera to work against; without this the whole scene reads as flat
 * however far the camera moves.
 */
export function Motes({ count = 200, palette }: { count?: number; palette: ScenePalette }) {
  const ref = useRef<THREE.Points>(null)

  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 30
      positions[i * 3 + 1] = (Math.random() - 0.5) * 10
      positions[i * 3 + 2] = (Math.random() - 0.5) * 16 + 1
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    return geo
  }, [count])

  useEffect(() => () => geometry.dispose(), [geometry])

  useFrame((state, delta) => {
    if (!ref.current) return
    // Drift with the line rather than orbiting: everything in this scene moves
    // left to right, because that is the direction work travels.
    ref.current.position.x = (ref.current.position.x + delta * 0.12) % 2
    ref.current.position.y = Math.sin(state.clock.elapsedTime * 0.16) * 0.12
  })

  return (
    <points ref={ref} geometry={geometry} frustumCulled={false}>
      <pointsMaterial
        size={0.035}
        sizeAttenuation
        color={palette.agentIdle}
        transparent
        opacity={0.5}
        depthWrite={false}
      />
    </points>
  )
}
