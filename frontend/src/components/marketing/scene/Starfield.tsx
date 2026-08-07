import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { STARFIELD_FRAG, STARFIELD_VERT } from './shaders'
import type { ScenePalette } from './palette'

/**
 * The deep field. One draw call, one BufferGeometry, no per-star objects —
 * which is why the count can be high without costing anything measurable on
 * the CPU.
 *
 * Distributed through a hollow spherical shell rather than a cube, so there is
 * no visible box edge when the camera turns and density stays even in every
 * direction.
 */
export function Starfield({
  count = 42000,
  innerRadius = 14,
  outerRadius = 78,
  palette,
}: {
  count?: number
  innerRadius?: number
  outerRadius?: number
  palette: ScenePalette
}) {
  const points = useRef<THREE.Points>(null)
  const material = useRef<THREE.ShaderMaterial>(null)

  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const scales = new Float32Array(count)
    const seeds = new Float32Array(count)

    const [base, warm, hot, dim] = palette.starColors
    const white = new THREE.Color(base)
    const amber = new THREE.Color(warm)
    const ember = new THREE.Color(hot)
    const ash = new THREE.Color(dim)
    const tint = new THREE.Color()

    for (let i = 0; i < count; i++) {
      // acos on a uniform variable avoids the pole clustering that a naive
      // latitude/longitude pick produces.
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const radius = innerRadius + Math.cbrt(Math.random()) * (outerRadius - innerRadius)

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta) * 0.72 // flattened
      positions[i * 3 + 2] = radius * Math.cos(phi)

      const roll = Math.random()
      if (roll > 0.94) tint.copy(amber)
      else if (roll > 0.88) tint.copy(ember)
      else if (roll > 0.62) tint.copy(ash)
      else tint.copy(white)

      colors[i * 3] = tint.r
      colors[i * 3 + 1] = tint.g
      colors[i * 3 + 2] = tint.b

      // Heavily skewed towards small: a few bright particles carry the
      // composition and the rest are texture.
      scales[i] = 0.25 + Math.pow(Math.random(), 4) * 2.6
      seeds[i] = Math.random()
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geo.setAttribute('aColor', new THREE.BufferAttribute(colors, 3))
    geo.setAttribute('aScale', new THREE.BufferAttribute(scales, 1))
    geo.setAttribute('aSeed', new THREE.BufferAttribute(seeds, 1))
    return geo
  }, [count, innerRadius, outerRadius, palette])

  useEffect(() => () => geometry.dispose(), [geometry])

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uPixelRatio: { value: 1 },
      uSize: { value: 1.3 },
      uOpacity: { value: palette.starOpacity },
    }),
    [palette.starOpacity],
  )

  useFrame((state, delta) => {
    if (material.current) {
      material.current.uniforms.uTime.value += delta
      material.current.uniforms.uPixelRatio.value = state.gl.getPixelRatio()
    }
    // Barely-there rotation. At this speed it is felt rather than seen.
    if (points.current) points.current.rotation.y += delta * 0.006
  })

  return (
    <points ref={points} geometry={geometry} frustumCulled={false}>
      <shaderMaterial
        ref={material}
        vertexShader={STARFIELD_VERT}
        fragmentShader={STARFIELD_FRAG}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}

/**
 * Foreground embers: far fewer, far larger, far closer particles drifting
 * across the lens. This is the layer that sells camera movement — parallax
 * needs something near to work against.
 */
export function EmberDust({ count = 260, palette }: { count?: number; palette: ScenePalette }) {
  const ref = useRef<THREE.Points>(null)

  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 26
      positions[i * 3 + 1] = (Math.random() - 0.5) * 16
      positions[i * 3 + 2] = (Math.random() - 0.5) * 18 + 2
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    return geo
  }, [count])

  useEffect(() => () => geometry.dispose(), [geometry])

  useFrame((_, delta) => {
    if (!ref.current) return
    // Embers rise. A downward drift here read as falling ash, which is the
    // wrong story for a system that is working.
    ref.current.rotation.y += delta * 0.014
    ref.current.position.y = (ref.current.position.y + delta * 0.06) % 4
  })

  return (
    <points ref={ref} geometry={geometry} frustumCulled={false}>
      <pointsMaterial
        size={0.05}
        sizeAttenuation
        color={palette.coreLit}
        transparent
        opacity={0.42}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}
