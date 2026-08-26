"""
Integrations router — model providers and plugins.

Two catalogues and the credentials that go with them:

    GET    /providers                          the model-provider catalogue
    GET    /providers/credentials              what this workspace has stored (masked)
    PUT    /providers/credentials/{provider}   add or replace a key
    DELETE /providers/credentials/{provider}   remove one
    POST   /providers/credentials/{provider}/test   prove it works, for real

    GET    /plugins                            the plugin catalogue
    POST   /plugins/{key}/connect              connect one, verifying as it saves
    POST   /plugins/connections/{id}/verify    re-check an existing connection

Secrets go in and never come out. Every response carries `masked_hint`
(`sk-ant-…9f2a`) so someone can confirm *which* key is installed; no endpoint
returns the key itself, in any form, to anyone, including the person who set it.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.connection import Connection
from app.models.integration import ModelCredential, mask
from app.models.user import User
from app.routers._helpers import OrgContext, get_optional_org, is_domain_admin
from app.routers.auth import get_current_user
from app.services import llm_providers, llm_service, plugin_verify, plugins
from app.services.encryption import decrypt_token, encrypt_token

router = APIRouter()


# ── Bodies ────────────────────────────────────────────────────────────────────

class CredentialBody(BaseModel):
    # Optional: a local Ollama or an unauthenticated internal gateway has no key.
    api_key: str | None = None
    base_url: str | None = None
    label: str | None = None
    default_model: str | None = None
    # {"gpt-5": {"input": 300, "output": 1500}} in cents per million tokens.
    price_overrides: dict = Field(default_factory=dict)


class ConnectBody(BaseModel):
    name: str | None = None
    token: str | None = None
    url: str | None = None
    user: str | None = None
    extra: str | None = None


def _require_billing_admin(org_ctx: Optional[OrgContext]) -> None:
    """
    A model-provider key is spending authority — whoever installs it can run
    up a vendor bill on the workspace's account. That is the billing domain,
    not the engineering one: a billing manager administers it without needing
    write access to a single agent, and an engineering lead who is not also
    a billing manager should not be able to install a key charged to finance.
    """
    if org_ctx and not is_domain_admin(org_ctx, "billing"):
        raise HTTPException(status_code=403,
                            detail="Only owners, admins and billing managers can manage model provider keys")


def _require_engineering_admin(org_ctx: Optional[OrgContext]) -> None:
    """A plugin token is access to a system the pipeline reads or writes —
    GitHub, Jira, Slack. That is the engineering domain: an engineering lead
    connects these without needing billing authority, and a billing manager
    should not be the one wiring up the org's GitHub token."""
    if org_ctx and not is_domain_admin(org_ctx, "engineering"):
        raise HTTPException(status_code=403,
                            detail="Only owners, admins and engineering leads can manage plugin connections")


def _scope(current_user: User, org_ctx: Optional[OrgContext]):
    if org_ctx:
        return ModelCredential.org_id == org_ctx.org_id
    return and_(ModelCredential.user_id == current_user.id, ModelCredential.org_id.is_(None))


# ═══ Model providers ══════════════════════════════════════════════════════════

