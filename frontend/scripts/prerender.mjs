/**
 * Prerenders the public marketing routes to real static HTML.
 *
 *   npm run build && node scripts/prerender.mjs
 *
 * Playwright is not a dependency of the app; like scripts/og.mjs this is a
 * build-time chore that uses whatever Playwright is on the machine:
 *
 *   npx playwright install chromium              # once
 *   npm install playwright@1.62.1 --no-save      # once, in frontend/
 *
 * WHY THIS EXISTS
 * These pages are client-rendered. `Seo.tsx` sets the title, description,
 * canonical and JSON-LD *after* the bundle boots, which Google can wait for
 * but the AI crawlers largely cannot: GPTBot, ClaudeBot, PerplexityBot and
 * OAI-SearchBot fetch HTML and do not execute JavaScript. Before this script,
 * every public URL served the same index.html shell — /the-gate answered with
 * the landing page's title, no headings and no body copy — so six distinct
 * pages looked like one duplicate page to exactly the crawlers that decide
 * whether this product gets cited in an answer.
 *
 * The output is a per-route `dist/<route>/index.html`. nginx already resolves
 * those: its SPA fallback is `try_files $uri $uri/ /index.html`, and `$uri/`
 * matches the prerendered directory before the fallback is reached. Real
 * visitors still get the SPA — React mounts into #root and replaces the
 * snapshot on hydration.
 */

import { chromium } from 'playwright'
import { createServer } from 'node:http'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, join, extname } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const dist = resolve(here, '..', 'dist')

/** Throwaway origin the snapshot is taken against. Anything Vite writes into
 *  the DOM against this origin is rewritten back to relative before writing. */
const PORT = 4178

/** Every public, indexable route. Keep in sync with App.tsx, sitemap.xml and
 *  robots.txt — a route missing here silently falls back to the shell. */
const ROUTES = ['/', '/how-it-works', '/the-gate', '/platform', '/pricing', '/security']

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.woff2': 'font/woff2', '.xml': 'application/xml',
  '.txt': 'text/plain',
}

// A minimal static server over dist/, with the same SPA fallback nginx uses.
const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost')
  let filePath = join(dist, url.pathname)
  if (!existsSync(filePath) || !extname(filePath)) filePath = join(dist, 'index.html')
  try {
    const body = await readFile(filePath)
    res.writeHead(200, { 'Content-Type': MIME[extname(filePath)] ?? 'application/octet-stream' })
    res.end(body)
  } catch {
    res.writeHead(404).end('not found')
  }
})

await new Promise((ok) => server.listen(PORT, ok))
// Alpine (musl) cannot run Playwright's own glibc Chromium build, so the
// Docker build stage installs it from apk and points here. Empty locally,
// where Playwright's bundled browser is used.
const browser = await chromium.launch(
  process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {},
)
const page = await browser.newPage()

for (const route of ROUTES) {
  await page.goto(`http://localhost:${PORT}${route}`, { waitUntil: 'networkidle' })
  // The reveal animations gate content on IntersectionObserver, so scroll the
  // whole page once: a section that never entered the viewport is still in the
  // DOM, but this also settles lazy chunks and the scene's first paint.
  await page.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += window.innerHeight) {
      window.scrollTo(0, y)
      await new Promise((r) => setTimeout(r, 120))
    }
    window.scrollTo(0, 0)
  })
  await page.waitForTimeout(400)

  const raw = await page.evaluate(() => {
    // The theme is a per-visitor preference resolved by the inline boot script
    // in <head>. Baking this machine's resolved theme into the snapshot would
    // ship every crawler — and the first paint of every visitor — whichever
    // theme this build box happened to have.
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.classList.remove('dark')
    document.documentElement.style.removeProperty('color-scheme')
    return '<!doctype html>\n' + document.documentElement.outerHTML
  })

  // Vite injects a <link rel="modulepreload"> for the lazily-imported WebGL
  // chunk once it is requested, and it writes that href against the *current*
  // origin — which during prerendering is this throwaway server. Left alone,
  // every production page would ship a dead absolute link to localhost:4178.
  // Rewriting the origin away leaves the correct root-relative path.
  const html = raw.replaceAll(`http://localhost:${PORT}`, '')
  if (raw !== html) console.log(`  ↳ rewrote ${(raw.length - html.length) / `http://localhost:${PORT}`.length} absolute prerender-origin URL(s) to relative`)

  const outDir = route === '/' ? dist : join(dist, route)
  await mkdir(outDir, { recursive: true })
  await writeFile(join(outDir, 'index.html'), html)

  const title = await page.title()
  console.log(`prerendered ${route.padEnd(15)} → ${(route === '/' ? 'index.html' : route + '/index.html').padEnd(26)} "${title}"`)
}

await browser.close()
server.close()
