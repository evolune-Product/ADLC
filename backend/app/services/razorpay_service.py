"""
Razorpay — the India billing rail.

International cards run 3% + GST on Razorpay; UPI, netbanking and domestic
cards run 2% + GST; a bank transfer via Razorpay's export account runs 1% +
GST with no forex markup. For a company priced in rupees, that is not a
rounding difference — it is the difference between a payment method a customer
actually has and one that quietly adds 1-3 points of FX spread on every charge.
That is the entire reason this exists alongside Stripe rather than telling
every Indian customer to find a card that works internationally.

Subscriptions, not one-off orders
----------------------------------
Razorpay's Orders API is for a single payment; Subscriptions is for recurring
billing, which is what a monthly plan actually is. A subscription requires a
`plan_id` that already exists in the Razorpay dashboard (or created once via
their API) for each tier — the same precondition Stripe already has for price
ids, so nothing new is asked of whoever configures this deployment.

Creating a subscription returns a `short_url` — a hosted Razorpay checkout
page — which is why the frontend needs no Razorpay JS SDK at all: the same
"redirect to a URL, come back on success" flow Stripe Checkout already uses
works unchanged for Razorpay too.

No SDK dependency
-------------------
Razorpay's REST API is HTTP Basic auth with (key_id, key_secret) and plain
JSON, so this is `httpx` directly rather than adding `razorpay` as a
dependency — the same choice `jira_service.py` and `github_service.py` (for
its non-PyGithub calls) already made for APIs this simple.
"""
from __future__ import annotations

import hashlib
import hmac
import logging

import httpx

from app.config import settings
from app.services.metering_service import PLANS

log = logging.getLogger(__name__)

API_BASE = "https://api.razorpay.com/v1"
REQUEST_TIMEOUT_S = 20.0

# A subscription needs a bounded number of billing cycles up front; Razorpay
# has no "forever" option the way Stripe's open-ended subscriptions do. 100
# monthly cycles is ~8 years — long enough that renewal is a non-event, short
# enough that an abandoned account does not bill into the indefinite future.
DEFAULT_TOTAL_CYCLES = 100


def is_configured() -> bool:
    return bool(settings.razorpay_key_id and settings.razorpay_key_secret)


def _auth() -> tuple[str, str]:
    return (settings.razorpay_key_id, settings.razorpay_key_secret)


def plan_id_for(plan: str) -> str | None:
    return {
        "enterprise": settings.razorpay_plan_enterprise,
    }.get(plan)


def create_subscription(*, plan: str, owner_key: str, email: str | None,
                        seats: int = 1) -> dict:
    """
    Returns {url, subscription_id, simulated}. `owner_key` is "org:<id>" or
    "user:<id>" and comes back in the subscription's `notes` on every webhook,
    the same way Stripe's `metadata` carries it — so the webhook handler can
    find the right `Subscription` row without a separate lookup table.
    """
    if plan not in PLANS or plan == "free":
        raise ValueError(f"Cannot start a Razorpay subscription for plan '{plan}'")

    if not is_configured():
        log.info("[razorpay not configured] simulated subscription: plan=%s owner=%s", plan, owner_key)
        return {
            "url": f"{settings.frontend_url}/billing?simulated=1&plan={plan}&gateway=razorpay",
            "subscription_id": f"sim_rzp_{plan}_{owner_key}",
            "simulated": True,
        }

    plan_id = plan_id_for(plan)
    if not plan_id:
        raise ValueError(f"No Razorpay plan id configured for plan '{plan}'")

    body = {
        "plan_id": plan_id,
        "quantity": max(seats, 1),
        "total_count": DEFAULT_TOTAL_CYCLES,
        "customer_notify": 1,
        "notes": {"plan": plan, "owner_key": owner_key},
    }
    if email:
        # Razorpay does not take an email directly on subscription creation;
        # it prefills the hosted checkout page's own customer step instead.
        body["notes"]["email"] = email

    with httpx.Client(timeout=REQUEST_TIMEOUT_S, auth=_auth()) as client:
        r = client.post(f"{API_BASE}/subscriptions", json=body)
    if r.status_code >= 400:
        raise RuntimeError(f"Razorpay subscription creation failed ({r.status_code}): {r.text[:300]}")

    data = r.json()
    return {"url": data["short_url"], "subscription_id": data["id"], "simulated": False}


