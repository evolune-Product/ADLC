import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useFrame, useThree } from '@react-three/fiber'
import { MEMBRANE_FRAG, MEMBRANE_VERT } from './shaders'
import type { ScenePalette } from './palette'
import {
  BRANCH_AT,
  COMMIT_U,
  ENVIRONMENTS,
  LABEL_RAIL_Y,
  MERGE_AT,
  TRUNK_FROM,
  TRUNK_TO,
  TRUNK_Y,
  describePhase,
  easeInOut,
  phaseAt,
} from './pipelineTimeline'
import type { NodeId, NodeState, PipelinePhase, ProjectFn } from './pipelineTimeline'

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

/* ────────────────────────────────────────────────────────────── component */

export function DeliveryLine({
  palette,
  onPhase,
  onProject,
  vertical = false,
}: {
  palette: ScenePalette
  /** Fires only when the phase changes, never per frame. */
  onPhase?: (phase: PipelinePhase) => void
  /** Fires per node per frame with screen-space coordinates. */
  onProject?: ProjectFn
  /** Run the line top-to-bottom instead of left-to-right. */
  vertical?: boolean
}) {
  const { camera, size } = useThree()
  const root = useRef<THREE.Group>(null)
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
    () => ({
      scale: new THREE.Vector3(),
      point: new THREE.Vector3(),
      /** Reused for every projection — `project()` mutates in place. */
      projected: new THREE.Vector3(),
    }),
    [],
  )

  /** World → screen pixels, for the DOM label overlay. */
  const project = useMemo(() => {
    return (id: NodeId, world: THREE.Vector3, state: NodeState) => {
      if (!onProject) return
      scratch.projected.copy(world)
      // The graph may be rotated as a whole, so a node's local position is not
      // its world position. Go through the group's matrix rather than
      // duplicating the rotation maths here.
      if (root.current) root.current.localToWorld(scratch.projected)
      scratch.projected.project(camera)
      onProject(
        id,
        (scratch.projected.x * 0.5 + 0.5) * size.width,
        (-scratch.projected.y * 0.5 + 0.5) * size.height,
        state,
      )
    }
  }, [onProject, camera, size.width, size.height, scratch])

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
      onPhase?.(describePhase(phase))
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
    const deployedTo = (i: number) =>
      !resetting &&
      ((phase.type === 'promote' && (phase.env > i || (phase.env === i && local > 0.75))) ||
        phase.type === 'done')

    envs.current.forEach((mesh, i) => {
      if (!mesh) return
      const deployed = deployedTo(i)
      const material = mesh.material as THREE.MeshBasicMaterial
      material.color.lerp(deployed ? colors.pass : colors.idle, damp)
      material.opacity += ((deployed ? 1 : 0.4) - material.opacity) * damp
      mesh.scale.lerp(scratch.scale.setScalar(deployed ? 1.15 : 1), damp)
    })

    /* ── DOM labels ────────────────────────────────────────────────────── */
    // Every node is named on screen. Anonymous dots are pretty; a diagram of a
    // pipeline whose stages you cannot name is not doing its job.
    if (onProject) {
      commitPoints.forEach((point, i) => {
        const lit = !resetting && i <= reached
        const working = phase.type === 'commit' && phase.index === i
        // Anchored at a common height rather than at the node itself: the
        // branch is an arc, so projecting each chip from its own commit
        // staggered the four of them down a slope. Aligned, they read as one
        // row of stages, which is what they are.
        scratch.point.set(point.x, LABEL_RAIL_Y, point.z)
        project(`commit-${i}` as NodeId, scratch.point, working ? 'active' : lit ? 'passed' : 'idle')
      })

      scratch.point.set(MERGE_AT, TRUNK_Y, 0)
      project('gate', scratch.point, holding ? 'held' : opening ? 'passed' : 'idle')

      ENVIRONMENTS.forEach((env, i) => {
        scratch.point.set(env.x, TRUNK_Y, 0)
        const arriving = phase.type === 'promote' && phase.env === i
        project(
          `env-${i}` as NodeId,
          scratch.point,
          arriving ? 'active' : deployedTo(i) ? 'passed' : 'idle',
        )
      })
    }
  })

  return (
    <group ref={root} rotation={[0, 0, vertical ? -Math.PI / 2 : 0]}>
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
            blending={palette.additive ? THREE.AdditiveBlending : THREE.NormalBlending}
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
        {/* HEAD's halo. On the dark theme it is added light; on the light one
            the same shell drawn normally at a lower opacity reads as the soft
            edge of a cast shadow, which is the daylight equivalent of a glow. */}
        <mesh scale={palette.additive ? 2.8 : 2.2}>
          <sphereGeometry args={[0.062, 20, 20]} />
          <meshBasicMaterial
            color={palette.packet}
            transparent
            opacity={palette.additive ? 0.22 : 0.13}
            side={THREE.BackSide}
            depthWrite={false}
            blending={palette.additive ? THREE.AdditiveBlending : THREE.NormalBlending}
          />
        </mesh>
      </group>
    </group>
  )
}
