"""
Credential verification — one authenticated call per plugin, driven by the
recipe on its catalogue entry.

This is the difference between a catalogue and a list of logos. A stored token
that has never been exercised is a deploy that fails at 3am with an auth error;
a token checked at connect time fails in the UI, in front of the person who can
fix it, with the vendor's own message attached.

SSRF
----
Several plugins are self-hostable (GitLab, Gitea, Mattermost, SonarQube,
Grafana, YouTrack), so a workspace supplies the host and the server then makes a
request to it. That is a server-side request forgery primitive by construction,
and the mitigation cannot simply be "block private addresses" — pointing at an
internal GitLab is the entire purpose of the field.

The rule is therefore keyed off deployment mode, which is the only place the
distinction is real:

  * `cloud` — a tenant admin must not be able to make shared infrastructure
    fetch `169.254.169.254` and hand back the response. Private, loopback,
    link-local and reserved addresses are refused, checked on the *resolved*
    address rather than the hostname, reusing `reader_service._assert_public_url`
    so there is one implementation of that check in the codebase.
  * `self_hosted` — the perimeter is the customer's own, the internal host is
    the point, and the operator already has shell on the box. The guard is off.

Redirects are never followed. A verification call is a single request to an
endpoint we chose from the registry; a redirect is either a misconfiguration or
an attempt to walk the request somewhere else, and neither deserves a second hop.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import httpx

from app.config import settings
from app.services import plugins
from app.services.reader_service import _assert_public_url

log = logging.getLogger(__name__)

# Long enough for a slow self-hosted instance, short enough that a connect form
# does not appear to hang.
VERIFY_TIMEOUT_S = 12.0


@dataclass
class VerifyResult:
    ok: bool
    detail: str = ""
    display_name: str | None = None
    status_code: int | None = None

    def as_dict(self) -> dict:
        return {
            "ok": self.ok, "detail": self.detail,
            "display_name": self.display_name, "status_code": self.status_code,
        }


def _dig(data, path: str | None):
    """Pull a display name out of a response by dotted path, tolerantly.

    A vendor changing a field name should downgrade the result to 'connected,
    name unknown', never turn a working credential into a failure."""
    if not path or data is None:
        return None
    cur = data
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[0] if cur else None
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur if isinstance(cur, (str, int, float, bool)) else None


def _guard(url: str) -> None:
    if settings.deployment_mode == "self_hosted":
        return
    _assert_public_url(url)


def verify(plugin_key: str, *, token: str | None = None, url: str | None = None,
           user: str | None = None, extra: str | None = None) -> VerifyResult:
    """
    Check a credential against the vendor. Never raises — a verification
    failure is a status on a connection, not a 500 on the request that created it.
    """
    spec = plugins.get(plugin_key)
    if not spec:
        return VerifyResult(False, f"Unknown plugin '{plugin_key}'")

    recipe = spec.get("verify")
    if not recipe:
        return VerifyResult(True, "Stored. This plugin has no verification endpoint.")

    try:
        if recipe.get("kind") == "webhook_ping":
            return _ping_webhook(url, recipe.get("shape"))
        return _call(spec, recipe, token=token, url=url, user=user, extra=extra)
    except httpx.TimeoutException:
        return VerifyResult(False, f"{spec['label']} did not respond within {int(VERIFY_TIMEOUT_S)}s")
    except httpx.RequestError as e:
        return VerifyResult(False, f"Could not reach {spec['label']}: {type(e).__name__}")
    except ValueError as e:
        # What `_assert_public_url` raises. Say plainly why, because the user
        # very likely typed an internal hostname on a cloud deployment.
        return VerifyResult(False, str(e))
    except Exception:
        log.exception("Verification blew up for %s", plugin_key)
        return VerifyResult(False, "Verification failed unexpectedly")


