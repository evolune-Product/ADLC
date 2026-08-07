import { useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { CORE_FRAG, CORE_VERT } from './shaders'
import type { ScenePalette } from './palette'

/**
 * The orchestrator at the centre of the system. Three concentric layers, each
 * moving on its own axis and at its own rate:
 *
 *   1. the displaced volume — a noise-driven surface that swells and settles
 *   2. a counter-rotating wireframe shell — reads as containment, not decoration
 *   3. an additive halo — the atmosphere the bloom pass picks up
 *
 * `activity` rises while a stage of the run is executing and falls back while
 * the run is held at the gate, so the core visibly reacts to the state machine
 * rather than performing a canned "thinking" loop.
 */
export function OrchestratorCore({
  position = [0, 0, 0],
  scale = 1,
  activity = 0,
  palette,
}: {
  position?: [number, number, number]
  scale?: number
  activity?: number
  palette: ScenePalette
}) {
  const group = useRef<THREE.Group>(null)
  const shell = useRef<THREE.Mesh>(null)
  const material = useRef<THREE.ShaderMaterial>(null)
  const halo = useRef<THREE.Mesh>(null)

  // Damped so a burst of activity eases in and decays out instead of snapping.
  const smoothed = useRef(0)

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uAmplitude: { value: 0.14 },
      uColorDeep: { value: new THREE.Color(palette.coreDeep) },
      uColorLit: { value: new THREE.Color(palette.coreLit) },
    }),
    [palette.coreDeep, palette.coreLit],
  )

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime
    smoothed.current += (activity - smoothed.current) * Math.min(1, delta * 2.4)

    if (material.current) {
      // Time advances faster while the system is working — the surface
      // literally quickens.
      material.current.uniforms.uTime.value += delta * (1 + smoothed.current * 2.2)
      material.current.uniforms.uAmplitude.value = 0.13 + smoothed.current * 0.17
    }

    if (group.current) {
      group.current.rotation.y += delta * 0.13
      group.current.position.y = position[1] + Math.sin(t * 0.42) * 0.09
    }

    if (shell.current) {
      shell.current.rotation.y -= delta * 0.24
      shell.current.rotation.x += delta * 0.07
    }

    if (halo.current) {
      const pulse = 1 + Math.sin(t * 0.9) * 0.045 + smoothed.current * 0.14
      halo.current.scale.setScalar(pulse)
      ;(halo.current.material as THREE.MeshBasicMaterial).opacity =
        0.15 + smoothed.current * 0.2
    }
  })

  return (
    <group ref={group} position={position} scale={scale}>
      {/* Displaced volume */}
      <mesh>
        <icosahedronGeometry args={[1, 32]} />
        <shaderMaterial
          ref={material}
          vertexShader={CORE_VERT}
          fragmentShader={CORE_FRAG}
          uniforms={uniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Containment shell */}
      <mesh ref={shell} scale={1.42}>
        <icosahedronGeometry args={[1, 1]} />
        <meshBasicMaterial
          color={palette.coreShell}
          wireframe
          transparent
          opacity={0.16}
          depthWrite={false}
        />
      </mesh>

      {/* Atmosphere — the surface the bloom pass blooms */}
      <mesh ref={halo} scale={2.1}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial
          color={palette.coreHalo}
          transparent
          opacity={0.15}
          side={THREE.BackSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  )
}
