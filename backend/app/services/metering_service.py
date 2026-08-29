"""
Usage metering and quota enforcement.

The business model is hybrid — platform fee plus metered runs — because per-seat
pricing collapsed from 21% to 15% of SaaS in twelve months while hybrid
base+usage became the 41% norm. That only works if every run is counted and
every plan limit is enforced, so this module is the single source of truth for:

  * which plan an owner (org or personal workspace) is on
  * how many runs they have used this period
  * whether the next run is allowed
  * what each run actually cost us in LLM spend
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.billing import Subscription, UsageRecord

# ── Plan catalogue ────────────────────────────────────────────────────────────
# Priced against the 2026 market: Devin ≈ $9/agent-hour, a GitHub agent session
# $6–12, standalone AI review $24–30/dev/mo. A governed run at $0.45–0.80
# marginal is a value story, and the overage price sits above worst-case token
# cost so heavy usage is accretive rather than dilutive.

PLANS: dict[str, dict] = {
    "free": {
        "name": "Free",
        "price_cents": 0,
        "included_runs": 25,
        "overage_cents_per_run": 0,      # hard stop, no overage
        "seats": 1,
        "max_projects": 1,
        "run_budget_cents": 60,
        "features": ["1 project", "25 runs/mo", "BYO LLM key", "community skills"],
        "requires_byo_key": True,
    },
    "pro": {
        # Same limits as Free — this is deliberately a paid tier with no real
        # differentiation yet, added to have a paid entry point before actual
        # feature gating lands in a later phase. Do not invent a differentiator
        # here that isn't real; the honest story is "same product, you're
        # paying for it" until that work is done.
        "name": "Pro",
        "price_cents": 10000,
        "included_runs": 25,
        "overage_cents_per_run": 0,
        "seats": 1,
        "max_projects": 1,
        "run_budget_cents": 60,
        "features": ["1 project", "25 runs/mo", "BYO LLM key", "community skills"],
        "requires_byo_key": True,
    },
    "enterprise": {
        "name": "Enterprise",
        "price_cents": 500000,
        "included_runs": 0,              # 0 = unlimited
        "overage_cents_per_run": 0,
        "seats": 25,
        "max_projects": 0,
        "run_budget_cents": 0,           # governed by policy, not plan
        "features": [
            "25 seats, unlimited runs", "Self-hosted / VPC", "BYO LLM",
            # OIDC only — SAML and SCIM are not built (see sso_service.py and
            # /security). Do not restate this as "SAML SSO" here; that string
            # used to ship straight to the in-app Billing page via
            # GET /billing/plans while /security and Trust.tsx correctly
            # disclosed the gap, so a paying customer's own billing page
            # promised something the rest of the product admitted it didn't do.
            "OIDC SSO (Okta, Entra ID, Google Workspace, Auth0)",
            "2-approver policies", "Evidence export", "SLA + CSM",
        ],
    },
}

PLAN_ORDER = ["free", "pro", "enterprise"]


@dataclass
class QuotaStatus:
    plan: str
    allowed: bool
    reason: str | None
    runs_used: int
    runs_included: int
    overage_runs: int
    overage_cents: int
    period_start: datetime
    period_end: datetime
    spend_millicents: int

    @property
    def runs_remaining(self) -> int:
        if self.runs_included == 0:
            return -1  # unlimited
        return max(self.runs_included - self.runs_used, 0)

    def as_dict(self) -> dict:
        return {
            "plan": self.plan,
            "plan_name": PLANS[self.plan]["name"],
            "allowed": self.allowed,
            "reason": self.reason,
            "runs_used": self.runs_used,
            "runs_included": self.runs_included,
            "runs_remaining": self.runs_remaining,
            "overage_runs": self.overage_runs,
            "overage_cents": self.overage_cents,
            "spend_usd": round(self.spend_millicents / 100_000, 4),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
        }


# ── Subscription lookup ───────────────────────────────────────────────────────

def get_or_create_subscription(db: Session, user_id: uuid.UUID, org_id: uuid.UUID | None) -> Subscription:
    """Every workspace has a subscription; free is the implicit default."""
    q = db.query(Subscription)
    sub = (q.filter(Subscription.org_id == org_id).first() if org_id
           else q.filter(Subscription.user_id == user_id, Subscription.org_id.is_(None)).first())
    if sub:
        return sub

    plan = PLANS["free"]
    now = datetime.now(timezone.utc)
    sub = Subscription(
        user_id=None if org_id else user_id,
        org_id=org_id,
        plan="free",
        status="active",
        seats=plan["seats"],
        included_runs=plan["included_runs"],
        overage_cents_per_run=plan["overage_cents_per_run"],
        max_projects=plan["max_projects"],
        run_budget_cents=plan["run_budget_cents"],
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def apply_plan(sub: Subscription, plan_key: str) -> Subscription:
    """Snapshot plan limits onto the subscription so later plan edits don't retro-apply."""
    plan = PLANS[plan_key]
    sub.plan = plan_key
    sub.included_runs = plan["included_runs"]
    sub.overage_cents_per_run = plan["overage_cents_per_run"]
    sub.max_projects = plan["max_projects"]
    sub.run_budget_cents = plan["run_budget_cents"]
    if plan["seats"]:
        sub.seats = plan["seats"]
    return sub