def _call(spec: dict, recipe: dict, *, token, url, user, extra) -> VerifyResult:
    target = recipe["url"]

    if "{base}" in target:
        if not url:
            return VerifyResult(False, f"{spec.get('url_label', 'URL')} is required")
        target = target.replace("{base}", url.rstrip("/"))
    if "{token}" in target:
        if not token:
            return VerifyResult(False, "A token is required")
        target = target.replace("{token}", token)

    _guard(target)

    headers = {"Accept": "application/json"}
    headers.update(recipe.get("extra_headers") or {})
    params = {}
    auth = recipe.get("auth")

    if auth == "bearer":
        headers["Authorization"] = f"Bearer {token or ''}"
    elif auth == "token":
        headers["Authorization"] = f"{recipe.get('prefix', 'token ')}{token or ''}"
    elif auth == "header":
        headers[recipe.get("header", "Authorization")] = f"{recipe.get('prefix', '')}{token or ''}"
    elif auth == "query":
        params[recipe.get("query_param", "token")] = token or ""
    elif auth == "basic":
        # Several vendors want the credential in one half only: SonarQube sends
        # the token as the username with an empty password, Azure DevOps the
        # reverse. The recipe says which, and the default is user:token.
        u = recipe["basic_user"] if "basic_user" in recipe else (user or token or "")
        pw = recipe["basic_pass"] if "basic_pass" in recipe else (token or "")
        headers["Authorization"] = "Basic " + base64.b64encode(f"{u}:{pw}".encode()).decode()
    elif auth == "in_url":
        pass   # the secret is already inside the URL (Telegram)

    with httpx.Client(timeout=VERIFY_TIMEOUT_S, follow_redirects=False) as client:
        r = client.get(target, headers=headers, params=params or None)

    ok_codes = recipe.get("ok") or [200, 201, 204]
    if r.status_code in ok_codes:
        name = None
        try:
            name = _dig(r.json(), recipe.get("name_path"))
        except Exception:
            pass   # a 200 with an unparseable body is still a working credential
        return VerifyResult(True, "Connected", str(name) if name is not None else None, r.status_code)

    if r.status_code in (401, 403):
        return VerifyResult(False, f"{spec['label']} rejected the credential "
                                   f"({r.status_code}). Check the token and its scopes.",
                            status_code=r.status_code)
    if 300 <= r.status_code < 400:
        return VerifyResult(False, f"{spec['label']} redirected the check — verify the URL "
                                   f"is the API host, not a login page.", status_code=r.status_code)
    return VerifyResult(False, f"{spec['label']} returned {r.status_code}: {r.text[:180]}",
                        status_code=r.status_code)


# ── Webhook targets ───────────────────────────────────────────────────────────
#
# A webhook has no auth endpoint to query, so the only honest check is to post
# to it. Each chat vendor wants a different envelope for the same sentence.

_PING_TEXT = "ADLC connected. Approvals, run failures and deploys will arrive here."


def _ping_body(shape: str | None) -> dict:
    if shape == "discord":
        return {"content": _PING_TEXT}
    if shape == "teams":
        return {"type": "message", "text": _PING_TEXT}
    if shape == "gchat":
        return {"text": _PING_TEXT}
    return {"text": _PING_TEXT}          # Slack, Mattermost, generic


def _ping_webhook(url: str | None, shape: str | None) -> VerifyResult:
    if not url:
        return VerifyResult(False, "A webhook URL is required")
    _guard(url)

    with httpx.Client(timeout=VERIFY_TIMEOUT_S, follow_redirects=False) as client:
        r = client.post(url, json=_ping_body(shape))

    # Vendors disagree on success: Slack returns 200 "ok", Discord 204,
    # Teams 200 "1", Google Chat 200 with the created message.
    if r.status_code in (200, 201, 202, 204):
        return VerifyResult(True, "Connected — a test message was posted to the channel.",
                            status_code=r.status_code)
    if r.status_code == 404:
        return VerifyResult(False, "That webhook no longer exists — it was probably revoked.",
                            status_code=r.status_code)
    return VerifyResult(False, f"The webhook returned {r.status_code}: {r.text[:180]}",
                        status_code=r.status_code)