def cancel_subscription(subscription_id: str, *, at_cycle_end: bool = True) -> dict:
    """
    Razorpay has no self-serve customer portal the way Stripe does — this is
    the closest equivalent, and it is why the billing router's cancel endpoint
    exists as an explicit action rather than a redirect.
    """
    if not is_configured() or subscription_id.startswith("sim_"):
        return {"status": "canceled", "simulated": True}

    with httpx.Client(timeout=REQUEST_TIMEOUT_S, auth=_auth()) as client:
        r = client.post(
            f"{API_BASE}/subscriptions/{subscription_id}/cancel",
            json={"cancel_at_cycle_end": 1 if at_cycle_end else 0},
        )
    if r.status_code >= 400:
        raise RuntimeError(f"Razorpay cancellation failed ({r.status_code}): {r.text[:300]}")
    return r.json()


def verify_webhook(payload: bytes, signature: str) -> None:
    """
    Raises on a bad signature — never trust an unverified billing event.

    Razorpay signs with HMAC-SHA256 over the raw request body using the
    webhook secret, delivered in `X-Razorpay-Signature`. `hmac.compare_digest`
    rather than `==` so the comparison itself cannot leak timing information
    about how much of the signature matched.
    """
    if not settings.razorpay_webhook_secret:
        raise RuntimeError("RAZORPAY_WEBHOOK_SECRET is not configured")
    expected = hmac.new(
        settings.razorpay_webhook_secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature or ""):
        raise ValueError("Razorpay webhook signature mismatch")


# Razorpay subscription statuses that mean "the customer is paying and should
# have access" versus statuses that mean the opposite. `halted` is deliberately
# treated as `past_due` rather than `canceled` — it means Razorpay gave up
# retrying a failed charge, which is a billing problem to surface, not
# something that should silently downgrade someone to the free plan.
_STATUS_MAP = {
    "authenticated": "active", "active": "active",
    "pending": "past_due", "halted": "past_due",
    "cancelled": "canceled", "completed": "canceled", "expired": "canceled",
}


def parse_event(event: dict) -> dict | None:
    """
    Normalise the handful of subscription/payment events we act on into the
    same shape `stripe_service.parse_event` and `paypal_service.parse_event`
    return, so the billing router has exactly one code path that applies a
    parsed event to a `Subscription` row regardless of which gateway sent it.
    """
    etype = event.get("event")
    payload = event.get("payload") or {}

    sub_entity = (payload.get("subscription") or {}).get("entity")
    pay_entity = (payload.get("payment") or {}).get("entity")

    if sub_entity:
        notes = sub_entity.get("notes") or {}
        status = _STATUS_MAP.get(sub_entity.get("status"), sub_entity.get("status"))
        return {
            "owner_key": notes.get("owner_key"),
            "plan": notes.get("plan"),
            "status": status,
            "customer_id": sub_entity.get("customer_id"),
            "subscription_id": sub_entity.get("id"),
            "period_start": sub_entity.get("current_start"),
            "period_end": sub_entity.get("current_end"),
        }

    if etype == "payment.failed" and pay_entity:
        # A payment-level failure doesn't carry the subscription's notes
        # directly on older webhook payloads; the subscription id it references
        # is enough for the router to look the row up without the metadata.
        return {
            "owner_key": None,
            "plan": None,
            "status": "past_due",
            "customer_id": pay_entity.get("customer_id"),
            "subscription_id": pay_entity.get("subscription_id") or pay_entity.get("invoice_id"),
        }

    return None
