import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { MEMBRANE_FRAG, MEMBRANE_VERT } from './shaders'
import type { ScenePalette } from './palette'

/**
 * The run, drawn the way engineers already draw it: a git graph.
 *
 * `main` runs left to right. A feature branch is cut from it, gathers four
 * commits as each agent finishes, and curves back down to rejoin the trunk.
 * At the exact point where it would merge stands the approval gate, and the
 * HEAD **stops there** — visibly, for the longest single beat in the loop —
 * until it is released. Only then does the merge land, and the change promotes
 * through dev, qa and prod, one environment at a time.
 *
 * This replaced an orbital diagram. The orbit was prettier and it was also
 * wrong: bodies circling a glowing centre read as a solar system whatever the
 * labels say, and it could not depict the two things that matter most here —
 * that work *merges* into a trunk, and that it is *promoted* afterwards.
 * Every element below corresponds to something in `run_tasks.py`.
 */

export type PipelinePhase = {
  label: string
  kind: 'running' | 'held' | 'passed' | 'idle'
  /** Feeds the gate's agitation and the lights' intensity. */
  activity: number
}

/* ─────────────────────────────────────────────────────────────── geometry */

/**
 * Sits low in the frame. The graph is the ground the headline stands on, not
 * something drawn across it — at trunk height 0 the line ran straight through
 * the word "approve".
 */
const TRUNK_Y = -1.5
const TRUNK_FROM = -16
const TRUNK_TO = 16

const BRANCH_AT = -6.5
const MERGE_AT = 2.2

/** Where the four agent commits sit along the branch, as curve parameters. */
const COMMIT_U = [0.17, 0.39, 0.61, 0.83]

/** Environments the DevOps agent promotes through, in order. */
const ENVIRONMENTS = [
  { name: 'dev', x: 5.0 },
  { name: 'qa', x: 7.6 },
  { name: 'prod', x: 10.4 },
]

/* ──────────────────────────────────────────────────────────────── timeline */

type Phase =
  | { type: 'branch'; duration: number }
  | { type: 'commit'; index: number; duration: number }
  | { type: 'move'; from: number; to: number; duration: number }
  | { type: 'toGate'; duration: number }
  | { type: 'hold'; duration: number }
  | { type: 'merge'; duration: number }
  | { type: 'promote'; env: number; duration: number }
  | { type: 'done'; duration: number }

const COMMIT_LABELS = [
  'PLANNER · file-level plan committed',
  'CODER · changes pushed to branch',
  'QA · tests run against the diff',
  'REVIEWER · diff scored, findings posted',
]

/**
 * One loop. Deliberately asymmetric: the hold at the gate is the longest beat
 * on the line, because in a real run it is by far the longest wait.
 */
const TIMELINE: Phase[] = [
  { type: 'branch', duration: 1.1 },
  { type: 'commit', index: 0, duration: 1.5 },
  { type: 'move', from: 0, to: 1, duration: 0.7 },
  { type: 'commit', index: 1, duration: 1.8 },
  { type: 'move', from: 1, to: 2, duration: 0.7 },
  { type: 'commit', index: 2, duration: 1.5 },
  { type: 'move', from: 2, to: 3, duration: 0.7 },
  { type: 'commit', index: 3, duration: 1.7 },
  { type: 'toGate', duration: 0.9 },
  { type: 'hold', duration: 3.2 },
  { type: 'merge', duration: 1.0 },
  { type: 'promote', env: 0, duration: 1.1 },
  { type: 'promote', env: 1, duration: 1.1 },
  { type: 'promote', env: 2, duration: 1.3 },
  { type: 'done', duration: 1.6 },
]

const TOTAL = TIMELINE.reduce((sum, p) => sum + p.duration, 0)

function phaseAt(elapsed: number) {
  let t = elapsed % TOTAL
  for (let i = 0; i < TIMELINE.length; i++) {
    const phase = TIMELINE[i]
    if (t < phase.duration) return { phase, local: t / phase.duration, index: i }
    t -= phase.duration
  }
  return { phase: TIMELINE[TIMELINE.length - 1], local: 1, index: TIMELINE.length - 1 }
}

