"""
Billing router — plans, usage, checkout, portal, gateway webhooks, BYO-LLM keys.

Three payment gateways, chosen at checkout time and independent of each other:

    stripe     the global default — cards, most of the world
    razorpay   the India rail — UPI/netbanking/cards domestically at 2%+GST,
               bank transfer internationally at 1%+GST with no forex markup
    paypal     for a buyer with a PayPal business account and no corporate
               card program, common outside the US/EU card networks

Each works with or without being configured: an unconfigured gateway applies
the plan change directly and returns a simulated checkout URL, exactly like
Stripe already did before Razorpay and PayPal existed — so a deployment that
enables none, one, two or all three gateways always has a working billing
path, and self-hosted/local installs exercise the full quota system with zero
payment configuration.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.billing import Subscription, UsageRecord
from app.models.user import User
from app.routers._helpers import OrgContext, get_optional_org, is_domain_admin
from app.routers.auth import get_current_user
from app.services import paypal_service, razorpay_service, stripe_service
from app.services.encryption import encrypt_token
from app.services.metering_service import (PLANS, PLAN_ORDER, apply_plan,
                                           check_quota, get_or_create_subscription)

log = logging.getLogger(__name__)
router = APIRouter()

GATEWAYS = ("stripe", "razorpay", "paypal")


class CheckoutBody(BaseModel):
    plan: str = Field(..., description="pro | enterprise")
    gateway: str = Field("stripe", description="stripe | razorpay | paypal")
    seats: int = 1


class ByoKeyBody(BaseModel):
    provider: str = Field(..., description="anthropic | openai | azure | ollama")
    api_key: str


class PlanChangeBody(BaseModel):
    plan: str


def _owner_key(current_user: User, org_ctx: Optional[OrgContext]) -> str:
    return f"org:{org_ctx.org_id}" if org_ctx else f"user:{current_user.id}"


def _require_admin(org_ctx: Optional[OrgContext]) -> None:
    # Spending authority — the subscription, the payment method, the plan.
    # A billing manager owns this without needing admin rights over agents,
    # skills or org membership; owner and admin still pass every domain.
    if org_ctx and not is_domain_admin(org_ctx, "billing"):
        raise HTTPException(403, "Only owners, admins and billing managers can manage billing")


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("/plans")
def list_plans():
    """Public plan catalogue — also drives the pricing page."""
    return [
        {"key": key, **{k: v for k, v in PLANS[key].items()}}
        for key in PLAN_ORDER
    ]


@router.get("")
def get_billing(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_id = org_ctx.org_id if org_ctx else None
    sub = get_or_create_subscription(db, current_user.id, org_id)
    quota = check_quota(db, current_user.id, org_id)

    scope = (UsageRecord.org_id == org_id) if org_id else (
        (UsageRecord.user_id == current_user.id) & (UsageRecord.org_id.is_(None)))

    by_model = (
        db.query(
            UsageRecord.model,
            func.count(UsageRecord.id),
            func.coalesce(func.sum(UsageRecord.input_tokens), 0),
            func.coalesce(func.sum(UsageRecord.output_tokens), 0),
            func.coalesce(func.sum(UsageRecord.cost_millicents), 0),
        )
        .filter(scope, UsageRecord.kind == "llm_call",
                UsageRecord.created_at >= quota.period_start)
        .group_by(UsageRecord.model)
        .all()
    )

    return {
        "subscription": {
            "plan": sub.plan,
            "plan_name": PLANS[sub.plan]["name"],
            "status": sub.status,
            "seats": sub.seats,
            "included_runs": sub.included_runs,
            "overage_cents_per_run": sub.overage_cents_per_run,
            "run_budget_cents": sub.run_budget_cents,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "byo_llm_provider": sub.byo_llm_provider,
            "byo_llm_configured": bool(sub.byo_llm_key),
            "payment_provider": sub.payment_provider,
            "stripe_customer_id": sub.stripe_customer_id,
            "razorpay_subscription_id": sub.razorpay_subscription_id,
            "paypal_subscription_id": sub.paypal_subscription_id,
        },
        "quota": quota.as_dict(),
        "usage_by_model": [
            {
                "model": model or "unknown",
                "calls": calls,
                "input_tokens": inp,
                "output_tokens": out,
                "cost_usd": round(cost / 100_000, 4),
            }
            for model, calls, inp, out, cost in by_model
        ],
        # Per-gateway, not one flag — the checkout page needs to know which
        # payment buttons are real and which would fall back to a simulated
        # upgrade, and that answer differs per gateway on the same deployment.
        "gateways_enabled": {
            "stripe": stripe_service.is_configured(),
            "razorpay": razorpay_service.is_configured(),
            "paypal": paypal_service.is_configured(),
        },
        # Kept for anything still reading the old single flag.
        "stripe_enabled": stripe_service.is_configured(),
    }


# ── Checkout / portal ─────────────────────────────────────────────────────────

@router.post("/checkout")
def create_checkout(
    body: CheckoutBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _require_admin(org_ctx)
    if body.plan not in PLANS or body.plan == "free":
        raise HTTPException(422, f"Unknown plan '{body.plan}'")
    if body.gateway not in GATEWAYS:
        raise HTTPException(422, f"Unknown payment gateway '{body.gateway}' — must be one of {GATEWAYS}")

    org_id = org_ctx.org_id if org_ctx else None
    sub = get_or_create_subscription(db, current_user.id, org_id)
    owner_key = _owner_key(current_user, org_ctx)

    if body.gateway == "stripe":
        session = stripe_service.create_checkout_session(
            plan=body.plan, owner_key=owner_key, email=current_user.email,
            customer_id=sub.stripe_customer_id, seats=body.seats,
        )
    elif body.gateway == "razorpay":
        session = razorpay_service.create_subscription(
            plan=body.plan, owner_key=owner_key, email=current_user.email, seats=body.seats,
        )
        if not session.get("simulated"):
            sub.razorpay_subscription_id = session["subscription_id"]
    else:  # paypal
        session = paypal_service.create_subscription(
            plan=body.plan, owner_key=owner_key, email=current_user.email,
        )
        if not session.get("simulated"):
            sub.paypal_subscription_id = session["subscription_id"]

    # The gateway a checkout was started on, recorded immediately rather than
    # only once a webhook confirms payment — the cancel and portal endpoints
    # below need to know which gateway's API to call, and a subscription only
    # ever has one gateway active: switching means starting a new checkout,
    # not two running in parallel.
    if not session.get("simulated"):
        sub.payment_provider = body.gateway

    # No gateway configured (self-hosted / local, or this specific gateway
    # disabled): apply the plan directly so the rest of the product is
    # exercisable end to end regardless of which gateway button was clicked.
    if session.get("simulated"):
        apply_plan(sub, body.plan)
        sub.status = "active"
        sub.current_period_start = datetime.now(timezone.utc)
        sub.current_period_end = sub.current_period_start + timedelta(days=30)

    db.commit()
    return session


@router.post("/portal")
def create_portal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    A self-serve billing portal. Stripe has one; Razorpay and PayPal do not —
    there is no hosted page to hand back for either, so this stays Stripe-only
    and `/billing/cancel` below is the gateway-agnostic action a Razorpay or
    PayPal subscriber uses instead.
    """
    _require_admin(org_ctx)
    sub = get_or_create_subscription(db, current_user.id, org_ctx.org_id if org_ctx else None)
    if sub.payment_provider and sub.payment_provider != "stripe":
        raise HTTPException(
            400,
            f"This subscription is billed through {sub.payment_provider}, which has no "
            f"self-serve portal — use POST /billing/cancel to cancel it instead.",
        )
    if not sub.stripe_customer_id and stripe_service.is_configured():
        raise HTTPException(400, "No billing account yet — start a subscription first")
    return stripe_service.create_portal_session(sub.stripe_customer_id or "")