def _period_bounds(sub: Subscription) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = sub.current_period_start or now
    end = sub.current_period_end or (start + timedelta(days=30))
    if end < now:                       # roll a stale period forward
        while end < now:
            start, end = end, end + timedelta(days=30)
    return start, end


# ── Quota ─────────────────────────────────────────────────────────────────────

def check_quota(db: Session, user_id: uuid.UUID, org_id: uuid.UUID | None) -> QuotaStatus:
    sub = get_or_create_subscription(db, user_id, org_id)
    start, end = _period_bounds(sub)

    scope = (UsageRecord.org_id == org_id) if org_id else (
        (UsageRecord.user_id == user_id) & (UsageRecord.org_id.is_(None)))

    runs_used = (
        db.query(func.count(UsageRecord.id))
        .filter(scope, UsageRecord.kind == "run", UsageRecord.created_at >= start)
        .scalar()
    ) or 0

    spend = (
        db.query(func.coalesce(func.sum(UsageRecord.cost_millicents), 0))
        .filter(scope, UsageRecord.created_at >= start)
        .scalar()
    ) or 0

    included = sub.included_runs
    unlimited = included == 0
    overage_runs = 0 if unlimited else max(runs_used - included, 0)
    overage_cents = overage_runs * sub.overage_cents_per_run

    allowed, reason = True, None
    if sub.status in ("canceled", "past_due"):
        allowed, reason = False, f"Subscription is {sub.status}. Update billing to continue."
    elif not unlimited and runs_used >= included and sub.overage_cents_per_run == 0:
        allowed = False
        reason = (f"Plan limit reached ({runs_used}/{included} runs this period). "
                  f"Upgrade to keep shipping.")

    return QuotaStatus(
        plan=sub.plan, allowed=allowed, reason=reason,
        runs_used=runs_used, runs_included=included,
        overage_runs=overage_runs, overage_cents=overage_cents,
        period_start=start, period_end=end, spend_millicents=spend,
    )


# ── Recording ─────────────────────────────────────────────────────────────────

def record_run(db: Session, *, user_id, org_id, run_id) -> UsageRecord:
    rec = UsageRecord(user_id=user_id, org_id=org_id, run_id=run_id, kind="run", quantity=1)
    db.add(rec)
    db.commit()
    return rec


def record_llm_call(
    db: Session, *, user_id, org_id, run_id, agent_role: str,
    model: str, provider: str, input_tokens: int, output_tokens: int,
    cost_millicents: int, billable: bool = True,
) -> UsageRecord:
    rec = UsageRecord(
        user_id=user_id, org_id=org_id, run_id=run_id, kind="llm_call",
        agent_role=agent_role, model=model, provider=provider,
        input_tokens=input_tokens, output_tokens=output_tokens,
        cost_millicents=cost_millicents, billable=billable,
    )
    db.add(rec)
    db.commit()
    return rec


def run_spend_millicents(db: Session, run_id) -> int:
    return (
        db.query(func.coalesce(func.sum(UsageRecord.cost_millicents), 0))
        .filter(UsageRecord.run_id == run_id)
        .scalar()
    ) or 0


def run_over_budget(db: Session, run_id, budget_cents: int) -> bool:
    """
    Per-run budget ceiling. Without it, one pathological ticket (deep retry loop,
    huge repo context) can invert the margin on an entire month of a plan.
    """
    if not budget_cents:
        return False
    return run_spend_millicents(db, run_id) > budget_cents * 1000