function describe(phase: Phase): PipelinePhase {
  switch (phase.type) {
    case 'branch':
      return { label: 'BRANCH · agent/adlc-482 cut from main', kind: 'running', activity: 0.5 }
    case 'commit':
      return { label: COMMIT_LABELS[phase.index], kind: 'running', activity: 1 }
    case 'move':
      return { label: 'HANDOFF · artefacts passed on', kind: 'running', activity: 0.4 }
    case 'toGate':
      return { label: 'PULL REQUEST · opened against main', kind: 'running', activity: 0.6 }
    case 'hold':
      return { label: 'HELD · awaiting human approval', kind: 'held', activity: 0.1 }
    case 'merge':
      return { label: 'APPROVED · merged to main', kind: 'passed', activity: 0.85 }
    case 'promote':
      return {
        label: `DEPLOYING · ${ENVIRONMENTS[phase.env].name}`,
        kind: 'passed',
        activity: 0.6,
      }
    case 'done':
      return { label: 'SHIPPED · run complete', kind: 'passed', activity: 0.15 }
  }
}

const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2)

/* ────────────────────────────────────────────────────────────── component */

export function DeliveryLine({
  palette,
  onPhase,
}: {
  palette: ScenePalette
  /** Fires only when the phase changes, never per frame. */
  onPhase?: (phase: PipelinePhase) => void
}) {
  const head = useRef<THREE.Group>(null)
  const commits = useRef<Array<THREE.Mesh | null>>([])
  const envs = useRef<Array<THREE.Mesh | null>>([])
  const gateRing = useRef<THREE.Mesh>(null)
  const membrane = useRef<THREE.ShaderMaterial>(null)
  const shipped = useRef<THREE.Mesh>(null)
  const elapsed = useRef(0)
  const lastPhase = useRef(-1)

  /** The feature branch: out of the trunk, along, and back down into it. */
  const branch = useMemo(
    () =>
      new THREE.CatmullRomCurve3([
        new THREE.Vector3(BRANCH_AT, TRUNK_Y, 0),
        new THREE.Vector3(BRANCH_AT + 1.5, TRUNK_Y + 0.72, 0.25),
        new THREE.Vector3(BRANCH_AT + 3.4, TRUNK_Y + 1.0, 0.32),
        new THREE.Vector3(MERGE_AT - 3.1, TRUNK_Y + 1.02, 0.3),
        new THREE.Vector3(MERGE_AT - 1.3, TRUNK_Y + 0.7, 0.2),
        new THREE.Vector3(MERGE_AT, TRUNK_Y, 0),
      ]),
    [],
  )

  const commitPoints = useMemo(() => COMMIT_U.map((u) => branch.getPointAt(u)), [branch])

  const colors = useMemo(
    () => ({
      idle: new THREE.Color(palette.agentIdle),
      active: new THREE.Color(palette.agentActive),
      head: new THREE.Color(palette.packet),
      hold: new THREE.Color(palette.gateHold),
      pass: new THREE.Color(palette.gatePass),
      gateIdle: new THREE.Color(palette.gateIdle),
    }),
    [palette],
  )

  const scratch = useMemo(
    () => ({ scale: new THREE.Vector3(), point: new THREE.Vector3() }),
    [],
  )

  const membraneUniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uAmplitude: { value: 0.06 },
      uColor: { value: new THREE.Color(palette.gateIdle) },
      uOpacity: { value: 0.35 },
    }),
    [palette.gateIdle],
  )

  useEffect(() => {
    lastPhase.current = -1
  }, [onPhase])

  useFrame((_, delta) => {
    elapsed.current += delta
    const { phase, local, index } = phaseAt(elapsed.current)

    if (index !== lastPhase.current) {
      lastPhase.current = index
      onPhase?.(describe(phase))
    }

    const damp = Math.min(1, delta * 6)

    /* ── HEAD ──────────────────────────────────────────────────────────── */
    if (head.current) {
      let visible = true

      switch (phase.type) {
        case 'branch':
          scratch.point.copy(branch.getPointAt(COMMIT_U[0] * easeInOut(local)))
          break
        case 'commit':
          scratch.point.copy(commitPoints[phase.index])
          break
        case 'move': {
          const u = THREE.MathUtils.lerp(
            COMMIT_U[phase.from],
            COMMIT_U[phase.to],
            easeInOut(local),
          )
          scratch.point.copy(branch.getPointAt(u))
          break
        }
        case 'toGate':
          scratch.point.copy(
            branch.getPointAt(THREE.MathUtils.lerp(COMMIT_U[3], 1, easeInOut(local))),
          )
          break
        case 'hold':
        case 'merge':
          scratch.point.set(MERGE_AT, TRUNK_Y, 0)
          break
        case 'promote': {
          const from = phase.env === 0 ? MERGE_AT : ENVIRONMENTS[phase.env - 1].x
          scratch.point.set(
            THREE.MathUtils.lerp(from, ENVIRONMENTS[phase.env].x, easeInOut(local)),
            TRUNK_Y,
            0,
          )
          break
        }
        case 'done':
          scratch.point.set(ENVIRONMENTS[2].x, TRUNK_Y, 0)
          visible = local < 0.5
          break
      }

      head.current.position.copy(scratch.point)

      // Held work pulses in place; moving work is steady. Both at once reads
      // as noise rather than as two different states.
      const pulse = phase.type === 'hold' ? 1 + Math.sin(elapsed.current * 5.5) * 0.18 : 1
      head.current.scale.lerp(scratch.scale.setScalar(visible ? pulse : 0.001), damp)

      const target =
        phase.type === 'hold'
          ? colors.hold
          : phase.type === 'merge' || phase.type === 'promote' || phase.type === 'done'
            ? colors.pass
            : colors.head

      head.current.traverse((child) => {
        const mesh = child as THREE.Mesh
        if (!mesh.isMesh) return
        ;(mesh.material as THREE.MeshBasicMaterial).color.lerp(target, damp)
      })
    }

    /* ── commits: light as they are made, stay lit until the run resets ── */
    const reached = (() => {
      switch (phase.type) {
        case 'branch':
          return -1
        case 'commit':
          return phase.index
        case 'move':
          return phase.from
        default:
          return 3
      }
    })()
    const resetting = phase.type === 'done' && local > 0.55

    commits.current.forEach((mesh, i) => {
      if (!mesh) return
      const lit = !resetting && i <= reached
      const material = mesh.material as THREE.MeshBasicMaterial
      material.color.lerp(lit ? colors.active : colors.idle, damp)
      mesh.scale.lerp(scratch.scale.setScalar(lit ? 1.2 : 0.75), damp)
    })

    /* ── the gate ──────────────────────────────────────────────────────── */
    const holding = phase.type === 'hold'
    const opening = phase.type === 'merge'

    if (membrane.current) {
      const u = membrane.current.uniforms
      u.uTime.value += delta * (holding ? 2.4 : 0.7)
      u.uAmplitude.value = holding ? 0.13 : 0.05
      ;(u.uColor.value as THREE.Color).lerp(
        holding ? colors.hold : opening ? colors.pass : colors.gateIdle,
        damp,
      )
      // Closed while it holds, torn open as it releases, a thin film otherwise.
      const targetOpacity = holding ? 0.62 : opening ? 0.62 * (1 - local) : 0.2
      u.uOpacity.value += (targetOpacity - u.uOpacity.value) * damp
    }

    if (gateRing.current) {
      gateRing.current.rotation.x += delta * (holding ? 0.9 : 0.3)
      ;(gateRing.current.material as THREE.MeshBasicMaterial).color.lerp(
        holding ? colors.hold : opening ? colors.pass : colors.gateIdle,
        damp,
      )
    }

    /* ── shipped trunk: main lights up behind the change as it promotes ── */
    if (shipped.current) {
      let progress = 0
      if (phase.type === 'promote') {
        const from = phase.env === 0 ? MERGE_AT : ENVIRONMENTS[phase.env - 1].x
        progress =
          (THREE.MathUtils.lerp(from, ENVIRONMENTS[phase.env].x, easeInOut(local)) - MERGE_AT) /
          (TRUNK_TO - MERGE_AT)
      } else if (phase.type === 'done') {
        progress = ((ENVIRONMENTS[2].x - MERGE_AT) / (TRUNK_TO - MERGE_AT)) * (1 - local)
      }
      shipped.current.scale.x = Math.max(0.0001, progress)
    }

    /* ── environment markers ───────────────────────────────────────────── */
    envs.current.forEach((mesh, i) => {
      if (!mesh) return
      const deployed =
        !resetting &&
        ((phase.type === 'promote' && (phase.env > i || (phase.env === i && local > 0.75))) ||
          phase.type === 'done')
      const material = mesh.material as THREE.MeshBasicMaterial
      material.color.lerp(deployed ? colors.pass : colors.idle, damp)
      material.opacity += ((deployed ? 1 : 0.4) - material.opacity) * damp
      mesh.scale.lerp(scratch.scale.setScalar(deployed ? 1.15 : 1), damp)
    })
  })

  return (
    <group>
      {/* main — the trunk everything lands on */}
      <mesh position={[(TRUNK_FROM + TRUNK_TO) / 2, TRUNK_Y, 0]}>
        <boxGeometry args={[TRUNK_TO - TRUNK_FROM, 0.02, 0.02]} />
        <meshBasicMaterial color={palette.agentIdle} transparent opacity={0.75} />
      </mesh>

      {/* The lit stretch of main behind a change that has shipped. Anchored at
          the merge point so it grows rightward rather than from its centre. */}
      <group position={[MERGE_AT, TRUNK_Y, 0]}>
        <mesh ref={shipped} position={[(TRUNK_TO - MERGE_AT) / 2, 0, 0]}>
          <boxGeometry args={[TRUNK_TO - MERGE_AT, 0.03, 0.03]} />
          <meshBasicMaterial color={palette.gatePass} toneMapped={false} />
        </mesh>
      </group>

      {/* the feature branch */}
      <mesh>
        <tubeGeometry args={[branch, 120, 0.019, 8, false]} />
        <meshBasicMaterial color={palette.coreLit} transparent opacity={0.95} toneMapped={false} />
      </mesh>

      {/* commits */}
      {commitPoints.map((point, i) => (
        <mesh
          key={i}
          ref={(mesh) => {
            commits.current[i] = mesh
          }}
          position={point}
        >
          <octahedronGeometry args={[0.082, 0]} />
          <meshBasicMaterial color={palette.agentIdle} toneMapped={false} />
        </mesh>
      ))}

      {/* the approval gate, standing across main at the merge point */}
      <group position={[MERGE_AT, TRUNK_Y, 0]}>
        <mesh ref={gateRing} rotation={[0, 0, Math.PI / 2]}>
          <torusGeometry args={[0.36, 0.011, 8, 72]} />
          <meshBasicMaterial color={palette.gateIdle} toneMapped={false} />
        </mesh>

        {/* the film the merge cannot cross unaided */}
        <mesh rotation={[0, Math.PI / 2, 0]}>
          <planeGeometry args={[0.72, 0.72, 40, 40]} />
          <shaderMaterial
            ref={membrane}
            vertexShader={MEMBRANE_VERT}
            fragmentShader={MEMBRANE_FRAG}
            uniforms={membraneUniforms}
            transparent
            depthWrite={false}
            side={THREE.DoubleSide}
            blending={THREE.AdditiveBlending}
          />
        </mesh>

        {/* posts, so the gate reads as built rather than as a floating hoop */}
        {[-1, 1].map((side) => (
          <mesh key={side} position={[0, side * 0.5, 0]}>
            <boxGeometry args={[0.035, 0.22, 0.035]} />
            <meshBasicMaterial color={palette.gateIdle} transparent opacity={0.35} />
          </mesh>
        ))}
      </group>

      {/* dev → qa → prod */}
      {ENVIRONMENTS.map((env, i) => (
        <mesh
          key={env.name}
          ref={(mesh) => {
            envs.current[i] = mesh
          }}
          position={[env.x, TRUNK_Y, 0]}
          rotation={[0, 0, Math.PI / 2]}
        >
          <torusGeometry args={[0.22, 0.012, 8, 48]} />
          <meshBasicMaterial color={palette.agentIdle} transparent opacity={0.4} toneMapped={false} />
        </mesh>
      ))}

      {/* HEAD — the change itself */}
      <group ref={head}>
        <mesh>
          <sphereGeometry args={[0.062, 20, 20]} />
          <meshBasicMaterial color={palette.packet} toneMapped={false} />
        </mesh>
        <mesh scale={2.8}>
          <sphereGeometry args={[0.062, 20, 20]} />
          <meshBasicMaterial
            color={palette.packet}
            transparent
            opacity={0.22}
            side={THREE.BackSide}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      </group>
    </group>
  )
}
