"""
Source reader — turns a URL into clean Markdown an agent can afford to read.

WHY THIS EXISTS
Tickets link out. A Jira description says "implement per the spec" and pastes a
Notion page, an RFC, a vendor API doc. Until now the Planner saw a bare URL
string and had to plan around it. Fetching the raw page instead is not an
option: a typical page ships ~800 kB of HTML to deliver ~8 kB of content, and
the platform pays for every byte of that in tokens.

So: fetch, extract the real article, convert to Markdown, and score how well
that read actually went.

PROVENANCE
This is a faithful port of AgentRead's read engine
(`agentread-main/src/lib/engine/read.ts`) — the same extraction pipeline
(Readability → Markdown), the same six ReadScore deductions with the same
weights, the same risk thresholds. That file is the source of truth for the
heuristic. If the scoring changes there, change it here, the same way
`TheGate` on the marketing site tracks `policy_service`.

WHAT IS DELIBERATELY DIFFERENT
AgentRead is a public tool where the user fetching a URL is the user who typed
it. This is an authenticated multi-tenant backend running inside a perimeter
that can reach Postgres, Redis and MinIO. Fetching an arbitrary user-supplied
URL from in here is a server-side request forgery hole unless it is guarded, so
`_assert_public_url` below rejects private, loopback, link-local and reserved
addresses — and re-checks on every redirect hop, because following redirects
blindly is exactly how that guard gets bypassed.

WHAT THE SCORE IS FOR
Not to audit anyone's website. It answers a governance question: *how good was
the context this agent planned from?* A plan built off a page that only
half-extracted is the kind of thing the person at the approval gate should be
able to see. Same shape as the reviewer score — advisory signal, attached to
the artifact, never an automatic failure.
"""
from __future__ import annotations

import ipaddress
import logging
import re
import socket
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse, urlunparse

import httpx

log = logging.getLogger(__name__)

# ── limits ──────────────────────────────────────────────────────────────────
FETCH_TIMEOUT_S = 15.0
LLMS_TXT_TIMEOUT_S = 4.0
MAX_REDIRECTS = 5
# A 5 MB page is already pathological; past this we are just burning memory on
# something we are about to throw away.
MAX_BYTES = 5 * 1024 * 1024
CACHE_TTL_S = 600
USER_AGENT = "Mozilla/5.0 (compatible; EvoluneOS-SourceReader/1.0; +https://evoluneos.com/bot)"

# ── scoring weights — keep in step with read.ts ─────────────────────────────
PENALTY_LOW_REDUCTION = 15
PENALTY_SCRIPT_HEAVY = 10
PENALTY_JS_ONLY_PRICE = 20
PENALTY_DISABLED_CTA = 15
PENALTY_LAZY_CONTENT = 8
PENALTY_NO_LLMS_TXT = 7
PENALTY_THIN_CONTENT = 25

RISK_LOW_AT = 75
RISK_MEDIUM_AT = 55


@dataclass
class ReadFlag:
    severity: str  # high | medium | low | ok
    text: str

    def as_dict(self) -> dict:
        return {"severity": self.severity, "text": self.text}


@dataclass
class ReadResult:
    url: str
    title: str
    markdown: str
    html_bytes: int
    markdown_bytes: int
    tokens_before: int
    tokens_after: int
    read_score: int
    hallucination_risk: str  # low | medium | high
    flags: list[ReadFlag] = field(default_factory=list)
    latency_ms: int = 0
    cached: bool = False

    @property
    def tokens_saved(self) -> int:
        return max(0, self.tokens_before - self.tokens_after)

    def as_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "html_bytes": self.html_bytes,
            "markdown_bytes": self.markdown_bytes,
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "tokens_saved": self.tokens_saved,
            "read_score": self.read_score,
            "hallucination_risk": self.hallucination_risk,
            "flags": [f.as_dict() for f in self.flags],
            "latency_ms": self.latency_ms,
            "cached": self.cached,
        }


class ReadError(RuntimeError):
    """The URL could not be read. Never fatal to a run — the agent proceeds
    without that source and the failure is recorded against the run."""


# ── URL safety ──────────────────────────────────────────────────────────────

_SCHEME_RE = re.compile(r"^([a-z][a-z0-9+.\-]*):", re.I)


def normalize_url(raw: str) -> str:
    url = (raw or "").strip()
    if not url:
        raise ReadError("Empty URL")

    # Only a *scheme-less* string gets https:// bolted on. Testing for "does not
    # start with http" instead turned `file:///etc/passwd` into
    # `https://file:///etc/passwd` — a host called "file" — which quietly
    # swallowed the scheme rather than rejecting it.
    scheme_match = _SCHEME_RE.match(url)
    if scheme_match:
        if scheme_match.group(1).lower() not in ("http", "https"):
            raise ReadError(f"Unsupported scheme: {scheme_match.group(1)}")
    else:
        url = f"https://{url}"

    parts = urlparse(url)
    if parts.scheme not in ("http", "https"):
        raise ReadError(f"Unsupported scheme: {parts.scheme}")
    if not parts.hostname:
        raise ReadError("URL has no host")
    return urlunparse(parts)


