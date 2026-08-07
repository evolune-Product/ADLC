import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import type { ScenePalette } from './palette'

/**
 * The run, as a body moving through a system.
 *
 * Six slots on one orbital plane: the five agent roles a pod actually executes
 * in order, and — between the Reviewer and the DevOps agent — the approval
 * gate. A work packet travels the ring, warming each agent as it arrives,
 * **stops dead at the gate**, and only continues once it is released.
 *
 * That pause is the entire product. Everything else in the scene exists to
 * make it legible: this is not an ambient background that happens to be
 * circular, it is the state machine in `run_tasks.py` drawn at 60fps.
 */

export type PipelinePhase = {
  /** Machine-ish label for the readout under the headline. */
  label: string
  /** Drives the readout's colour. */
  kind: 'running' | 'held' | 'passed' | 'idle'
  /** Feeds the orchestrator core's activity, so it quickens under load. */
  activity: number
}

const STAGES = [
  { key: 'sprint', name: 'Planner', label: 'PLANNER · decomposing ticket' },
  { key: 'dev', name: 'Coder', label: 'CODER · writing changes' },
  { key: 'qa', name: 'QA', label: 'QA · running tests' },
  { key: 'reviewer', name: 'Reviewer', label: 'REVIEWER · scoring diff' },
  { key: 'devops', name: 'DevOps', label: 'DEVOPS · promoting to prod' },
] as const

/** Slot 4 is the gate; the five agents take slots 0–3 and 5. */
const SLOT_OF_STAGE = [0, 1, 2, 3, 5]
const GATE_SLOT = 4
const SLOT_COUNT = 6
const RADIUS = 3.15

/** Angle of a slot on the ring, in radians. */
const slotAngle = (slot: number) => -Math.PI / 2 + (slot * Math.PI * 2) / SLOT_COUNT

type Phase =
  | { type: 'dwell'; stage: number; duration: number }
  | { type: 'travel'; from: number; to: number; duration: number }
  | { type: 'hold'; duration: number }
  | { type: 'release'; duration: number }
  | { type: 'reset'; duration: number }

/**
 * One loop of the timeline. Durations are in seconds and deliberately
 * asymmetric — the hold at the gate is the longest single beat on the ring,
 * because in a real run it is by far the longest wait.
 */
const TIMELINE: Phase[] = [
  { type: 'dwell', stage: 0, duration: 1.5 },
  { type: 'travel', from: 0, to: 1, duration: 1.0 },
  { type: 'dwell', stage: 1, duration: 1.8 },
  { type: 'travel', from: 1, to: 2, duration: 1.0 },
  { type: 'dwell', stage: 2, duration: 1.5 },
  { type: 'travel', from: 2, to: 3, duration: 1.0 },
  { type: 'dwell', stage: 3, duration: 1.7 },
  { type: 'travel', from: 3, to: GATE_SLOT, duration: 0.85 },
  { type: 'hold', duration: 3.0 },
  { type: 'release', duration: 1.0 },
  { type: 'dwell', stage: 4, duration: 1.6 },
  { type: 'reset', duration: 1.5 },
]

const TOTAL = TIMELINE.reduce((sum, p) => sum + p.duration, 0)

function phaseAt(elapsed: number) {
  let t = elapsed % TOTAL
  for (let i = 0; i < TIMELINE.length; i++) {
    const phase = TIMELINE[i]
    if (t < phase.duration) return { phase, local: t / phase.duration, index: i }
    t -= phase.duration
  }
  const last = TIMELINE[TIMELINE.length - 1]
  return { phase: last, local: 1, index: TIMELINE.length - 1 }
}

function describe(phase: Phase): PipelinePhase {
  switch (phase.type) {
    case 'dwell':
      return { label: STAGES[phase.stage].label, kind: 'running', activity: 1 }
    case 'travel':
      return { label: 'HANDOFF · passing artefacts', kind: 'running', activity: 0.45 }
    case 'hold':
      return { label: 'HELD · awaiting human approval', kind: 'held', activity: 0.08 }
    case 'release':
      return { label: 'APPROVED · policy satisfied', kind: 'passed', activity: 0.7 }
    case 'reset':
      return { label: 'MERGED · run complete', kind: 'passed', activity: 0.2 }
  }
}

