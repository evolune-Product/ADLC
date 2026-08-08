import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * Per-route document head.
 *
 * ADLC's public pages are client-rendered, so every crawler and every link
 * unfurler — Google, Slack, LinkedIn, and increasingly GPTBot and ClaudeBot —
 * sees whatever is in `index.html` unless something rewrites it. Before this,
 * that meant `/pricing` shared the home page's title and description, and the
 * 404 route advertised itself as indexable.
 *
 * Deliberately imperative rather than declarative. React 19 will hoist a
 * `<meta>` rendered anywhere in the tree into `<head>`, but it will not
 * reconcile it against the tag `index.html` already ships, so the page ends up
 * with two descriptions and the crawler picks one. Mutating the existing tag by
 * selector guarantees exactly one of each, and restoring on unmount keeps a
 * client-side navigation away from a page from leaving its metadata behind.
 *
 * The site-wide Organization and SoftwareApplication graph stays in
 * `index.html`, where it is visible without running JavaScript. Only page-level
 * schema (a pricing page's FAQ, say) is injected here.
 */

const SITE_URL = 'https://adlc.dev'

type SeoProps = {
  title: string
  description: string
  /** Path only, e.g. '/pricing'. Defaults to the current location. */
  path?: string
  /** Adds `noindex, nofollow` and suppresses the canonical link. */
  noIndex?: boolean
  /** Page-level JSON-LD. Removed again on unmount. */
  schema?: object
}

/** Sets an attribute on an existing head tag, returning what was there before
 *  so it can be put back. */
function setMeta(selector: string, attribute: string, value: string) {
  const el = document.head.querySelector(selector)
  if (!el) return null
  const previous = el.getAttribute(attribute)
  el.setAttribute(attribute, value)
  return () => {
    if (previous === null) el.removeAttribute(attribute)
    else el.setAttribute(attribute, previous)
  }
}

export function Seo({ title, description, path, noIndex = false, schema }: SeoProps) {
  const location = useLocation()
  const url = `${SITE_URL}${path ?? location.pathname}`

  useEffect(() => {
    const restore: Array<(() => void) | null> = []
    const previousTitle = document.title
    document.title = title

    restore.push(setMeta('meta[name="description"]', 'content', description))
    restore.push(setMeta('meta[property="og:title"]', 'content', title))
    restore.push(setMeta('meta[property="og:description"]', 'content', description))
    restore.push(setMeta('meta[property="og:url"]', 'content', url))
    restore.push(setMeta('meta[name="twitter:title"]', 'content', title))
    restore.push(setMeta('meta[name="twitter:description"]', 'content', description))

    const canonical = document.head.querySelector('link[rel="canonical"]')
    const previousCanonical = canonical?.getAttribute('href') ?? null
    if (canonical) {
      if (noIndex) canonical.remove()
      else canonical.setAttribute('href', url)
    }

    let robots: HTMLMetaElement | null = null
    if (noIndex) {
      robots = document.createElement('meta')
      robots.name = 'robots'
      robots.content = 'noindex, nofollow'
      document.head.appendChild(robots)
    }

    let ld: HTMLScriptElement | null = null
    if (schema) {
      ld = document.createElement('script')
      ld.type = 'application/ld+json'
      ld.dataset.seo = 'page'
      ld.textContent = JSON.stringify(schema)
      document.head.appendChild(ld)
    }

    return () => {
      document.title = previousTitle
      restore.forEach((undo) => undo?.())
      robots?.remove()
      ld?.remove()
      if (canonical && noIndex && previousCanonical !== null) {
        canonical.setAttribute('href', previousCanonical)
        document.head.appendChild(canonical)
      }
    }
    // `schema` is a literal at every call site, so it is stringified rather
    // than compared by identity — otherwise a fresh object each render would
    // rip the script tag out and reinsert it on every commit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title, description, url, noIndex, JSON.stringify(schema ?? null)])

  return null
}
