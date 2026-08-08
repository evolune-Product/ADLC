/**
 * The run's timeline — the model both views share.
 *
 * Deliberately free of any three.js import. `hooks.ts` needs the phase
 * schedule to drive the compact mobile stage, and if that pulled in the
 * renderer the whole ~250 kB WebGL chunk would land in the main bundle for
 * every visitor, including the ones this file exists to spare.
 */

export type PipelinePhase = {
  label: string
  kind: 'running' | 'held' | 'passed' | 'idle'
  /** Feeds the gate's agitation and the lights' intensity. */
  activity: number
  /** Which named node this phase is at, if any. Lets a DOM legend track the
   *  scene on screens too narrow to label the nodes in place. */
  node?: NodeId
}

/** Environments the DevOps agent promotes through, in order. */
export const ENVIRONMENTS = [
  { name: 'dev', x: 5.0 },
  { name: 'qa', x: 7.6 },
  { name: 'prod', x: 10.4 },
]

/**
 * Nodes that get a DOM label. Positions are projected to screen space every
 * frame and handed to the overlay — labels are rendered as HTML, not as
 * textures in the scene, so they stay crisp at any DPI, use the real UI font
 * and real icons, and cost nothing to change.
 */
export type NodeId =
  | 'commit-0'
  | 'commit-1'
  | 'commit-2'
  | 'commit-3'
  | 'gate'
  | 'env-0'
  | 'env-1'
  | 'env-2'

export type NodeState = 'idle' | 'active' | 'held' | 'passed'

/** Called once per node per frame. Writes to the DOM directly — never state. */
export type ProjectFn = (id: NodeId, x: number, y: number, state: NodeState) => void

export type Phase =
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

/** The loop's length in seconds. */
export const TIMELINE_TOTAL = TIMELINE.reduce((sum, p) => sum + p.duration, 0)

/**
 * The run's state at a given moment, with no rendering attached.
 *
 * The WebGL scene and the compact mobile timeline are two views of this one
 * function, so a phone and a desktop describe the same run in the same words
 * even though only one of them is drawing it.
 */
export function phaseAtTime(elapsed: number): PipelinePhase {
  return describePhase(phaseAt(elapsed).phase)
}

export function phaseAt(elapsed: number) {
  let t = elapsed % TOTAL
  for (let i = 0; i < TIMELINE.length; i++) {
    const phase = TIMELINE[i]
    if (t < phase.duration) return { phase, local: t / phase.duration, index: i }
    t -= phase.duration
  }
  return { phase: TIMELINE[TIMELINE.length - 1], local: 1, index: TIMELINE.length - 1 }
}

export function describePhase(phase: Phase): PipelinePhase {
  switch (phase.type) {
    case 'branch':
      return { label: 'BRANCH · agent/adlc-482 cut from main', kind: 'running', activity: 0.5 }
    case 'commit':
      return {
        label: COMMIT_LABELS[phase.index],
        kind: 'running',
        activity: 1,
        node: `commit-${phase.index}` as NodeId,
      }
    case 'move':
      return {
        label: 'HANDOFF · artefacts passed on',
        kind: 'running',
        activity: 0.4,
        node: `commit-${phase.from}` as NodeId,
      }
    case 'toGate':
      return {
        label: 'PULL REQUEST · opened against main',
        kind: 'running',
        activity: 0.6,
        node: 'commit-3',
      }
    case 'hold':
      return { label: 'HELD · awaiting human approval', kind: 'held', activity: 0.1, node: 'gate' }
    case 'merge':
      return { label: 'APPROVED · merged to main', kind: 'passed', activity: 0.85, node: 'gate' }
    case 'promote':
      return {
        label: `DEPLOYING · ${ENVIRONMENTS[phase.env].name}`,
        kind: 'passed',
        activity: 0.6,
        node: `env-${phase.env}` as NodeId,
      }
    case 'done':
      return { label: 'SHIPPED · run complete', kind: 'passed', activity: 0.15, node: 'env-2' }
  }
}

export const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2)

/* ──────────────────────────────────────────────── layout (no three.js) */

/**
 * Sits low in the frame. The graph is the ground the headline stands on, not
 * something drawn across it — at trunk height 0 the line ran straight through
 * the word "approve".
 */
export const TRUNK_Y = -1.5
export const TRUNK_FROM = -16
export const TRUNK_TO = 16

export const BRANCH_AT = -6.5
export const MERGE_AT = 2.2

/** Where the four agent commits sit along the branch, as curve parameters. */
export const COMMIT_U = [0.17, 0.39, 0.61, 0.83]

/** The height every commit's DOM label is anchored at, so the four sit on one
 *  line instead of stepping down the arc. */
export const LABEL_RAIL_Y = TRUNK_Y + 1.24

/**
 * The bounding box the camera has to frame, so the rig can fit the graph to
 * any viewport aspect instead of relying on two hardcoded breakpoints. Padded
 * a little past the outermost node — a diagram touching the edge of its frame
 * reads as cropped — and taller above the trunk than below, because the label
 * rail and its chips live up there.
 */
const EXTENT = {
  minX: BRANCH_AT - 1.4,
  maxX: ENVIRONMENTS[2].x + 1.4,
  minY: TRUNK_Y - 0.8,
  maxY: LABEL_RAIL_Y + 0.3,
}

/**
 * The box the camera has to frame.
 *
 * A run is a long, flat thing — roughly 19 units wide and 3 tall. In a wide
 * desktop band that is the right shape; in a portrait phone frame, fitting its
 * width leaves the graph a sliver a few pixels tall. So on narrow screens the
 * whole graph is rotated to run top-to-bottom, and this reports the box
 * accordingly. `main` still flows in the reading direction either way.
 */
export function graphExtent(vertical: boolean) {
  if (!vertical) return EXTENT
  // A quarter turn about Z: x becomes y and y becomes −x.
  return {
    minX: -EXTENT.maxY,
    maxX: -EXTENT.minY,
    minY: EXTENT.minX,
    maxY: EXTENT.maxX,
  }
}
