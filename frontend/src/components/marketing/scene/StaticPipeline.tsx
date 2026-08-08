/**
 * Static counterpart to the WebGL scene, shown to reduced-motion visitors, on
 * machines without a WebGL context, and on hardware that would run the real
 * scene badly.
 *
 * A genuine alternative rendering, not a placeholder: the same trunk, the same
 * feature branch with four agent commits, the same gate standing at the merge
 * point, the same three environments beyond it — and HEAD drawn where it
 * spends the longest, stopped at the gate. Someone who only ever sees this one
 * frame still learns what the product does.
 */

const W = 1000
const H = 460
const TRUNK_Y = 300

const BRANCH_AT = 120
const MERGE_AT = 560
const BRANCH_TOP = 150

const COMMITS = [
  { x: 218, label: 'Planner' },
  { x: 320, label: 'Coder' },
  { x: 400, label: 'QA' },
  { x: 482, label: 'Reviewer' },
]

const ENVIRONMENTS = [
  { x: 680, name: 'dev' },
  { x: 790, name: 'qa' },
  { x: 900, name: 'prod' },
]

/** Out of the trunk, along the top, and back down into it. */
const BRANCH_PATH = `
  M ${BRANCH_AT} ${TRUNK_Y}
  C ${BRANCH_AT + 54} ${TRUNK_Y}, ${BRANCH_AT + 62} ${BRANCH_TOP}, ${BRANCH_AT + 118} ${BRANCH_TOP}
  L ${MERGE_AT - 118} ${BRANCH_TOP}
  C ${MERGE_AT - 62} ${BRANCH_TOP}, ${MERGE_AT - 54} ${TRUNK_Y}, ${MERGE_AT} ${TRUNK_Y}
`

const LABEL_STYLE = {
  fontFamily: 'var(--mk-mono)',
  fontSize: 11,
  letterSpacing: '0.14em',
  textTransform: 'uppercase' as const,
}

export function StaticPipeline() {
  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
      {/* Heat under the composition, so the area is never a flat black box
          even before anything else paints. */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(56% 44% at 46% 62%, rgba(232, 99, 42, 0.14) 0%, transparent 70%), radial-gradient(34% 30% at 72% 66%, rgba(74, 222, 128, 0.06) 0%, transparent 72%)',
        }}
      />

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="absolute left-1/2 top-[58%] h-auto w-[min(150vw,1320px)] -translate-x-1/2 -translate-y-1/2"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* the ground */}
        <g stroke="var(--mk-hairline)" strokeWidth={1} opacity={0.5}>
          {Array.from({ length: 9 }, (_, i) => (
            <line key={i} x1={0} y1={370 + i * 11} x2={W} y2={370 + i * 11} />
          ))}
        </g>

        {/* main, before the merge */}
        <line
          x1={0}
          y1={TRUNK_Y}
          x2={MERGE_AT}
          y2={TRUNK_Y}
          stroke="var(--mk-ink-3)"
          strokeOpacity={0.55}
          strokeWidth={2}
        />
        {/* main, after the gate — dim, because nothing has shipped yet */}
        <line
          x1={MERGE_AT}
          y1={TRUNK_Y}
          x2={W}
          y2={TRUNK_Y}
          stroke="var(--mk-ink-3)"
          strokeOpacity={0.28}
          strokeWidth={2}
          strokeDasharray="5 7"
        />
        <text x={14} y={TRUNK_Y - 16} fill="var(--mk-ink-3)" fillOpacity={0.75} style={LABEL_STYLE}>
          main
        </text>

        {/* the feature branch */}
        <path
          d={BRANCH_PATH}
          fill="none"
          stroke="var(--mk-ember)"
          strokeOpacity={0.75}
          strokeWidth={2}
        />

        {/* Agent commits. Deliberately unlabelled: the branch arcs up through
            the middle of the viewport, which is where the headline lives, and
            four labels along it printed straight through the type. Which agent
            made which commit is carried by the status readout beside this
            diagram and by the "how a run works" section — the shape of the
            graph is what this frame is for. */}
        {COMMITS.map((commit) => (
          <g key={commit.label}>
            <circle cx={commit.x} cy={BRANCH_TOP} r={14} fill="var(--mk-amber)" opacity={0.13} />
            <circle cx={commit.x} cy={BRANCH_TOP} r={5} fill="var(--mk-amber)" />
          </g>
        ))}

        {/* the gate, holding, exactly where the branch would merge */}
        <g>
          <line
            x1={MERGE_AT}
            y1={TRUNK_Y - 52}
            x2={MERGE_AT}
            y2={TRUNK_Y + 52}
            stroke="var(--mk-hold)"
            strokeOpacity={0.5}
            strokeWidth={1.5}
          />
          <circle
            cx={MERGE_AT}
            cy={TRUNK_Y}
            r={30}
            fill="var(--mk-hold)"
            opacity={0.1}
            className="mk-animate-breathe"
            style={{ transformOrigin: `${MERGE_AT}px ${TRUNK_Y}px` }}
          />
          <circle
            cx={MERGE_AT}
            cy={TRUNK_Y}
            r={22}
            fill="none"
            stroke="var(--mk-hold)"
            strokeOpacity={0.8}
            strokeWidth={1.75}
          />
          {/* HEAD, stopped. Unlabelled for the same reason as the commits —
              the readout directly beneath this point already reads "HELD ·
              AWAITING HUMAN APPROVAL", so a second label would be the same
              sentence twice, printed over the call to action. */}
          <circle cx={MERGE_AT} cy={TRUNK_Y} r={6.5} fill="var(--mk-hold)" />
        </g>

        {/* dev → qa → prod, not yet reached */}
        {ENVIRONMENTS.map((env) => (
          <g key={env.name}>
            <circle
              cx={env.x}
              cy={TRUNK_Y}
              r={11}
              fill="none"
              stroke="var(--mk-ink-3)"
              strokeOpacity={0.45}
              strokeWidth={1.5}
            />
            <text
              x={env.x}
              y={TRUNK_Y + 34}
              textAnchor="middle"
              fill="var(--mk-ink-3)"
              fillOpacity={0.7}
              style={LABEL_STYLE}
            >
              {env.name}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}