@router.get("/providers")
def list_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    The catalogue, annotated with what this workspace has already connected.

    One call rather than two, because the settings page needs both to render a
    single row per provider and fetching them separately guarantees a flash of
    "not connected" on every load.
    """
    stored = {
        c.provider: c for c in db.query(ModelCredential).filter(_scope(current_user, org_ctx)).all()
    }
    groups = llm_providers.catalog()
    for group in groups:
        for provider in group["providers"]:
            cred = stored.get(provider["key"])
            provider["connected"] = cred is not None
            provider["credential"] = _cred_out(cred) if cred else None

    return {
        "groups": groups,
        "connected_count": len(stored),
        "total": len(llm_providers.PROVIDERS),
        # Stated plainly, because it is the product's position rather than a
        # limitation: we do not resell inference and never hold model spend.
        "byo_only": True,
    }


def _cred_out(c: ModelCredential) -> dict:
    return {
        "id": str(c.id),
        "provider": c.provider,
        "label": c.label,
        "masked_hint": c.masked_hint,
        "base_url": c.base_url,
        "default_model": c.default_model,
        "price_overrides": c.price_overrides or {},
        "is_active": c.is_active,
        "status": c.status,
        "status_detail": c.status_detail,
        "last_verified_at": c.last_verified_at.isoformat() if c.last_verified_at else None,
        "has_key": bool(c.api_key),
    }


@router.get("/providers/credentials")
def list_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    rows = db.query(ModelCredential).filter(_scope(current_user, org_ctx)).all()
    return {"credentials": [_cred_out(c) for c in rows]}


@router.put("/providers/credentials/{provider}")
def upsert_credential(
    provider: str,
    body: CredentialBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _require_billing_admin(org_ctx)

    spec = llm_providers.get(provider)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Unknown provider '{provider}'")

    row = (
        db.query(ModelCredential)
        .filter(_scope(current_user, org_ctx), ModelCredential.provider == provider)
        .first()
    )

    # Validation has to know whether a key is already stored, so the lookup
    # comes first. Demanding a key on every edit would mean re-pasting the
    # secret to change a default model — and since the UI cannot show the key
    # back, that means fetching it from the vendor's console again.
    if llm_providers.requires_key(provider) and not body.api_key and not (row and row.api_key):
        raise HTTPException(status_code=422, detail=f"{spec['label']} requires an API key")
    if llm_providers.requires_base_url(provider) and not body.base_url and not (row and row.base_url):
        raise HTTPException(
            status_code=422,
            detail=f"{spec['label']} requires a base URL — {spec.get('url_hint', '')}".strip(),
        )

    if not row:
        row = ModelCredential(
            user_id=current_user.id,
            org_id=org_ctx.org_id if org_ctx else None,
            provider=provider,
        )
        db.add(row)

    row.label = body.label or spec["label"]
    # Same rule as the key: an omitted endpoint keeps the stored one. Wiping it
    # would silently break Azure and every self-hosted provider, where the URL
    # is the only thing that says where to send the request.
    if body.base_url:
        row.base_url = body.base_url
    row.default_model = body.default_model or row.default_model
    row.price_overrides = body.price_overrides or row.price_overrides or {}

    # An omitted key on an update means "leave the stored one alone" — the UI
    # cannot show it back, so it cannot resend it, and treating a blank field as
    # a deletion would silently wipe a working key on an unrelated edit.
    if body.api_key:
        row.api_key = encrypt_token(body.api_key)
        row.masked_hint = mask(body.api_key)

    # Any change invalidates the previous verification.
    row.status = "unknown"
    row.status_detail = None
    row.last_verified_at = None

    db.commit()
    db.refresh(row)
    return _cred_out(row)


@router.delete("/providers/credentials/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    provider: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _require_billing_admin(org_ctx)
    row = (
        db.query(ModelCredential)
        .filter(_scope(current_user, org_ctx), ModelCredential.provider == provider)
        .first()
    )
    if row:
        db.delete(row)
        db.commit()


@router.post("/providers/credentials/{provider}/test")
def test_credential(
    provider: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Prove the key works by making the smallest real completion the provider allows.

    Not a ping to a /models list endpoint: several vendors will happily list
    models for a key that has no inference quota, no billing attached, or the
    wrong project scope, and the failure then surfaces mid-run instead. A
    two-token completion costs a fraction of a cent and answers the question
    that actually matters — can this workspace generate with this key.
    """
    _require_billing_admin(org_ctx)
    row = (
        db.query(ModelCredential)
        .filter(_scope(current_user, org_ctx), ModelCredential.provider == provider)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="No credential stored for that provider")

    spec = llm_providers.get(provider) or {}
    model = row.default_model or (spec.get("suggested_models") or [None])[0]
    if not model:
        raise HTTPException(
            status_code=422,
            detail="Set a default model on this credential before testing it",
        )

    key = None
    if row.api_key:
        try:
            key = decrypt_token(row.api_key)
        except Exception:
            row.status, row.status_detail = "error", "Stored key could not be decrypted — re-enter it"
            db.commit()
            return {**_cred_out(row), "ok": False}

    try:
        result = llm_service.complete(
            system="You are a connectivity check.",
            user="Reply with the single word: ok",
            model=model,
            max_tokens=16,
            force_tool=False,
            byo_provider=provider,
            byo_key=key,
            byo_base_url=row.base_url,
            timeout=30.0,
        )
        row.status = "ok"
        row.status_detail = (
            f"{result.model} responded — {result.input_tokens + result.output_tokens} tokens"
        )
    except Exception as e:
        row.status = "error"
        # The vendor's own message is far more useful than ours: it says
        # "insufficient_quota" or "model not found" or "invalid x-api-key".
        row.status_detail = str(e)[:400]

    row.last_verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return {**_cred_out(row), "ok": row.status == "ok"}


# ═══ Plugins ══════════════════════════════════════════════════════════════════

