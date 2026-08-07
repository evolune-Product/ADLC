"""
Billing router — plans, usage, checkout, portal, Stripe webhooks, BYO-LLM keys.

Works with or without Stripe configured: without it, plan changes are applied
directly and checkout returns a simulated URL, so self-hosted and local installs
still exercise the full quota path.
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
from app.routers._helpers import OrgContext, get_optional_org
from app.routers.auth import get_current_user
from app.services import stripe_service
from app.services.encryption import encrypt_token
from app.services.metering_service import (PLANS, PLAN_ORDER, apply_plan,
                                           check_quota, get_or_create_subscription)

log = logging.getLogger(__name__)
router = APIRouter()


class CheckoutBody(BaseModel):
    plan: str = Field(..., description="team | growth | enterprise")
    seats: int = 1


class ByoKeyBody(BaseModel):
    provider: str = Field(..., description="anthropic | openai | azure | ollama")
    api_key: str


class PlanChangeBody(BaseModel):
    plan: str


def _owner_key(current_user: User, org_ctx: Optional[OrgContext]) -> str:
    return f"org:{org_ctx.org_id}" if org_ctx else f"user:{current_user.id}"


def _require_admin(org_ctx: Optional[OrgContext]) -> None:
    if org_ctx and org_ctx.role not in ("owner", "admin"):
        raise HTTPException(403, "Only owners and admins can manage billing")


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
            "stripe_customer_id": sub.stripe_customer_id,
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

    org_id = org_ctx.org_id if org_ctx else None
    sub = get_or_create_subscription(db, current_user.id, org_id)

    session = stripe_service.create_checkout_session(
        plan=body.plan,
        owner_key=_owner_key(current_user, org_ctx),
        email=current_user.email,
        customer_id=sub.stripe_customer_id,
        seats=body.seats,
    )

    # No Stripe configured (self-hosted / local): apply the plan directly so the
    # rest of the product is exercisable end to end.
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
    _require_admin(org_ctx)
    sub = get_or_create_subscription(db, current_user.id, org_ctx.org_id if org_ctx else None)
    if not sub.stripe_customer_id and stripe_service.is_configured():
        raise HTTPException(400, "No billing account yet — start a subscription first")
    return stripe_service.create_portal_session(sub.stripe_customer_id or "")


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


# ── Stripe webhook ────────────────────────────────────────────────────────────

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    if not stripe_service.is_configured():
        raise HTTPException(503, "Stripe is not configured")

    payload = await request.body()
    try:
        event = stripe_service.verify_webhook(payload, stripe_signature)
    except Exception as exc:
        raise HTTPException(400, f"Invalid Stripe signature: {exc}")

    parsed = stripe_service.parse_event(event)
    if not parsed or not parsed.get("owner_key"):
        return {"received": True, "handled": False}

    kind, _, raw_id = parsed["owner_key"].partition(":")
    q = db.query(Subscription)
    sub = (q.filter(Subscription.org_id == raw_id).first() if kind == "org"
           else q.filter(Subscription.user_id == raw_id, Subscription.org_id.is_(None)).first())
    if not sub:
        log.warning("Stripe event for unknown owner %s", parsed["owner_key"])
        return {"received": True, "handled": False}

    if parsed.get("plan") and parsed["plan"] in PLANS:
        apply_plan(sub, parsed["plan"])
    if parsed.get("status"):
        sub.status = parsed["status"]
    sub.stripe_customer_id = parsed.get("customer_id") or sub.stripe_customer_id
    sub.stripe_subscription_id = parsed.get("subscription_id") or sub.stripe_subscription_id
    if parsed.get("period_start"):
        sub.current_period_start = datetime.fromtimestamp(parsed["period_start"], tz=timezone.utc)
    if parsed.get("period_end"):
        sub.current_period_end = datetime.fromtimestamp(parsed["period_end"], tz=timezone.utc)
    if "cancel_at_period_end" in parsed:
        sub.cancel_at_period_end = bool(parsed["cancel_at_period_end"])
    db.commit()

    return {"received": True, "handled": True, "plan": sub.plan, "status": sub.status}
