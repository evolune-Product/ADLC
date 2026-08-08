"""
OpenID Connect single sign-on, per organisation.

WHY OIDC AND NOT SAML
Enterprise buyers ask for "SSO" and mean either. SAML needs a library that
links against libxmlsec1 — a native build dependency on a platform whose pitch
includes running air-gapped from a compose file. OIDC reaches Okta, Entra ID,
Google Workspace, Auth0, Keycloak and PingFederate over plain HTTPS with
nothing but the JWT library already in this project. SAML-only IdPs remain a
genuine gap and are named as one on the public security page.

THE FLOW
Authorization Code with PKCE. Confidential client (we hold a secret), so PKCE
is belt-and-braces rather than strictly required — but an interception attack
on the redirect is the one failure mode that turns SSO into a liability, and
S256 costs nothing.

WHERE THE STATE LIVES
Nowhere. `state` is a short-lived JWT signed with the platform's own secret,
carrying the connection id, the nonce and the PKCE verifier. That means no
Redis round-trip, no cleanup job, no session table — and, more usefully, a
callback that arrives on a different worker than the one that started the flow
still validates. It expires in ten minutes.

WHAT IS CHECKED ON THE WAY BACK
The ID token's signature against the IdP's published JWKS, its issuer, its
audience, its expiry, and the nonce we generated. Skipping signature
verification is defensible when the token comes straight from the token
endpoint over TLS with client authentication — it is also the kind of shortcut
that ages badly, so it is not taken here.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from urllib.parse import urlencode

import httpx
from jose import jwt
from jose.exceptions import JWTError

from app.config import settings

log = logging.getLogger(__name__)

DISCOVERY_TIMEOUT_S = 8.0
TOKEN_TIMEOUT_S = 10.0
STATE_TTL_S = 600
SCOPES = "openid email profile"

# Discovery documents and JWKS are stable for hours; refetching them on every
# sign-in would put the IdP in the critical path of a request twice over.
_CACHE_TTL_S = 3600
_discovery_cache: dict[str, tuple[float, dict]] = {}
_jwks_cache: dict[str, tuple[float, dict]] = {}


class SsoError(RuntimeError):
    """Anything that should send the user back to /login with an explanation
    rather than a stack trace."""


def redirect_uri() -> str:
    """
    The single registered callback, on the API rather than the SPA — the code
    exchange needs the client secret and must never happen in a browser.

    One URI for every organisation. The connection is identified by the signed
    state, not by the path, so onboarding a new tenant is a database row, not a
    new URI to register with their identity provider.
    """
    return f"{settings.api_base_url.rstrip('/')}/auth/sso/callback"


# ── discovery ───────────────────────────────────────────────────────────────

def discover(issuer: str) -> dict:
    """The IdP's `.well-known/openid-configuration`, cached."""
    issuer = issuer.rstrip("/")
    hit = _discovery_cache.get(issuer)
    if hit and (time.monotonic() - hit[0]) < _CACHE_TTL_S:
        return hit[1]

    url = f"{issuer}/.well-known/openid-configuration"
    try:
        with httpx.Client(timeout=DISCOVERY_TIMEOUT_S) as client:
            response = client.get(url)
            response.raise_for_status()
            doc = response.json()
    except Exception as exc:
        raise SsoError(f"Could not read the OIDC configuration at {url}") from exc

    for required in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        if required not in doc:
            raise SsoError(f"The OIDC configuration at {url} is missing {required}")

    _discovery_cache[issuer] = (time.monotonic(), doc)
    return doc


def _jwks(jwks_uri: str) -> dict:
    hit = _jwks_cache.get(jwks_uri)
    if hit and (time.monotonic() - hit[0]) < _CACHE_TTL_S:
        return hit[1]
    try:
        with httpx.Client(timeout=DISCOVERY_TIMEOUT_S) as client:
            response = client.get(jwks_uri)
            response.raise_for_status()
            keys = response.json()
    except Exception as exc:
        raise SsoError("Could not fetch the identity provider's signing keys") from exc
    _jwks_cache[jwks_uri] = (time.monotonic(), keys)
    return keys