def _assert_public_url(url: str) -> None:
    """
    Refuse anything that resolves inside our own perimeter.

    The check is on the *resolved addresses*, not the hostname: a hostname that
    looks external can still have an A record pointing at 169.254.169.254 or
    10.0.0.5, which is the standard way this attack is written. Every address
    the name resolves to has to be public, because we do not control which one
    the socket will pick.
    """
    parts = urlparse(url)
    host = parts.hostname
    if not host:
        raise ReadError("URL has no host")

    try:
        infos = socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ReadError(f"Could not resolve {host}") from exc

    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        ):
            raise ReadError(f"Refusing to fetch a non-public address ({addr}) for {host}")


def _fetch(url: str) -> tuple[str, str]:
    """
    GET the page, following redirects **one hop at a time** so the SSRF guard
    runs against every destination rather than only the one the user typed.

    Returns (final_url, html).
    """
    current = url
    with httpx.Client(
        timeout=FETCH_TIMEOUT_S,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            _assert_public_url(current)
            response = client.get(current)

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise ReadError(f"Redirect from {current} with no Location header")
                current = str(response.url.join(location))
                continue

            if response.status_code >= 400:
                raise ReadError(f"Upstream responded {response.status_code}")

            content = response.content[:MAX_BYTES]
            encoding = response.encoding or "utf-8"
            return current, content.decode(encoding, errors="replace")

    raise ReadError(f"Too many redirects (> {MAX_REDIRECTS})")


def _llms_txt_exists(url: str) -> bool:
    """Does the site publish a sanctioned map for agents? Advisory only, and a
    failure here must never fail the read."""
    parts = urlparse(url)
    probe = urlunparse((parts.scheme, parts.netloc, "/llms.txt", "", "", ""))
    try:
        _assert_public_url(probe)
        with httpx.Client(timeout=LLMS_TXT_TIMEOUT_S, follow_redirects=True,
                          headers={"User-Agent": USER_AGENT}) as client:
            return client.head(probe).status_code < 400
    except Exception:
        return False


# ── extraction ──────────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """~4 chars per token — the heuristic both Anthropic's and OpenAI's docs
    quote. Exact enough for a saving we are reporting, not billing."""
    return max(1, round(len(text) / 4))


def _to_markdown(html: str) -> str:
    from markdownify import markdownify

    return markdownify(
        html,
        heading_style="ATX",
        bullets="-",
        # Nothing in these ever carries signal an agent can use, and they are
        # most of the byte count.
        strip=["script", "style", "noscript", "iframe", "nav", "footer"],
    ).strip()


def _extract(html: str, url: str) -> tuple[str, str]:
    """(title, content_html) via Readability, with a raw-text fallback."""
    from readability import Document

    doc = Document(html)
    try:
        title = (doc.short_title() or "").strip()
    except Exception:
        title = ""
    try:
        content_html = doc.summary(html_partial=True)
    except Exception:
        content_html = ""
    return title or url, content_html or html


# ── the read ────────────────────────────────────────────────────────────────

_cache: dict[str, tuple[float, ReadResult]] = {}


def read_url(raw_url: str, *, fresh: bool = False) -> ReadResult:
    """
    Fetch, extract, score. Raises `ReadError` — callers are expected to record
    the failure and carry on without the source.
    """
    url = normalize_url(raw_url)
    started = time.monotonic()

    if not fresh:
        hit = _cache.get(url)
        if hit and (time.monotonic() - hit[0]) < CACHE_TTL_S:
            cached = hit[1]
            return ReadResult(
                **{**cached.__dict__, "cached": True,
                   "latency_ms": int((time.monotonic() - started) * 1000)}
            )

    final_url, html = _fetch(url)
    html_bytes = len(html.encode("utf-8"))

    # Signals are read from the RAW html, before Readability strips the very
    # markup that betrays a client-side-only page.
    script_count = len(re.findall(r"<script[\s>]", html, re.I))
    has_price_markup = bool(re.search(r"price|buy now|add to cart", html, re.I))
    has_disabled_cta = bool(
        re.search(r"disabled[^>]*>[^<]*(buy|checkout|add to cart)", html, re.I)
    )
    has_lazy_content = bool(
        re.search(r"loading=[\"']lazy[\"']|data-lazy|IntersectionObserver", html, re.I)
    )

    title, content_html = _extract(html, final_url)
    markdown = _to_markdown(content_html)

    if len(markdown) < 40:
        # Readability found nothing usable — an SPA shell, a paywall, a bot
        # wall. Fall back to raw text so the agent gets *something*, and let
        # the thin-content penalty say so.
        text = re.sub(r"<[^>]+>", " ", html)
        markdown = re.sub(r"\s+", " ", text).strip()[:4000]

    # A price mentioned in the markup but absent from what we extracted is the
    # single strongest hallucination signal there is: the agent will read a
    # page about a product and find no price on it.
    js_only_price = has_price_markup and not re.search(r"\$\s?\d|₹\s?\d|price", markdown, re.I)

    # The extractor usually leaves the page's own <h1> in place, so prepending
    # the title unconditionally (as the TypeScript engine does, where
    # Readability strips it) prints the heading twice.
    first_line = markdown.lstrip().split("\n", 1)[0].lstrip("# ").strip()
    if first_line.casefold() != title.casefold():
        markdown = f"# {title}\n\n{markdown}"
    markdown_bytes = len(markdown.encode("utf-8"))

    llms_txt = _llms_txt_exists(final_url)

    score = 100
    flags: list[ReadFlag] = []

    reduction = 1 - (markdown_bytes / max(html_bytes, 1))
    if reduction < 0.5:
        score -= PENALTY_LOW_REDUCTION
        flags.append(ReadFlag("medium", "Low payload reduction — the page may already be light, or content was not fully extracted."))

    if script_count > 25:
        score -= PENALTY_SCRIPT_HEAVY
        flags.append(ReadFlag("medium", f"{script_count} <script> tags — heavy client-side rendering, so a non-JS read may be incomplete."))

    if js_only_price:
        score -= PENALTY_JS_ONLY_PRICE
        flags.append(ReadFlag("high", "Price or CTA keywords appear in the raw HTML but not in the extracted text — rendered client-side only."))

    if has_disabled_cta:
        score -= PENALTY_DISABLED_CTA
        flags.append(ReadFlag("high", "A buy/checkout control is disabled in the markup — it likely hydrates only after JavaScript runs."))

    if has_lazy_content:
        score -= PENALTY_LAZY_CONTENT
        flags.append(ReadFlag("low", "Lazy-loaded content detected — some sections may not be present in this read."))

    if llms_txt:
        flags.append(ReadFlag("ok", "/llms.txt found and reachable."))
    else:
        score -= PENALTY_NO_LLMS_TXT
        flags.append(ReadFlag("medium", "No /llms.txt — this site publishes no sanctioned map for agents."))

    if len(markdown) < 200:
        score -= PENALTY_THIN_CONTENT
        flags.append(ReadFlag("high", "Almost no text could be extracted — likely a bot wall, a paywall, or an empty SPA shell."))

    score = max(1, min(100, round(score)))
    risk = "low" if score >= RISK_LOW_AT else "medium" if score >= RISK_MEDIUM_AT else "high"

    if not flags:
        flags.append(ReadFlag("ok", "No risk signals — this page reads cleanly."))

    result = ReadResult(
        url=final_url,
        title=title,
        markdown=markdown,
        html_bytes=html_bytes,
        markdown_bytes=markdown_bytes,
        tokens_before=estimate_tokens(html),
        tokens_after=estimate_tokens(markdown),
        read_score=score,
        hallucination_risk=risk,
        flags=flags,
        latency_ms=int((time.monotonic() - started) * 1000),
        cached=False,
    )

    _cache[url] = (time.monotonic(), result)
    return result


# ── finding the URLs in the first place ─────────────────────────────────────

# Bare URLs and the target of a markdown link both, with trailing punctuation
# left behind — a sentence-ending period is not part of the address.
_URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]+", re.I)

# Reading these back would spend tokens on nothing an agent can use.
_SKIP_HOST_SUFFIXES = (
    "githubusercontent.com", "shields.io", "badge.fury.io",
)
_SKIP_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".zip", ".tar", ".gz", ".mp4", ".mp3", ".woff", ".woff2", ".css", ".js",
)


def extract_urls(text: str, *, limit: int = 5) -> list[str]:
    """
    Every distinct, readable URL in a block of text, in the order it appears.

    Capped, because a ticket that pastes forty links is not a reason to make
    forty network calls before planning starts.
    """
    seen: list[str] = []
    for match in _URL_RE.finditer(text or ""):
        url = match.group(0).rstrip(".,;:!?")
        lowered = url.lower()
        if any(lowered.endswith(ext) for ext in _SKIP_EXTENSIONS):
            continue
        host = (urlparse(lowered).hostname or "")
        if any(host.endswith(suffix) for suffix in _SKIP_HOST_SUFFIXES):
            continue
        if url not in seen:
            seen.append(url)
        if len(seen) >= limit:
            break
    return seen
