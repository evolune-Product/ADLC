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

    fogDensity: 0.026,
    ambient: 0.6,
    bloomIntensity: 1.1,
  }
}
