/**
 * Static counterpart to the WebGL scene, shown to reduced-motion visitors, on
 * machines without a WebGL context, and on hardware that would run the real
 * scene badly.
 *
 * It is a genuine alternative rendering rather than a placeholder: the same six
 * slots, the same five agents in execution order, the same gate between the
 * Reviewer and DevOps — and the packet drawn where it spends the longest,
 * stopped at the gate. Someone who only ever sees this frame still learns what
 * the product does.
 */

const RX = 358
const RY = 132
const CX = 450
const CY = 300

/**
 * Slots are rotated half a step off the vertical. On the axis-aligned layout a
 * node lands at top-centre and another at bottom-centre — exactly where the
 * headline and the standfirst sit — and their labels printed straight through
 * the copy. Offsetting by 30° puts all six on the diagonals and the flanks,
 * clear of the text column at every viewport width.
 */
const slot = (i: number) => {
  const angle = -Math.PI / 2 + Math.PI / 6 + (i * Math.PI * 2) / 6
  return { x: CX + Math.cos(angle) * RX, y: CY + Math.sin(angle) * RY }
}

const AGENTS = [
  { name: 'Planner', slot: 0 },
  { name: 'Coder', slot: 1 },
  { name: 'QA', slot: 2 },
  { name: 'Reviewer', slot: 3 },
  { name: 'DevOps', slot: 5 },
]

const GATE = slot(4)

export function StaticPipeline() {
  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
      {/* Heat under the composition, so the area is never a flat black box
          even before anything else paints. */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(58% 46% at 50% 40%, rgba(232, 99, 42, 0.16) 0%, transparent 68%), radial-gradient(40% 38% at 66% 62%, rgba(245, 166, 35, 0.09) 0%, transparent 72%)',
        }}
      />

      <svg
        viewBox="0 0 900 600"
        className="absolute left-1/2 top-1/2 h-[min(112vh,820px)] w-[min(122vw,1180px)] -translate-x-1/2 -translate-y-1/2"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <radialGradient id="mk-core-glow">
            <stop offset="0%" stopColor="var(--mk-amber)" stopOpacity="0.9" />
            <stop offset="42%" stopColor="var(--mk-ember)" stopOpacity="0.32" />
            <stop offset="100%" stopColor="var(--mk-ember)" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* The path */}
        <ellipse
          cx={CX}
          cy={CY}
          rx={RX}
          ry={RY}
          fill="none"
          stroke="var(--mk-hairline-lit)"
          strokeWidth={1.25}
        />

        {/* The orchestrator */}
        <circle cx={CX} cy={CY} r={110} fill="url(#mk-core-glow)" />
        <circle
          cx={CX}
          cy={CY}
          r={30}
          fill="none"
          stroke="var(--mk-ember)"
          strokeOpacity={0.5}
          strokeWidth={1}
        />
        <circle cx={CX} cy={CY} r={10} fill="var(--mk-ember)" opacity={0.92} />

        {/* Agents in execution order */}
        {AGENTS.map((agent) => {
          const p = slot(agent.slot)
          return (
            <g key={agent.name}>
              <circle cx={p.x} cy={p.y} r={16} fill="var(--mk-ink-3)" opacity={0.14} />
              <circle cx={p.x} cy={p.y} r={5.5} fill="var(--mk-ink-3)" />
              <text
                x={p.x}
                y={p.y - 26}
                textAnchor="middle"
                fill="var(--mk-ink-3)"
                fillOpacity={0.72}
                style={{
                  fontFamily: 'var(--mk-mono)',
                  fontSize: 11,
                  letterSpacing: '0.14em',
                  textTransform: 'uppercase',
                }}
              >
                {agent.name}
              </text>
            </g>
          )
        })}

        {/* The gate, holding */}
        <g>
          <circle
            cx={GATE.x}
            cy={GATE.y}
            r={26}
            fill="var(--mk-hold)"
            opacity={0.1}
            className="mk-animate-breathe"
            style={{ transformOrigin: `${GATE.x}px ${GATE.y}px` }}
          />
          <circle
            cx={GATE.x}
            cy={GATE.y}
            r={18}
            fill="none"
            stroke="var(--mk-hold)"
            strokeOpacity={0.75}
            strokeWidth={1.5}
          />
          <line
            x1={GATE.x}
            y1={GATE.y - 18}
            x2={GATE.x}
            y2={GATE.y + 18}
            stroke="var(--mk-hold)"
            strokeOpacity={0.55}
            strokeWidth={1.25}
          />
          {/* The packet, stopped */}
          <circle cx={GATE.x} cy={GATE.y} r={6} fill="var(--mk-hold)" />
          <text
            x={GATE.x}
            y={GATE.y + 40}
            textAnchor="middle"
            fill="var(--mk-hold)"
            style={{
              fontFamily: 'var(--mk-mono)',
              fontSize: 11,
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
            }}
          >
            Approval gate
          </text>
        </g>
      </svg>
    </div>
  )
}
