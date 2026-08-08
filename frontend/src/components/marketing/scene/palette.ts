/**
 * three.js materials are unreachable from CSS, so the scene reads the resolved
 * marketing tokens off the document and rebuilds its palette from them. The
 * stylesheet stays the single source of truth for the product's colour.
 *
 * The literals below are the fallback for a non-DOM environment (SSR, tests).
 * They mirror `marketing.css`; if you change a colour, change it there — this
 * file only has to survive not being able to read it.
 */

export type ScenePalette = ReturnType<typeof scenePalette>

const FALLBACK = {
  '--mk-scene-bg': '#08070a',
  '--mk-ember': '#e8632a',
  '--mk-ember-lit': '#ff8f5c',
  '--mk-amber': '#f5a623',
  '--mk-ink': '#f5efe6',
  '--mk-ink-3': '#7d766f',
  '--mk-hairline-lit': '#342d3d',
  '--mk-pass': '#4ade80',
  '--mk-hold': '#f2545b',

  /* Numeric, and in the stylesheet for the same reason the colours are: the
     scene's exposure is part of the theme, not a constant. Bloom and additive
     blending only mean anything against a dark ground — see marketing.css. */
  '--mk-scene-fog': '0.026',
  '--mk-scene-ambient': '0.6',
  '--mk-scene-bloom': '1.1',
  '--mk-scene-vignette': '0.55',
  '--mk-scene-grid-opacity': '0.2',
  '--mk-scene-additive': '1',
} as const

type Token = keyof typeof FALLBACK

export function scenePalette() {
  let read: (token: Token) => string = (token) => FALLBACK[token]

  if (typeof document !== 'undefined') {
    const computed = getComputedStyle(document.documentElement)
    read = (token) => computed.getPropertyValue(token).trim() || FALLBACK[token]
  }

  const num = (token: Token) => {
    const parsed = Number.parseFloat(read(token))
    return Number.isFinite(parsed) ? parsed : Number.parseFloat(FALLBACK[token])
  }

  return {
    background: read('--mk-scene-bg'),

    /** The feature branch, and anything else carrying the brand's heat. */
    coreLit: read('--mk-ember'),

    /** The ruled ground the line runs on. */
    grid: read('--mk-hairline-lit'),

    /** Commits and environment markers: dark until the run reaches them. */
    agentIdle: read('--mk-ink-3'),
    agentActive: read('--mk-amber'),

    /** HEAD — the change moving down the line. */
    packet: read('--mk-ink'),

    /** Gate states. These two are the only semantic colours in the scene:
     *  holding at the gate, and cleared through it. */
    gateHold: read('--mk-hold'),
    gatePass: read('--mk-pass'),
    gateIdle: read('--mk-ember-lit'),

    fogDensity: num('--mk-scene-fog'),
    ambient: num('--mk-scene-ambient'),
    /** Zero means "do not mount the post chain at all", not "bloom softly". */
    bloomIntensity: num('--mk-scene-bloom'),
    vignetteDarkness: num('--mk-scene-vignette'),
    gridOpacity: num('--mk-scene-grid-opacity'),
    /**
     * Whether emissive elements — the HEAD halo, the gate membrane — should add
     * their light to what is behind them.
     *
     * On the dark ground that is what makes them glow. On the light one there
     * is nothing left to add to: additive blending against near-white clips to
     * white and the element simply disappears. Those meshes switch to normal
     * blending and carry their weight with opacity instead.
     */
    additive: num('--mk-scene-additive') > 0.5,
  }
}
