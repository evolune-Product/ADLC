import { useCallback, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { Canvas } from '@react-three/fiber'
import { Bloom, EffectComposer, Vignette } from '@react-three/postprocessing'
import { KernelSize } from 'postprocessing'
import { DeliveryLine } from './DeliveryLine'
import type { PipelinePhase, ProjectFn } from './pipelineTimeline'
import { GridField, Motes } from './GridField'
import { Rig } from './Rig'
import { scenePalette } from './palette'
import { useMediaQuery, usePointer } from '../hooks'

/**
 * The scene. Mounted only by the marketing pages, only on the client, only
 * when the visitor has neither asked for reduced motion nor arrived on a
 * device that would run it badly — see PipelineCanvas, which owns those
 * decisions.
 *
 * Budget discipline, because a cinematic scene that drops frames stops being
 * cinematic:
 *   - one draw call for the grid, one for the motes
 *   - the render loop is suspended entirely once the stage scrolls out of view
 *   - the post-processing chain is dropped on small screens
 *   - dpr is capped at 1.75; past that, bloom costs more than it shows
 */
export function PipelineScene({
  active = true,
  onPhase,
  onProject,
}: {
  /** False once the stage has left the viewport — freezes the loop. */
  active?: boolean
  onPhase?: (phase: PipelinePhase) => void
  onProject?: ProjectFn
}) {
  const pointer = usePointer()
  const isSmall = useMediaQuery('(max-width: 900px)')
  const isCoarse = useMediaQuery('(pointer: coarse)')

  const palette = useMemo(() => scenePalette(), [])
  const lastLabel = useRef<string | null>(null)

  const handlePhase = useCallback(
    (phase: PipelinePhase) => {
      if (phase.label !== lastLabel.current) {
        lastLabel.current = phase.label
        onPhase?.(phase)
      }
    },
    [onPhase],
  )

  return (
    <Canvas
      frameloop={active ? 'always' : 'never'}
      dpr={[1, isSmall ? 1.4 : 1.75]}
      gl={{
        // Bloom plus the grain overlay hide aliasing more cheaply than MSAA.
        antialias: false,
        alpha: true,
        powerPreference: 'high-performance',
        /*
          Tone mapping only on the dark theme.

          ACES exists here to keep the bloom's highlights from clipping. The
          light theme has no bloom, and applying it there actively hurt: the
          fog colour is the page's own cream, so any curve applied to it makes
          the fogged-out far end of the grid render as a *different* cream from
          the CSS background behind the canvas — which showed up as a bright
          horizontal band across the middle of the hero where the grid's
          horizon is. Passing the colour through untouched makes the horizon
          dissolve into the page exactly as intended.
        */
        toneMapping: palette.bloomIntensity > 0 ? THREE.ACESFilmicToneMapping : THREE.NoToneMapping,
        toneMappingExposure: palette.bloomIntensity > 0 ? 1.12 : 1,
      }}
      // Position is solved by the Rig from the graph's bounding box; this is
      // only the first frame's guess, before it settles.
      camera={{ position: [1.9, 0, 14], fov: 42, near: 0.1, far: 200 }}
      style={{ pointerEvents: 'none' }}
    >
      {/* Exponential fog dissolves both ends of the line into the page
          background, so main has no visible cut-off and the canvas has no
          edge against the DOM behind it. */}
      <fogExp2 attach="fog" args={[palette.background, palette.fogDensity]} />

      <ambientLight intensity={palette.ambient} />

      <GridField palette={palette} divisions={isSmall ? 36 : 60} />
      <Motes count={isSmall ? 70 : 170} palette={palette} />
      <DeliveryLine
        palette={palette}
        onPhase={handlePhase}
        onProject={onProject}
        vertical={isSmall}
      />

      <Rig pointer={pointer} strength={isCoarse ? 0.35 : 1} vertical={isSmall} />

      {/* Bloom is skipped entirely on the light theme rather than turned down.
          A luminance threshold of 0.18 against a cream ground selects the
          *background* — the whole frame blooms and the picture goes to milk.
          The vignette alone still seats the scene in the page. */}
      {isSmall ? (
        <></>
      ) : palette.bloomIntensity > 0 ? (
        <EffectComposer multisampling={0}>
          <Bloom
            intensity={palette.bloomIntensity}
            luminanceThreshold={0.18}
            luminanceSmoothing={0.6}
            kernelSize={KernelSize.LARGE}
            mipmapBlur
          />
          <Vignette offset={0.34} darkness={palette.vignetteDarkness} />
        </EffectComposer>
      ) : (
        <EffectComposer multisampling={0}>
          <Vignette offset={0.42} darkness={palette.vignetteDarkness} />
        </EffectComposer>
      )}
    </Canvas>
  )
}

export default PipelineScene