@router.post("/cancel")
def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Cancel the active subscription, regardless of which gateway it is billed
    through. Stripe customers should generally prefer the portal — it also
    handles payment-method updates the portal offers that this endpoint does
    not — but this works for Stripe too, which matters for a subscription that
    somehow has no `stripe_customer_id` on file to build a portal session from.
    """
    _require_admin(org_ctx)
    sub = get_or_create_subscription(db, current_user.id, org_ctx.org_id if org_ctx else None)

    if sub.plan == "free" or not sub.payment_provider:
        raise HTTPException(400, "There is no paid subscription to cancel")

    if sub.payment_provider == "stripe":
        if not sub.stripe_subscription_id:
            raise HTTPException(400, "No Stripe subscription id on file — use the billing portal")
        stripe_service.cancel_subscription(sub.stripe_subscription_id)
        sub.cancel_at_period_end = True
    elif sub.payment_provider == "razorpay":
        if not sub.razorpay_subscription_id:
            raise HTTPException(400, "No Razorpay subscription id on file")
        razorpay_service.cancel_subscription(sub.razorpay_subscription_id, at_cycle_end=True)
        sub.cancel_at_period_end = True
    elif sub.payment_provider == "paypal":
        if not sub.paypal_subscription_id:
            raise HTTPException(400, "No PayPal subscription id on file")
        paypal_service.cancel_subscription(sub.paypal_subscription_id)
        # PayPal cancels immediately rather than at period end — there is no
        # "cancel at cycle end" option on their Subscriptions API.
        sub.status = "canceled"
        apply_plan(sub, "free")
    else:
        raise HTTPException(400, f"Unknown payment provider '{sub.payment_provider}' on this subscription")

    db.commit()
    return {"plan": sub.plan, "status": sub.status, "cancel_at_period_end": sub.cancel_at_period_end}


@router.put("/plan")
def change_plan(
    body: PlanChangeBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Direct plan change — self-hosted/enterprise path where billing is invoiced."""
    _require_admin(org_ctx)
    if body.plan not in PLANS:
        raise HTTPException(422, f"Unknown plan '{body.plan}'")
    if stripe_service.is_configured() and body.plan != "free":
        raise HTTPException(400, "Use /billing/checkout when Stripe is enabled")

    sub = get_or_create_subscription(db, current_user.id, org_ctx.org_id if org_ctx else None)
    apply_plan(sub, body.plan)
    sub.status = "active"
    db.commit()
    return {"plan": sub.plan, "status": sub.status}


