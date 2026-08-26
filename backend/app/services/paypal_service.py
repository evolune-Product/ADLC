"""
PayPal — the rail for a buyer with a PayPal business account and no corporate
card program, which is common outside the US/EU card networks and among
smaller agencies and startups who would otherwise need to get a card approved
just to pay a SaaS bill.

Subscriptions v1
----------------
Like Razorpay, this is the recurring-billing API rather than a one-off order.
A `plan_id` must exist in the PayPal dashboard (or be created once via their
API) per tier before checkout works — same precondition as Stripe's price ids
and Razorpay's plan ids.

Creating a subscription returns a `links` array with an `approve` entry — the
hosted PayPal approval page. Same "redirect out, come back on success" shape
as Stripe Checkout and Razorpay's `short_url`, so the frontend needs no PayPal
JS SDK either.

Sandbox by default
-------------------
`settings.paypal_mode` defaults to `"sandbox"`. A deployment has to
deliberately set it to `"live"` before a real charge can happen — a
misconfigured `.env` should fail toward "nothing gets charged", not the
reverse.

Webhook verification is a real API call, not local HMAC
----------------------------------------------------------
Stripe and Razorpay sign webhooks with an HMAC the recipient can check purely
locally. PayPal does not — it verifies by having the recipient call PayPal's
own `/v1/notifications/verify-webhook-signature` endpoint with the delivery
headers and the raw event body, and PayPal answers whether the signature was
valid. There is no local shortcut; skipping this call and trusting the body
directly would mean any request shaped like a PayPal webhook is accepted as one.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.services.metering_service import PLANS

log = logging.getLogger(__name__)

REQUEST_TIMEOUT_S = 20.0

_BASE_URLS = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live": "https://api-m.paypal.com",
}


def is_configured() -> bool:
    return bool(settings.paypal_client_id and settings.paypal_client_secret)


def _base_url() -> str:
    return _BASE_URLS.get(settings.paypal_mode, _BASE_URLS["sandbox"])


def _access_token() -> str:
    """
    OAuth2 client-credentials grant. Fetched per call rather than cached —
    billing actions (starting a checkout, verifying an occasional webhook) are
    infrequent enough that the extra round trip is immaterial, and not caching
    a bearer token removes an entire class of "the cached token expired
    mid-request" bug for a code path that has to be trustworthy above all else.
    """
    with httpx.Client(timeout=REQUEST_TIMEOUT_S) as client:
        r = client.post(
            f"{_base_url()}/v1/oauth2/token",
            auth=(settings.paypal_client_id, settings.paypal_client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
        )
    if r.status_code >= 400:
        raise RuntimeError(f"PayPal OAuth failed ({r.status_code}): {r.text[:300]}")
    return r.json()["access_token"]


def plan_id_for(plan: str) -> str | None:
    return {
        "team": settings.paypal_plan_team,
        "growth": settings.paypal_plan_growth,
        "enterprise": settings.paypal_plan_enterprise,
    }.get(plan)


def _reverse_plan_lookup(plan_id: str) -> str | None:
    """The webhook payload carries PayPal's plan id, not our plan name —
    unlike Stripe's metadata or Razorpay's notes, a PayPal subscription has no
    generic key-value bag to stash our own plan name in. `custom_id` holds
    exactly one string and it is already spent on `owner_key`, so the plan
    name has to be recovered by reversing the id we minted it from."""
    for plan, pid in (("team", settings.paypal_plan_team),
                      ("growth", settings.paypal_plan_growth),
                      ("enterprise", settings.paypal_plan_enterprise)):
        if pid and pid == plan_id:
            return plan
    return None


def create_subscription(*, plan: str, owner_key: str, email: str | None) -> dict:
    """Returns {url, subscription_id, simulated}."""
    if plan not in PLANS or plan == "free":
        raise ValueError(f"Cannot start a PayPal subscription for plan '{plan}'")

    if not is_configured():
        log.info("[paypal not configured] simulated subscription: plan=%s owner=%s", plan, owner_key)
        return {
            "url": f"{settings.frontend_url}/billing?simulated=1&plan={plan}&gateway=paypal",
            "subscription_id": f"sim_pp_{plan}_{owner_key}",
            "simulated": True,
        }

    plan_id = plan_id_for(plan)
    if not plan_id:
        raise ValueError(f"No PayPal plan id configured for plan '{plan}'")

    token = _access_token()
    body: dict = {
        "plan_id": plan_id,
        # `custom_id` is the one field PayPal echoes back on every webhook
        # event for this subscription — the same job Stripe's client_reference_id
        # and Razorpay's notes.owner_key do.
        "custom_id": owner_key,
        "application_context": {
            "brand_name": "ADLC",
            "user_action": "SUBSCRIBE_NOW",
            "return_url": f"{settings.frontend_url}/billing?upgraded={plan}&gateway=paypal",
            "cancel_url": f"{settings.frontend_url}/billing?canceled=1&gateway=paypal",
        },
    }
    if email:
        body["subscriber"] = {"email_address": email}

    with httpx.Client(timeout=REQUEST_TIMEOUT_S) as client:
        r = client.post(
            f"{_base_url()}/v1/billing/subscriptions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"PayPal subscription creation failed ({r.status_code}): {r.text[:300]}")

    data = r.json()
    approve = next((link["href"] for link in data.get("links", []) if link.get("rel") == "approve"), None)
    if not approve:
        raise RuntimeError("PayPal subscription created but returned no approval link")
    return {"url": approve, "subscription_id": data["id"], "simulated": False}


def cancel_subscription(subscription_id: str, *, reason: str = "Canceled by customer") -> dict:
    if not is_configured() or subscription_id.startswith("sim_"):
        return {"status": "canceled", "simulated": True}

    token = _access_token()
    with httpx.Client(timeout=REQUEST_TIMEOUT_S) as client:
        r = client.post(
            f"{_base_url()}/v1/billing/subscriptions/{subscription_id}/cancel",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"reason": reason},
        )
    # PayPal returns 204 with no body on a successful cancel.
    if r.status_code not in (200, 204):
        raise RuntimeError(f"PayPal cancellation failed ({r.status_code}): {r.text[:300]}")
    return {"status": "canceled", "simulated": False}


def verify_webhook(headers: dict, raw_body: bytes) -> dict:
    """
    Verify a webhook by asking PayPal, and return the parsed event body only
    if PayPal confirms it. Raises on any failure to verify — including PayPal
    itself being unreachable, because a webhook this code cannot prove is
    genuine must never be treated as genuine.

    `headers` should be the raw request headers (case-insensitive access);
    PayPal's signature covers a specific set of transmission headers plus the
    event body, not just the body the way Stripe and Razorpay sign.
    """
    import json

    if not settings.paypal_webhook_id:
        raise RuntimeError("PAYPAL_WEBHOOK_ID is not configured")

    # Checked before any network call: a request missing the signature headers
    # is not shaped like a genuine PayPal webhook at all, and there is no
    # reason to spend an OAuth round trip finding that out.
    verify_body = {
        "transmission_id": headers.get("paypal-transmission-id"),
        "transmission_time": headers.get("paypal-transmission-time"),
        "cert_url": headers.get("paypal-cert-url"),
        "auth_algo": headers.get("paypal-auth-algo"),
        "transmission_sig": headers.get("paypal-transmission-sig"),
        "webhook_id": settings.paypal_webhook_id,
        "webhook_event": json.loads(raw_body),
    }
    if not all([verify_body["transmission_id"], verify_body["transmission_sig"],
                verify_body["cert_url"]]):
        raise ValueError("Missing PayPal transmission headers — not a genuine PayPal webhook")

    token = _access_token()
    with httpx.Client(timeout=REQUEST_TIMEOUT_S) as client:
        r = client.post(
            f"{_base_url()}/v1/notifications/verify-webhook-signature",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=verify_body,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"PayPal webhook verification call failed ({r.status_code}): {r.text[:300]}")

    result = r.json()
    if result.get("verification_status") != "SUCCESS":
        raise ValueError(f"PayPal webhook signature not verified: {result.get('verification_status')}")

    return verify_body["webhook_event"]


# PayPal subscription statuses, mapped the same shape as Razorpay's.
_STATUS_MAP = {
    "APPROVAL_PENDING": "past_due", "APPROVED": "active", "ACTIVE": "active",
    "SUSPENDED": "past_due", "CANCELLED": "canceled", "EXPIRED": "canceled",
}


def parse_event(event: dict) -> dict | None:
    """
    Normalise BILLING.SUBSCRIPTION.* and PAYMENT.SALE.* events into the same
    shape `stripe_service.parse_event` / `razorpay_service.parse_event` return.
    """
    etype = event.get("event_type", "")
    resource = event.get("resource") or {}

    if etype.startswith("BILLING.SUBSCRIPTION."):
        plan_id = resource.get("plan_id")
        billing_info = resource.get("billing_info") or {}
        next_cycle = (billing_info.get("next_billing_time"))
        return {
            "owner_key": resource.get("custom_id"),
            "plan": _reverse_plan_lookup(plan_id) if plan_id else None,
            "status": _STATUS_MAP.get(resource.get("status"), resource.get("status")),
            "customer_id": (resource.get("subscriber") or {}).get("payer_id"),
            "subscription_id": resource.get("id"),
            "period_end": next_cycle,   # ISO 8601 string, not a unix timestamp — see the router
        }

    if etype == "PAYMENT.SALE.DENIED":
        return {
            "owner_key": None, "plan": None, "status": "past_due",
            "customer_id": None,
            "subscription_id": resource.get("billing_agreement_id"),
        }

    return None
