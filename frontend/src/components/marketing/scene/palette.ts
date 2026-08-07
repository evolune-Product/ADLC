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
  '--mk-ember-deep': '#7a2d0f',
  '--mk-amber': '#f5a623',
  '--mk-ink': '#f5efe6',
  '--mk-ink-3': '#7d766f',
  '--mk-pass': '#4ade80',
  '--mk-hold': '#f2545b',
} as const

type Token = keyof typeof FALLBACK

export function scenePalette() {
  let read: (token: Token) => string = (token) => FALLBACK[token]

  if (typeof document !== 'undefined') {
    const computed = getComputedStyle(document.documentElement)
    read = (token) => computed.getPropertyValue(token).trim() || FALLBACK[token]
  }

  return {
    background: read('--mk-scene-bg'),
    /** Molten interior of the core — the deep end of the heat ramp. */
    coreDeep: read('--mk-ember-deep'),
    /** Crest and rim colour, and the light the core casts on its neighbours. */
    coreLit: read('--mk-ember'),
    coreShell: read('--mk-ember-lit'),
    coreHalo: read('--mk-ember'),

    /** Agent nodes idle in ink and heat up as the run reaches them. */
    agentIdle: read('--mk-ink-3'),
    agentActive: read('--mk-amber'),

    /** The work packet moving down the pipeline. */
    packet: read('--mk-ink'),

    /** Gate states. These two are the only semantic colours in the scene:
     *  holding at the gate, and cleared through it. */
    gateHold: read('--mk-hold'),
    gatePass: read('--mk-pass'),
    gateIdle: read('--mk-ember-lit'),

    /** Mostly ink-white with a heated minority — the coloured few are what
     *  give the field temperature without turning it into confetti. */
    starColors: [read('--mk-ink'), read('--mk-amber'), read('--mk-ember'), read('--mk-ink-3')],
    starOpacity: 0.85,

    fogDensity: 0.0125,
    ambient: 0.55,
    bloomIntensity: 1.15,
  }
}
