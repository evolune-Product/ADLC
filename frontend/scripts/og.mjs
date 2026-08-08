/**
 * Renders public/og.png — the social card every link to this site unfurls as.
 *
 *   node scripts/og.mjs
 *
 * Playwright is not a dependency of the app; this is a build-time chore run by
 * hand when the headline or the brand changes, so it uses whatever Playwright
 * is on the machine:
 *
 *   npx playwright install chromium   # once
 *   npx playwright@1.62 -- node scripts/og.mjs
 *
 * Why a screenshot rather than an SVG: the card has to be a raster. Facebook,
 * X, LinkedIn and Slack all decline SVG in og:image and show no image at all
 * instead, and hand-authoring a 1200×630 PNG is worse than rendering the same
 * markup the site is made of. scripts/og-card.html is that markup — edit it,
 * not the PNG.
 */

import { chromium } from 'playwright'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const source = resolve(here, 'og-card.html')
const out = resolve(here, '..', 'public', 'og.png')

const browser = await chromium.launch()
const page = await browser.newPage({
  // The size every scraper crops to. Rendered 1:1 rather than at 2x: these are
  // displayed at a few hundred pixels wide and the file has to stay small
  // enough that a preview does not time out.
  viewport: { width: 1200, height: 630 },
  deviceScaleFactor: 1,
})

await page.goto(`file://${source}`)
// The gradient-clipped headline needs a beat to settle before capture.
await page.waitForTimeout(400)
await page.screenshot({ path: out })
await browser.close()

console.log(`wrote ${out}`)
