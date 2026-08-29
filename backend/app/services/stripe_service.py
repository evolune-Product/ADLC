"""
Stripe integration — checkout, customer portal, and webhook handling.

Deliberately thin and optional: the whole billing layer works without Stripe
configured (`is_configured()` is False → the API returns a simulated checkout
so self-hosted installs and local development can still exercise plan changes).
Enterprise deals are invoiced, not carded, so Stripe is the self-serve path only.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.services.metering_service import PLANS

log = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.stripe_secret_key)


def _client():
    import stripe
    stripe.api_key = settings.stripe_secret_key
    return stripe


def price_id_for(plan: str) -> str | None:
    return {
        "pro": settings.stripe_price_pro,
        "enterprise": settings.stripe_price_enterprise,
    }.get(plan)


def create_checkout_session(*, plan: str, owner_key: str, email: str | None,
                            customer_id: str | None, seats: int = 1) -> dict:
    """
    Returns {url, session_id, simulated}. `owner_key` is "org:<id>" or
    "user:<id>" and comes back on the webhook so we know who to upgrade.
    """
    if plan not in PLANS or plan == "free":
        raise ValueError(f"Cannot start checkout for plan '{plan}'")

    if not is_configured():
        log.info("[stripe not configured] simulated checkout: plan=%s owner=%s", plan, owner_key)
        return {
            "url": f"{settings.frontend_url}/billing?simulated=1&plan={plan}",
            "session_id": f"sim_{plan}_{owner_key}",
            "simulated": True,
        }

    stripe = _client()
    price = price_id_for(plan)
    if not price:
        raise ValueError(f"No Stripe price id configured for plan '{plan}'")

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price, "quantity": max(seats, 1)}],
        success_url=f"{settings.frontend_url}/billing?upgraded={plan}",
        cancel_url=f"{settings.frontend_url}/billing?canceled=1",
        customer=customer_id or None,
        customer_email=None if customer_id else email,
        client_reference_id=owner_key,
        metadata={"plan": plan, "owner_key": owner_key},
        subscription_data={"metadata": {"plan": plan, "owner_key": owner_key}},
        allow_promotion_codes=True,
    )
    return {"url": session.url, "session_id": session.id, "simulated": False}


def cancel_subscription(subscription_id: str) -> dict:
    """
    Cancel at period end, not immediately — a customer who cancels still paid
    for the current period and should keep what they paid for. Exists so
    `/billing/cancel` has a gateway-symmetric action for a Stripe subscriber
    who somehow has no `stripe_customer_id` on file to build a portal session
    from (the normal path is still the portal, which also handles payment
    method updates this does not).
    """
    if not is_configured() or subscription_id.startswith("sim_"):
        return {"status": "canceled", "simulated": True}
    stripe = _client()
    sub = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
    return {"status": sub.status, "cancel_at_period_end": True, "simulated": False}


def create_portal_session(customer_id: str) -> dict:
    if not is_configured():
        return {"url": f"{settings.frontend_url}/billing?simulated=1", "simulated": True}
    stripe = _client()
    session = stripe.billing_portal.Session.create(
        customer=customer_id, return_url=f"{settings.frontend_url}/billing"
    )
    return {"url": session.url, "simulated": False}


def verify_webhook(payload: bytes, signature: str):
    """Raises on an invalid signature — never trust an unverified billing event."""
    stripe = _client()
    return stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)


def parse_event(event) -> dict | None:
    """
    Normalise the handful of events we act on into
    {owner_key, plan, status, customer_id, subscription_id, period_start, period_end}.
    """
    etype = event["type"] if isinstance(event, dict) else event.type
    obj = (event["data"]["object"] if isinstance(event, dict) else event.data.object)

    def g(key, default=None):
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

    meta = g("metadata") or {}

    if etype == "checkout.session.completed":
        return {
            "owner_key": meta.get("owner_key") or g("client_reference_id"),
            "plan": meta.get("plan"),
            "status": "active",
            "customer_id": g("customer"),
            "subscription_id": g("subscription"),
        }

    if etype in ("customer.subscription.updated", "customer.subscription.created"):
        status = g("status")
        return {
            "owner_key": meta.get("owner_key"),
            "plan": meta.get("plan"),
            "status": "active" if status in ("active", "trialing") else status,
            "customer_id": g("customer"),
            "subscription_id": g("id"),
            "period_start": g("current_period_start"),
            "period_end": g("current_period_end"),
            "cancel_at_period_end": bool(g("cancel_at_period_end")),
        }

    if etype == "customer.subscription.deleted":
        return {
            "owner_key": meta.get("owner_key"), "plan": "free", "status": "canceled",
            "customer_id": g("customer"), "subscription_id": g("id"),
        }

    if etype == "invoice.payment_failed":
        return {
            "owner_key": meta.get("owner_key"), "plan": None, "status": "past_due",
            "customer_id": g("customer"), "subscription_id": g("subscription"),
        }

    return None
