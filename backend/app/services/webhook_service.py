"""
Outbound webhooks with HMAC-SHA256 signatures.

Enterprise buyers will not adopt a control plane they cannot wire into their own
systems (ServiceNow change records, PagerDuty, internal audit lakes). Every
delivery is signed and logged, which doubles as compliance evidence for
"agent action X was reported to system Y at time T".

Signature scheme (Stripe/Svix-compatible shape):
    X-ADLC-Timestamp: <unix seconds>
    X-ADLC-Signature: sha256=<hex hmac of "{timestamp}.{body}" using the hook secret>
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid

import httpx
from sqlalchemy.orm import Session

from app.models.governance import Webhook, WebhookDelivery

log = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 10


def sign(secret: str, timestamp: int, body: str) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def verify(secret: str, timestamp: int, body: str, signature: str, tolerance: int = 300) -> bool:
    """Exposed so customers (and our tests) can validate the same way we sign."""
    if abs(time.time() - timestamp) > tolerance:
        return False
    return hmac.compare_digest(sign(secret, timestamp, body), signature)


def dispatch(db: Session, *, org_id: uuid.UUID | None, event: str, payload: dict) -> int:
    """Fire `event` to every active hook in the org subscribed to it."""
    if not org_id:
        return 0

    hooks = (
        db.query(Webhook)
        .filter(Webhook.org_id == org_id, Webhook.is_active.is_(True))
        .all()
    )
    sent = 0
    for hook in hooks:
        if hook.events and event not in hook.events:
            continue
        if _deliver(db, hook, event, payload):
            sent += 1
    return sent


def _deliver(db: Session, hook: Webhook, event: str, payload: dict) -> bool:
    envelope = {
        "id": str(uuid.uuid4()),
        "event": event,
        "created_at": int(time.time()),
        "data": payload,
    }
    body = json.dumps(envelope, default=str, separators=(",", ":"))
    ts = int(time.time())
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "agentic-sdlc-webhooks/1.0",
        "X-ADLC-Event": event,
        "X-ADLC-Timestamp": str(ts),
        "X-ADLC-Signature": sign(hook.secret, ts, body),
    }

    started = time.time()
    status, ok, error = None, False, None
    try:
        r = httpx.post(str(hook.url), content=body, headers=headers, timeout=10)
        status, ok = r.status_code, 200 <= r.status_code < 300
        if not ok:
            error = r.text[:500]
    except Exception as exc:
        error = str(exc)[:500]

    db.add(WebhookDelivery(
        webhook_id=hook.id, event=event, payload=envelope,
        status_code=status, ok=ok, error=error,
        duration_ms=int((time.time() - started) * 1000),
    ))

    # Auto-disable a persistently dead endpoint rather than retrying forever.
    hook.failure_count = 0 if ok else (hook.failure_count or 0) + 1
    if hook.failure_count >= MAX_CONSECUTIVE_FAILURES:
        hook.is_active = False
        log.warning("Disabled webhook %s after %s consecutive failures", hook.id, hook.failure_count)
    db.commit()
    return ok
