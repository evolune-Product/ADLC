import { useCallback, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { Canvas } from '@react-three/fiber'
import { Bloom, EffectComposer, Vignette } from '@react-three/postprocessing'
import { KernelSize } from 'postprocessing'
import { OrchestratorCore } from './OrchestratorCore'
import { PipelineRing } from './PipelineRing'
import type { PipelinePhase } from './PipelineRing'
import { EmberDust, Starfield } from './Starfield'
import { Rig } from './Rig'
import { scenePalette } from './palette'
import { useMediaQuery, usePointer, useScrollProgress } from '../hooks'

/**
 * The scene. Mounted only by the marketing pages, only on the client, only
 * when the visitor has neither asked for reduced motion nor arrived on a
 * device that would run it badly — see PipelineCanvas, which owns those
 * decisions.
 *
 * Budget discipline, because a cinematic scene that drops frames stops being
 * cinematic:
 *   - one draw call for the whole star field, one for the ember dust
 *   - the render loop is suspended entirely once the hero scrolls out of view
 *   - particle counts and the post-processing chain scale down on small screens
 *   - dpr is capped at 1.75; past that, bloom costs more than it shows
 */
export function PipelineScene({
  active = true,
  onPhase,
}: {
  /** False once the hero has left the viewport — freezes the loop. */
  active?: boolean
  onPhase?: (phase: PipelinePhase) => void
}) {
  const pointer = usePointer()
  const scrollProgress = useScrollProgress()
  const isSmall = useMediaQuery('(max-width: 900px)')
  const isCoarse = useMediaQuery('(pointer: coarse)')

  const palette = useMemo(() => scenePalette(), [])

  // The core's activity is driven by the ring's own state machine, so the
  // centre of the composition quickens under load and settles while the run is
  // held at the gate. Kept in a ref-backed state that only changes on phase
  // boundaries, not per frame.
  const [activity, setActivity] = useState(0)
  const lastLabel = useRef<string | null>(null)

  const handlePhase = useCallback(
    (phase: PipelinePhase) => {
      if (phase.label !== lastLabel.current) {
        lastLabel.current = phase.label
        setActivity(phase.activity)
        onPhase?.(phase)
      }
    },
    [onPhase],
  )

  const starCount = isSmall ? 12000 : 42000
  const dustCount = isSmall ? 100 : 260
  const postProcessing = !isSmall

  return (
    <Canvas
      frameloop={active ? 'always' : 'never'}
      dpr={[1, isSmall ? 1.4 : 1.75]}
      gl={{
        // Bloom plus the grain overlay hide aliasing more cheaply than MSAA.
        antialias: false,
        alpha: true,
        powerPreference: 'high-performance',
        toneMapping: THREE.ACESFilmicToneMapping,
        toneMappingExposure: 1.1,
      }}
      camera={{ position: [0, 0.6, isSmall ? 12.4 : 8.6], fov: 46, near: 0.1, far: 200 }}
      style={{ pointerEvents: 'none' }}
    >
      {/* Exponential fog dissolves the far field into the page background, so
          the canvas has no visible edge against the DOM behind it. */}
      <fogExp2 attach="fog" args={[palette.background, palette.fogDensity]} />

      <ambientLight intensity={palette.ambient} />
      {/* One warm key from above and a cooler counter-fill, so the ring reads
          as lit by the core rather than flatly self-illuminated. */}
      <pointLight position={[5, 6, 5]} intensity={45} color={palette.agentActive} distance={40} />
      <pointLight position={[-7, -3, -4]} intensity={18} color="#5b6786" distance={40} />
      <pointLight position={[0, 0, 0]} intensity={22} color={palette.coreLit} distance={14} />

      <Starfield count={starCount} palette={palette} />
      <EmberDust count={dustCount} palette={palette} />

      {/* Set back behind the type plane and scaled down: the core is the light
          source for the composition, not a competitor to the headline sitting
          in front of it. */}
      <OrchestratorCore
        activity={activity}
        scale={isSmall ? 0.66 : 0.9}
        position={[0, -0.1, -1.2]}
        palette={palette}
      />
      <PipelineRing palette={palette} onPhase={handlePhase} />

      <Rig
        pointer={pointer}
        scrollProgress={scrollProgress}
        strength={isCoarse ? 0.35 : 1}
        baseZ={isSmall ? 12.4 : 8.6}
      />

      {postProcessing ? (
        <EffectComposer multisampling={0}>
          <Bloom
            intensity={palette.bloomIntensity}
            luminanceThreshold={0.16}
            luminanceSmoothing={0.6}
            kernelSize={KernelSize.LARGE}
            mipmapBlur
          />
          <Vignette offset={0.28} darkness={0.7} />
        </EffectComposer>
      ) : (
        <></>
      )}
    </Canvas>
  )
}

export default PipelineScene