/** Slot the packet occupies, as a float so travel is a smooth interpolation. */
function packetSlot(phase: Phase, local: number): number {
  switch (phase.type) {
    case 'dwell':
      return SLOT_OF_STAGE[phase.stage]
    case 'travel':
      return phase.from + (phase.to - phase.from) * easeInOut(local)
    case 'hold':
      return GATE_SLOT
    case 'release':
      return GATE_SLOT + (SLOT_OF_STAGE[4] - GATE_SLOT) * easeInOut(local)
    case 'reset':
      return SLOT_OF_STAGE[4]
  }
}

const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2)

export function PipelineRing({
  palette,
  onPhase,
}: {
  palette: ScenePalette
  /** Fires only when the phase actually changes, not every frame. */
  onPhase?: (phase: PipelinePhase) => void
}) {
  const group = useRef<THREE.Group>(null)
  const packet = useRef<THREE.Group>(null)
  const trail = useRef<THREE.Mesh>(null)
  const gate = useRef<THREE.Group>(null)
  const gateBarrier = useRef<THREE.Mesh>(null)
  const agents = useRef<Array<THREE.Group | null>>([])
  const elapsed = useRef(0)
  const lastPhaseIndex = useRef(-1)

  const colors = useMemo(
    () => ({
      idle: new THREE.Color(palette.agentIdle),
      active: new THREE.Color(palette.agentActive),
      packet: new THREE.Color(palette.packet),
      hold: new THREE.Color(palette.gateHold),
      pass: new THREE.Color(palette.gatePass),
      gateIdle: new THREE.Color(palette.gateIdle),
    }),
    [palette],
  )

  // Scratch objects, allocated once. Allocating a Vector3 inside useFrame
  // means ~60 garbage objects a second per element on the ring.
  const scratch = useMemo(() => ({ scale: new THREE.Vector3() }), [])

  useEffect(() => {
    lastPhaseIndex.current = -1
  }, [onPhase])

  useFrame((_, delta) => {
    elapsed.current += delta
    const { phase, local, index } = phaseAt(elapsed.current)

    if (index !== lastPhaseIndex.current) {
      lastPhaseIndex.current = index
      onPhase?.(describe(phase))
    }

    // --- packet ------------------------------------------------------------
    const slot = packetSlot(phase, local)
    const angle = slotAngle(slot)
    if (packet.current) {
      packet.current.position.set(Math.cos(angle) * RADIUS, 0, Math.sin(angle) * RADIUS)

      // A held packet pulses; a moving one is steady. Motion and pulsing at
      // the same time reads as noise.
      const held = phase.type === 'hold'
      const pulse = held ? 1 + Math.sin(elapsed.current * 5.5) * 0.16 : 1
      packet.current.scale.setScalar(pulse * (phase.type === 'reset' ? 1 - local : 1))

      const target = held ? colors.hold : phase.type === 'release' ? colors.pass : colors.packet
      packet.current.traverse((child) => {
        const mesh = child as THREE.Mesh
        if (!mesh.isMesh) return
        const material = mesh.material as THREE.MeshBasicMaterial
        material.color.lerp(target, Math.min(1, delta * 6))
      })
    }

    // The trail is a short arc of ring that follows the packet, so the path
    // already travelled is visibly lit and the direction of flow is never
    // ambiguous.
    if (trail.current) {
      trail.current.rotation.z = -angle
      const material = trail.current.material as THREE.MeshBasicMaterial
      material.opacity = phase.type === 'travel' || phase.type === 'release' ? 0.75 : 0.28
    }

    // --- agents ------------------------------------------------------------
    const activeStage = phase.type === 'dwell' ? phase.stage : -1
    STAGES.forEach((_stage, i) => {
      const node = agents.current[i]
      if (!node) return
      const isActive = i === activeStage
      const targetScale = isActive ? 1.32 : 1
      node.scale.lerp(scratch.scale.setScalar(targetScale), Math.min(1, delta * 5))
      node.traverse((child) => {
        const mesh = child as THREE.Mesh
        if (!mesh.isMesh) return
        const material = mesh.material as THREE.MeshBasicMaterial
        material.color.lerp(isActive ? colors.active : colors.idle, Math.min(1, delta * 4))
      })
    })

    // --- gate --------------------------------------------------------------
    if (gate.current) {
      gate.current.rotation.y += delta * 0.4
    }
    if (gateBarrier.current) {
      const material = gateBarrier.current.material as THREE.MeshBasicMaterial
      const held = phase.type === 'hold'
      const passing = phase.type === 'release'

      material.color.lerp(
        held ? colors.hold : passing ? colors.pass : colors.gateIdle,
        Math.min(1, delta * 5),
      )
      // Closed and opaque while it holds; opening as it releases; a thin
      // standing membrane the rest of the time.
      const targetOpacity = held ? 0.34 + Math.sin(elapsed.current * 4) * 0.1 : passing ? 0.34 * (1 - local) : 0.12
      material.opacity += (targetOpacity - material.opacity) * Math.min(1, delta * 6)
    }
  })

  return (
    // Tilted so the ring reads as an orbital plane in perspective rather than
    // a flat circle pasted on the screen.
    <group ref={group} rotation={[-0.46, 0, 0]}>
      {/* The path itself */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[RADIUS, 0.007, 6, 220]} />
        <meshBasicMaterial color={palette.agentIdle} transparent opacity={0.32} depthWrite={false} />
      </mesh>

      {/* Lit trailing arc, rotated to follow the packet */}
      <mesh ref={trail} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[RADIUS, 0.016, 6, 48, Math.PI / 3]} />
        <meshBasicMaterial
          color={palette.coreLit}
          transparent
          opacity={0.4}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Agent nodes */}
      {STAGES.map((stage, i) => {
        const angle = slotAngle(SLOT_OF_STAGE[i])
        return (
          <group
            key={stage.key}
            ref={(node) => {
              agents.current[i] = node
            }}
            position={[Math.cos(angle) * RADIUS, 0, Math.sin(angle) * RADIUS]}
          >
            <mesh>
              <icosahedronGeometry args={[0.15, 1]} />
              <meshBasicMaterial color={palette.agentIdle} toneMapped={false} />
            </mesh>
            {/* Its own small atmosphere, so bloom has something to catch when
                the node heats up. Kept tight: at 2.6× the active node bloomed
                into a flat disc the size of a word in the headline. */}
            <mesh scale={1.9}>
              <sphereGeometry args={[0.15, 16, 16]} />
              <meshBasicMaterial
                color={palette.agentIdle}
                transparent
                opacity={0.13}
                side={THREE.BackSide}
                depthWrite={false}
                blending={THREE.AdditiveBlending}
              />
            </mesh>
          </group>
        )
      })}

      {/* The gate. Two counter-set rings and a membrane across the path. */}
      <group
        position={[
          Math.cos(slotAngle(GATE_SLOT)) * RADIUS,
          0,
          Math.sin(slotAngle(GATE_SLOT)) * RADIUS,
        ]}
        rotation={[0, -slotAngle(GATE_SLOT), 0]}
      >
        <group ref={gate}>
          <mesh>
            <torusGeometry args={[0.42, 0.014, 8, 64]} />
            <meshBasicMaterial color={palette.gateIdle} toneMapped={false} />
          </mesh>
          <mesh rotation={[0, Math.PI / 2, 0]} scale={0.78}>
            <torusGeometry args={[0.42, 0.01, 8, 64]} />
            <meshBasicMaterial
              color={palette.gateIdle}
              transparent
              opacity={0.5}
              toneMapped={false}
            />
          </mesh>
        </group>

        {/* The membrane the packet cannot cross unaided */}
        <mesh ref={gateBarrier}>
          <circleGeometry args={[0.41, 48]} />
          <meshBasicMaterial
            color={palette.gateIdle}
            transparent
            opacity={0.12}
            side={THREE.DoubleSide}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      </group>

      {/* The work packet */}
      <group ref={packet}>
        <mesh>
          <sphereGeometry args={[0.1, 20, 20]} />
          <meshBasicMaterial color={palette.packet} toneMapped={false} />
        </mesh>
        <mesh scale={3.4}>
          <sphereGeometry args={[0.1, 20, 20]} />
          <meshBasicMaterial
            color={palette.packet}
            transparent
            opacity={0.2}
            side={THREE.BackSide}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      </group>
    </group>
  )
}
