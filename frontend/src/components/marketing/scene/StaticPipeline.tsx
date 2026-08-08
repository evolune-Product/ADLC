/**
 * Static counterpart to the WebGL scene, shown to reduced-motion visitors, on
 * machines without a WebGL context, and on hardware that would run the real
 * scene badly.
 *
 * A genuine alternative rendering, not a placeholder: the same trunk, the same
 * feature branch with a commit per agent, the same gate standing at the merge
 * point, the same three environments beyond it — and HEAD drawn where it
 * spends the longest, stopped at the gate.
 *
 * It carries its own labels. The animated scene names its nodes with projected
 * DOM chips, which only have positions to sit at while the render loop is
 * running; a visitor who never gets that loop must still be able to name every
 * stage.
 */

const W = 1180
const H = 400
const TRUNK_Y = 250

const BRANCH_AT = 150
const MERGE_AT = 620
const BRANCH_TOP = 118

const COMMITS = [
  { x: 268, label: 'Planner' },
  { x: 378, label: 'Coder' },
  { x: 466, label: 'QA' },
  { x: 552, label: 'Reviewer' },
]

const ENVIRONMENTS = [
  { x: 760, name: 'dev' },
  { x: 880, name: 'qa' },
  { x: 1000, name: 'prod' },
]

/** Out of the trunk, along the top, and back down into it. */
const BRANCH_PATH = `
  M ${BRANCH_AT} ${TRUNK_Y}
  C ${BRANCH_AT + 58} ${TRUNK_Y}, ${BRANCH_AT + 66} ${BRANCH_TOP}, ${BRANCH_AT + 124} ${BRANCH_TOP}
  L ${MERGE_AT - 124} ${BRANCH_TOP}
  C ${MERGE_AT - 66} ${BRANCH_TOP}, ${MERGE_AT - 58} ${TRUNK_Y}, ${MERGE_AT} ${TRUNK_Y}
`

const LABEL_STYLE = {
  fontFamily: 'var(--mk-mono)',
  fontSize: 11,
  letterSpacing: '0.13em',
  textTransform: 'uppercase' as const,
}

export function StaticPipeline() {
  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
      {/* Two soft washes standing in for the WebGL scene's lighting. Kept at a
          low alpha of the ember and pass hues rather than a flat tint, so the
          same values sit correctly on both the near-black and the cream
          ground. */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(52% 62% at 40% 55%, var(--mk-glow-ember-soft) 0%, transparent 72%), radial-gradient(30% 46% at 74% 58%, color-mix(in srgb, var(--mk-pass) 8%, transparent) 0%, transparent 74%)',
        }}
      />

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="absolute inset-0 h-full w-full"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* the ground */}
        <g stroke="var(--mk-hairline)" strokeWidth={1} opacity={0.45}>
          {Array.from({ length: 7 }, (_, i) => (
            <line key={i} x1={0} y1={318 + i * 12} x2={W} y2={318 + i * 12} />
          ))}
        </g>

        {/* main, before the merge */}
        <line
          x1={0}
          y1={TRUNK_Y}
          x2={MERGE_AT}
          y2={TRUNK_Y}
          stroke="var(--mk-ink-3)"
          strokeOpacity={0.6}
          strokeWidth={2}
        />
        {/* main, after the gate — dashed, because nothing has shipped yet */}
        <line
          x1={MERGE_AT}
          y1={TRUNK_Y}
          x2={W}
          y2={TRUNK_Y}
          stroke="var(--mk-ink-3)"
          strokeOpacity={0.3}
          strokeWidth={2}
          strokeDasharray="5 7"
        />
        <text x={16} y={TRUNK_Y - 14} fill="var(--mk-ink-3)" fillOpacity={0.75} style={LABEL_STYLE}>
          main
        </text>

        {/* the feature branch */}
        <path
          d={BRANCH_PATH}
          fill="none"
          stroke="var(--mk-ember)"
          strokeOpacity={0.85}
          strokeWidth={2}
        />

        {/* agent commits */}
        {COMMITS.map((commit) => (
          <g key={commit.label}>
            <circle cx={commit.x} cy={BRANCH_TOP} r={13} fill="var(--mk-amber)" opacity={0.14} />
            <circle cx={commit.x} cy={BRANCH_TOP} r={5} fill="var(--mk-amber)" />
            <line
              x1={commit.x}
              y1={BRANCH_TOP - 16}
              x2={commit.x}
              y2={BRANCH_TOP - 26}
              stroke="var(--mk-hairline-lit)"
              strokeWidth={1}
            />
            <text
              x={commit.x}
              y={BRANCH_TOP - 34}
              textAnchor="middle"
              fill="var(--mk-ink-3)"
              style={LABEL_STYLE}
            >
              {commit.label}
            </text>
          </g>
        ))}

        {/* the gate, holding, exactly where the branch would merge */}
        <g>
          <line
            x1={MERGE_AT}
            y1={TRUNK_Y - 44}
            x2={MERGE_AT}
            y2={TRUNK_Y + 44}
            stroke="var(--mk-hold)"
            strokeOpacity={0.45}
            strokeWidth={1.5}
          />
          <circle
            cx={MERGE_AT}
            cy={TRUNK_Y}
            r={27}
            fill="var(--mk-hold)"
            opacity={0.1}
            className="mk-animate-breathe"
            style={{ transformOrigin: `${MERGE_AT}px ${TRUNK_Y}px` }}
          />
          <circle
            cx={MERGE_AT}
            cy={TRUNK_Y}
            r={20}
            fill="none"
            stroke="var(--mk-hold)"
            strokeOpacity={0.85}
            strokeWidth={1.75}
          />
          {/* HEAD, stopped */}
          <circle cx={MERGE_AT} cy={TRUNK_Y} r={6} fill="var(--mk-hold)" />
          <text
            x={MERGE_AT}
            y={TRUNK_Y + 62}
            textAnchor="middle"
            fill="var(--mk-hold)"
            style={LABEL_STYLE}
          >
            Approval gate
          </text>
        </g>

        {/* dev → qa → prod, not yet reached */}
        {ENVIRONMENTS.map((env) => (
          <g key={env.name}>
            <circle
              cx={env.x}
              cy={TRUNK_Y}
              r={10}
              fill="none"
              stroke="var(--mk-ink-3)"
              strokeOpacity={0.5}
              strokeWidth={1.5}
            />
            <text
              x={env.x}
              y={TRUNK_Y + 30}
              textAnchor="middle"
              fill="var(--mk-ink-3)"
              fillOpacity={0.75}
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