# ── BYO LLM key ───────────────────────────────────────────────────────────────

@router.put("/llm-key")
def set_byo_key(
    body: ByoKeyBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Bring-your-own model key. Stored Fernet-encrypted, used in place of the
    platform key for every agent call in this workspace.
    """
    _require_admin(org_ctx)
    sub = get_or_create_subscription(db, current_user.id, org_ctx.org_id if org_ctx else None)
    sub.byo_llm_provider = body.provider
    sub.byo_llm_key = encrypt_token(body.api_key)
    db.commit()
    return {"provider": sub.byo_llm_provider, "configured": True}


@router.delete("/llm-key", status_code=status.HTTP_204_NO_CONTENT)
def clear_byo_key(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _require_admin(org_ctx)
    sub = get_or_create_subscription(db, current_user.id, org_ctx.org_id if org_ctx else None)
    sub.byo_llm_provider = None
    sub.byo_llm_key = None
    db.commit()


# ── Gateway webhooks ──────────────────────────────────────────────────────────
#
# One shared applier for all three gateways. `stripe_service`, `razorpay_service`
# and `paypal_service` each normalise their own wildly different event shapes
# into the same flat dict — {owner_key, plan, status, customer_id,
# subscription_id, period_start, period_end, cancel_at_period_end} — precisely
# so this section only has to know how to apply *one* shape to a Subscription
# row, not three.

def _find_subscription(db: Session, parsed: dict, provider: str) -> Subscription | None:
    """
    Look the row up by `owner_key` when the event carries one — every gateway's
    subscription-lifecycle events do. A handful of events don't (Razorpay's
    `payment.failed`, PayPal's `PAYMENT.SALE.DENIED` reference the payment, not
    the subscription's own metadata), so those fall back to matching on the
    gateway's own subscription id, which the row already has on file from the
    checkout that created it.
    """
    owner_key = parsed.get("owner_key")
    if owner_key:
        kind, _, raw_id = owner_key.partition(":")
        q = db.query(Subscription)
        return (q.filter(Subscription.org_id == raw_id).first() if kind == "org"
                else q.filter(Subscription.user_id == raw_id, Subscription.org_id.is_(None)).first())

    sub_id = parsed.get("subscription_id")
    if not sub_id:
        return None
    column = {
        "stripe": Subscription.stripe_subscription_id,
        "razorpay": Subscription.razorpay_subscription_id,
        "paypal": Subscription.paypal_subscription_id,
    }[provider]
    return db.query(Subscription).filter(column == sub_id).first()


def _to_datetime(value) -> datetime:
    """Stripe and Razorpay send unix timestamps; PayPal sends ISO 8601
    strings (`next_billing_time`). Normalised here so the shared applier below
    never has to know which gateway produced the value it is looking at."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _apply_billing_event(sub: Subscription, parsed: dict, provider: str) -> None:
    if parsed.get("plan") and parsed["plan"] in PLANS:
        apply_plan(sub, parsed["plan"])
    if parsed.get("status"):
        sub.status = parsed["status"]

    if provider == "stripe":
        sub.stripe_customer_id = parsed.get("customer_id") or sub.stripe_customer_id
        sub.stripe_subscription_id = parsed.get("subscription_id") or sub.stripe_subscription_id
    elif provider == "razorpay":
        sub.razorpay_subscription_id = parsed.get("subscription_id") or sub.razorpay_subscription_id
    elif provider == "paypal":
        sub.paypal_subscription_id = parsed.get("subscription_id") or sub.paypal_subscription_id
        sub.paypal_payer_id = parsed.get("customer_id") or sub.paypal_payer_id

    if parsed.get("period_start"):
        sub.current_period_start = _to_datetime(parsed["period_start"])
    if parsed.get("period_end"):
        sub.current_period_end = _to_datetime(parsed["period_end"])
    if "cancel_at_period_end" in parsed:
        sub.cancel_at_period_end = bool(parsed["cancel_at_period_end"])


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """Path kept as the bare `/webhook` for backward compatibility — this is
    the endpoint any deployment configured in Stripe's dashboard before
    Razorpay and PayPal existed, and moving it would silently break every
    existing webhook subscription. Razorpay and PayPal get their own paths
    below since neither had one to preserve."""
    if not stripe_service.is_configured():
        raise HTTPException(503, "Stripe is not configured")

    payload = await request.body()
    try:
        event = stripe_service.verify_webhook(payload, stripe_signature)
    except Exception as exc:
        raise HTTPException(400, f"Invalid Stripe signature: {exc}")

    parsed = stripe_service.parse_event(event)
    if not parsed:
        return {"received": True, "handled": False}

    sub = _find_subscription(db, parsed, "stripe")
    if not sub:
        log.warning("Stripe event for unknown owner %s", parsed.get("owner_key"))
        return {"received": True, "handled": False}

    _apply_billing_event(sub, parsed, "stripe")
    db.commit()
    return {"received": True, "handled": True, "plan": sub.plan, "status": sub.status}


@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
    db: Session = Depends(get_db),
):
    if not razorpay_service.is_configured():
        raise HTTPException(503, "Razorpay is not configured")

    import json

    payload = await request.body()
    try:
        razorpay_service.verify_webhook(payload, x_razorpay_signature)
    except Exception as exc:
        raise HTTPException(400, f"Invalid Razorpay signature: {exc}")

    event = json.loads(payload)
    parsed = razorpay_service.parse_event(event)
    if not parsed:
        return {"received": True, "handled": False}

    sub = _find_subscription(db, parsed, "razorpay")
    if not sub:
        log.warning("Razorpay event for unknown subscription %s", parsed.get("subscription_id"))
        return {"received": True, "handled": False}

    _apply_billing_event(sub, parsed, "razorpay")
    db.commit()
    return {"received": True, "handled": True, "plan": sub.plan, "status": sub.status}


@router.post("/webhook/paypal")
async def paypal_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    if not paypal_service.is_configured():
        raise HTTPException(503, "PayPal is not configured")

    payload = await request.body()
    # PayPal's signature covers a specific set of transmission headers, not
    # only the body — the full header set has to reach the verifier, unlike
    # Stripe's and Razorpay's single-header HMAC.
    headers = {k.lower(): v for k, v in request.headers.items()}
    try:
        event = paypal_service.verify_webhook(headers, payload)
    except Exception as exc:
        raise HTTPException(400, f"Invalid PayPal webhook: {exc}")

    parsed = paypal_service.parse_event(event)
    if not parsed:
        return {"received": True, "handled": False}

    sub = _find_subscription(db, parsed, "paypal")
    if not sub:
        log.warning("PayPal event for unknown subscription %s", parsed.get("subscription_id"))
        return {"received": True, "handled": False}

    _apply_billing_event(sub, parsed, "paypal")
    db.commit()
    return {"received": True, "handled": True, "plan": sub.plan, "status": sub.status}