def check_connection(issuer: str) -> dict:
    """Validate an issuer at configuration time, so an admin finds out the URL
    is wrong while they are on the settings page rather than when their team
    cannot sign in on Monday."""
    doc = discover(issuer)
    _jwks(doc["jwks_uri"])
    return {
        "issuer": doc.get("issuer", issuer),
        "authorization_endpoint": doc["authorization_endpoint"],
        "token_endpoint": doc["token_endpoint"],
        "supports_pkce": "S256" in (doc.get("code_challenge_methods_supported") or []),
    }


# ── the outbound half ───────────────────────────────────────────────────────

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def authorize_url(connection_id: str, issuer: str, client_id: str) -> str:
    doc = discover(issuer)

    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    nonce = secrets.token_urlsafe(24)

    state = jwt.encode(
        {
            "cid": str(connection_id),
            "nonce": nonce,
            "verifier": verifier,
            "exp": int(time.time()) + STATE_TTL_S,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri(),
        "scope": SCOPES,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{doc['authorization_endpoint']}?{urlencode(params)}"


def read_state(state: str) -> dict:
    try:
        return jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        # Covers both tampering and the ten-minute expiry — a user who left the
        # IdP page open over lunch gets the same "start again" as an attacker.
        raise SsoError("This sign-in link has expired. Please try again.") from exc


# ── the inbound half ────────────────────────────────────────────────────────

def exchange_code(*, issuer: str, client_id: str, client_secret: str,
                  code: str, verifier: str) -> dict:
    doc = discover(issuer)
    try:
        with httpx.Client(timeout=TOKEN_TIMEOUT_S) as client:
            response = client.post(
                doc["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri(),
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code_verifier": verifier,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        log.warning("SSO token exchange rejected by %s: %s", issuer, exc.response.text[:300])
        raise SsoError("The identity provider rejected the sign-in.") from exc
    except Exception as exc:
        raise SsoError("Could not reach the identity provider.") from exc


def verify_id_token(*, issuer: str, client_id: str, id_token: str, nonce: str) -> dict:
    doc = discover(issuer)
    keys = _jwks(doc["jwks_uri"])
    try:
        claims = jwt.decode(
            id_token,
            keys,
            algorithms=doc.get("id_token_signing_alg_values_supported") or ["RS256"],
            audience=client_id,
            issuer=doc.get("issuer", issuer),
            options={"verify_at_hash": False},  # no access token bound here
        )
    except JWTError as exc:
        raise SsoError("The identity provider's response could not be verified.") from exc

    # Replay protection. Without this check the nonce is decoration.
    if claims.get("nonce") != nonce:
        raise SsoError("The identity provider's response could not be verified.")

    return claims


def profile_from(claims: dict, *, issuer: str, access_token: str | None) -> tuple[str, str | None, str | None]:
    """
    (email, name, picture).

    Some IdPs — Entra ID in certain configurations most notably — omit `email`
    from the ID token entirely, so falling back to the userinfo endpoint is not
    an edge case, it is Tuesday.
    """
    email = claims.get("email") or claims.get("preferred_username")
    name = claims.get("name")
    picture = claims.get("picture")

    if not email and access_token:
        doc = discover(issuer)
        userinfo = doc.get("userinfo_endpoint")
        if userinfo:
            try:
                with httpx.Client(timeout=TOKEN_TIMEOUT_S) as client:
                    response = client.get(
                        userinfo, headers={"Authorization": f"Bearer {access_token}"}
                    )
                    response.raise_for_status()
                    info = response.json()
                email = info.get("email") or info.get("preferred_username")
                name = name or info.get("name")
                picture = picture or info.get("picture")
            except Exception:
                log.info("userinfo lookup failed for %s", issuer)

    if not email or "@" not in email:
        raise SsoError("The identity provider did not return an email address.")

    if claims.get("email_verified") is False:
        raise SsoError("That account's email address is not verified with your identity provider.")

    return email.lower(), name, picture


def domain_of(email: str) -> str:
    return email.rsplit("@", 1)[-1].strip().lower()