@router.get("/plugins")
def list_plugins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    The plugin catalogue, annotated with what this workspace has connected.

    `counts` is computed from the registry rather than written down, so the
    number on the marketing surface cannot drift from the number of plugins
    that actually exist.
    """
    scope = (
        Connection.org_id == org_ctx.org_id if org_ctx
        else and_(Connection.user_id == current_user.id, Connection.org_id.is_(None))
    )
    connections = db.query(Connection).filter(scope).all()
    by_type: dict[str, list] = {}
    for c in connections:
        by_type.setdefault(c.type, []).append({
            "id": str(c.id), "name": c.name, "status": c.status,
            "workspace_url": c.workspace_url,
            "metadata": c.metadata_ or {},
        })

    groups = plugins.catalog()
    for group in groups:
        for plugin in group["plugins"]:
            plugin["connections"] = by_type.get(plugin["key"], [])
            plugin["connected"] = bool(plugin["connections"])

    return {"groups": groups, "counts": plugins.counts(),
            "connected_count": len({c.type for c in connections})}


@router.post("/plugins/{key}/connect", status_code=status.HTTP_201_CREATED)
def connect_plugin(
    key: str,
    body: ConnectBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Connect a plugin, verifying the credential before it is saved as working.

    A connection is always created — a credential that failed verification is
    stored with `status="error"` and the vendor's reason attached, rather than
    thrown away. Someone who pasted a token with one missing scope should be
    able to fix the scope and re-verify, not retype the whole form.
    """
    _require_engineering_admin(org_ctx)

    spec = plugins.get(key)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Unknown plugin '{key}'")

    if plugins.requires_token(key) and not body.token:
        raise HTTPException(status_code=422,
                            detail=f"{spec.get('token_label', 'Token')} is required")
    if plugins.requires_url(key) and not body.url:
        raise HTTPException(status_code=422,
                            detail=f"{spec.get('url_label', 'URL')} is required")
    if plugins.requires_user(key) and not body.user:
        raise HTTPException(status_code=422,
                            detail=f"{spec.get('user_label', 'Username')} is required")

    result = plugin_verify.verify(key, token=body.token, url=body.url,
                                  user=body.user, extra=body.extra)

    metadata = {"depth": spec["depth"], "verified_detail": result.detail}
    if result.display_name:
        metadata["display_name"] = result.display_name
    if body.user:
        metadata["email"] = body.user
    if body.extra:
        metadata["extra"] = body.extra

    conn = Connection(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        name=body.name or spec["label"],
        type=key,
        status="connected" if result.ok else "error",
        # A webhook URL is as much a secret as a token — anyone holding it can
        # post into the channel — so it is encrypted the same way rather than
        # left in the plaintext workspace_url column.
        access_token=encrypt_token(body.token or body.url) if (body.token or spec["auth"] == plugins.AUTH_WEBHOOK) else None,
        workspace_url=body.url if spec["auth"] != plugins.AUTH_WEBHOOK else None,
        metadata_=metadata,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    return {
        "id": str(conn.id), "type": conn.type, "name": conn.name,
        "status": conn.status, "verified": result.ok, "detail": result.detail,
        "display_name": result.display_name,
    }


@router.post("/plugins/connections/{connection_id}/verify")
def reverify_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Re-run the check. Tokens expire and get revoked; a status from three
    months ago is not evidence the integration still works."""
    scope = (
        Connection.org_id == org_ctx.org_id if org_ctx
        else and_(Connection.user_id == current_user.id, Connection.org_id.is_(None))
    )
    conn = db.query(Connection).filter(Connection.id == connection_id, scope).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    spec = plugins.get(conn.type)
    if not spec:
        raise HTTPException(status_code=422,
                            detail=f"'{conn.type}' is not a catalogue plugin")

    secret = None
    if conn.access_token:
        try:
            secret = decrypt_token(conn.access_token)
        except Exception:
            conn.status = "error"
            db.commit()
            raise HTTPException(status_code=500, detail="Stored credential could not be decrypted")

    is_webhook = spec["auth"] == plugins.AUTH_WEBHOOK
    result = plugin_verify.verify(
        conn.type,
        token=None if is_webhook else secret,
        url=secret if is_webhook else conn.workspace_url,
        user=(conn.metadata_ or {}).get("email"),
        extra=(conn.metadata_ or {}).get("extra"),
    )

    conn.status = "connected" if result.ok else "error"
    meta = dict(conn.metadata_ or {})
    meta["verified_detail"] = result.detail
    if result.display_name:
        meta["display_name"] = result.display_name
    conn.metadata_ = meta
    db.commit()

    return {"id": str(conn.id), "status": conn.status,
            "verified": result.ok, "detail": result.detail}
