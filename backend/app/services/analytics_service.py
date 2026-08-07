"""
ROI and productivity analytics.

The engineering-intelligence vendors (Faros, Jellyfish, LinearB, DX) own the
"what did AI actually save us?" conversation but cannot execute work. This
platform generates the ground-truth event stream — ticket → plan → PR → review →
approval → deploy, with timestamps and real token cost — so the value narrative
should be computed here rather than resold by someone else.

Everything is derived from run/step/usage rows: no separate telemetry pipeline,
no numbers that can't be traced back to a run.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.billing import UsageRecord
from app.models.insight import Deployment, RunFeedback
from app.models.project import Project
from app.models.run import Approval, Run, RunStep

# A human baseline for the same unit of work. Deliberately conservative and
# configurable — an inflated default would make the whole dashboard untrustworthy
# to the engineering leader who has to defend it.
DEFAULT_MANUAL_HOURS_PER_TICKET = 3.5
DEFAULT_ENGINEER_HOURLY_USD = 75.0


def _project_ids(db: Session, owner_filter_clause) -> list[uuid.UUID]:
    return [p.id for p in db.query(Project).filter(owner_filter_clause).all()]


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def summary(db: Session, project_ids: list[uuid.UUID], *, days: int = 30,
            manual_hours: float = DEFAULT_MANUAL_HOURS_PER_TICKET,
            hourly_rate: float = DEFAULT_ENGINEER_HOURLY_USD) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    if not project_ids:
        return _empty_summary(days)

    runs = (
        db.query(Run)
        .filter(Run.project_id.in_(project_ids), Run.created_at >= since)
        .all()
    )
    completed = [r for r in runs if r.status == "completed"]
    failed = [r for r in runs if r.status == "failed"]

    cycle_hours = [
        (r.completed_at - r.created_at).total_seconds() / 3600
        for r in completed if r.completed_at and r.created_at
    ]

    approval_latency = []
    for r in completed:
        first = (
            db.query(Approval)
            .filter(Approval.run_id == r.id)
            .order_by(Approval.created_at)
            .first()
        )
        step = (
            db.query(RunStep)
            .filter(RunStep.run_id == r.id, RunStep.agent_role == "dev")
            .order_by(RunStep.created_at.desc())
            .first()
        )
        if first and step and first.created_at and step.created_at:
            approval_latency.append((first.created_at - step.created_at).total_seconds() / 3600)

    spend_millicents = (
        db.query(func.coalesce(func.sum(UsageRecord.cost_millicents), 0))
        .filter(UsageRecord.run_id.in_([r.id for r in runs]) if runs else False)
        .scalar()
    ) or 0
    spend_usd = spend_millicents / 100_000

    hours_saved = max(len(completed) * manual_hours - sum(cycle_hours) * 0.15, 0)
    money_saved = hours_saved * hourly_rate
    total = len(runs)

    return {
        "window_days": days,
        "runs_total": total,
        "runs_completed": len(completed),
        "runs_failed": len(failed),
        "runs_awaiting_approval": len([r for r in runs if r.status == "awaiting_approval"]),
        "success_rate": round(len(completed) / total * 100, 1) if total else 0.0,
        "median_cycle_hours": round(_median(cycle_hours), 2),
        "median_approval_latency_hours": round(_median(approval_latency), 2),
        "spend_usd": round(spend_usd, 2),
        "cost_per_completed_run_usd": round(spend_usd / len(completed), 3) if completed else 0.0,
        "hours_saved": round(hours_saved, 1),
        "money_saved_usd": round(money_saved, 2),
        "roi_multiple": round(money_saved / spend_usd, 1) if spend_usd > 0.01 else None,
        "assumptions": {
            "manual_hours_per_ticket": manual_hours,
            "engineer_hourly_usd": hourly_rate,
            "note": "Hours saved = completed runs × manual baseline, minus 15% of "
                    "elapsed agent time as human supervision overhead.",
        },
    }


def _empty_summary(days: int) -> dict:
    return {
        "window_days": days, "runs_total": 0, "runs_completed": 0, "runs_failed": 0,
        "runs_awaiting_approval": 0, "success_rate": 0.0, "median_cycle_hours": 0.0,
        "median_approval_latency_hours": 0.0, "spend_usd": 0.0,
        "cost_per_completed_run_usd": 0.0, "hours_saved": 0.0, "money_saved_usd": 0.0,
        "roi_multiple": None,
        "assumptions": {
            "manual_hours_per_ticket": DEFAULT_MANUAL_HOURS_PER_TICKET,
            "engineer_hourly_usd": DEFAULT_ENGINEER_HOURLY_USD,
        },
    }


def timeseries(db: Session, project_ids: list[uuid.UUID], *, days: int = 30) -> list[dict]:
    """Daily runs / completions / spend — the shape every exec chart wants."""
    if not project_ids:
        return []
    since = datetime.now(timezone.utc) - timedelta(days=days)

    buckets: dict[str, dict] = defaultdict(
        lambda: {"runs": 0, "completed": 0, "failed": 0, "spend_usd": 0.0})

    for r in db.query(Run).filter(Run.project_id.in_(project_ids), Run.created_at >= since).all():
        key = r.created_at.date().isoformat()
        buckets[key]["runs"] += 1
        if r.status == "completed":
            buckets[key]["completed"] += 1
        elif r.status == "failed":
            buckets[key]["failed"] += 1

    usage = (
        db.query(UsageRecord.created_at, UsageRecord.cost_millicents)
        .join(Run, Run.id == UsageRecord.run_id)
        .filter(Run.project_id.in_(project_ids), UsageRecord.created_at >= since)
        .all()
    )
    for created_at, cost in usage:
        buckets[created_at.date().isoformat()]["spend_usd"] += (cost or 0) / 100_000

    return [
        {"date": day, **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in vals.items()}}
        for day, vals in sorted(buckets.items())
    ]


def agent_scorecard(db: Session, project_ids: list[uuid.UUID], *, days: int = 30) -> list[dict]:
    """
    Per-agent-role success rate, duration, spend and human feedback.

    This is the feedback loop: which agents (and therefore which skills) actually
    produce code humans approve. It is also the upsell conversation — "your QA
    agent passes 94% first time, your dev agent 61%; here is what to change".
    """
    if not project_ids:
        return []
    since = datetime.now(timezone.utc) - timedelta(days=days)

    run_ids = [r.id for r in db.query(Run.id).filter(
        Run.project_id.in_(project_ids), Run.created_at >= since).all()]
    if not run_ids:
        return []

    rows: dict[str, dict] = defaultdict(
        lambda: {"steps": 0, "success": 0, "failed": 0, "duration_ms": 0,
                 "spend_millicents": 0, "thumbs_up": 0, "thumbs_down": 0})

    for step in db.query(RunStep).filter(RunStep.run_id.in_(run_ids)).all():
        role = step.agent_role or "unknown"
        rows[role]["steps"] += 1
        if step.status == "success":
            rows[role]["success"] += 1
        elif step.status == "failed":
            rows[role]["failed"] += 1
        rows[role]["duration_ms"] += step.duration_ms or 0

    for rec in db.query(UsageRecord).filter(UsageRecord.run_id.in_(run_ids),
                                            UsageRecord.kind == "llm_call").all():
        rows[rec.agent_role or "unknown"]["spend_millicents"] += rec.cost_millicents or 0

    for fb in db.query(RunFeedback).filter(RunFeedback.run_id.in_(run_ids)).all():
        role = fb.agent_role or "unknown"
        if fb.rating > 0:
            rows[role]["thumbs_up"] += 1
        elif fb.rating < 0:
            rows[role]["thumbs_down"] += 1

    out = []
    for role, v in rows.items():
        graded = v["success"] + v["failed"]
        rated = v["thumbs_up"] + v["thumbs_down"]
        out.append({
            "agent_role": role,
            "steps": v["steps"],
            "success_rate": round(v["success"] / graded * 100, 1) if graded else 0.0,
            "avg_duration_sec": round(v["duration_ms"] / v["steps"] / 1000, 1) if v["steps"] else 0.0,
            "spend_usd": round(v["spend_millicents"] / 100_000, 3),
            "thumbs_up": v["thumbs_up"],
            "thumbs_down": v["thumbs_down"],
            "quality_score": round(v["thumbs_up"] / rated * 100, 1) if rated else None,
        })
    return sorted(out, key=lambda r: r["steps"], reverse=True)


def deployment_history(db: Session, project_ids: list[uuid.UUID], *, limit: int = 50) -> list[dict]:
    if not project_ids:
        return []
    rows = (
        db.query(Deployment)
        .filter(Deployment.project_id.in_(project_ids))
        .order_by(Deployment.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(d.id),
            "run_id": str(d.run_id) if d.run_id else None,
            "project_id": str(d.project_id),
            "environment": d.environment,
            "branch": d.branch,
            "sha": d.sha,
            "status": d.status,
            "approver_count": d.approver_count,
            "message": d.message,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in rows
    ]


def export_rows(db: Session, project_ids: list[uuid.UUID], *, days: int = 90) -> list[dict]:
    """Flat per-run rows for CSV export — what a board deck or a Faros/Jellyfish
    import actually needs."""
    if not project_ids:
        return []
    since = datetime.now(timezone.utc) - timedelta(days=days)
    runs = (
        db.query(Run)
        .filter(Run.project_id.in_(project_ids), Run.created_at >= since)
        .order_by(Run.created_at.desc())
        .all()
    )
    spend_by_run = dict(
        db.query(UsageRecord.run_id, func.coalesce(func.sum(UsageRecord.cost_millicents), 0))
        .filter(UsageRecord.run_id.in_([r.id for r in runs]) if runs else False)
        .group_by(UsageRecord.run_id)
        .all()
    )
    out = []
    for r in runs:
        cycle = ((r.completed_at - r.created_at).total_seconds() / 3600
                 if r.completed_at and r.created_at else None)
        out.append({
            "run_id": str(r.id),
            "project_id": str(r.project_id),
            "status": r.status,
            "branch": r.branch_name or "",
            "pr_url": r.pr_url or "",
            "retry_count": r.retry_count,
            "cycle_hours": round(cycle, 3) if cycle is not None else "",
            "spend_usd": round((spend_by_run.get(r.id, 0)) / 100_000, 4),
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "completed_at": r.completed_at.isoformat() if r.completed_at else "",
        })
    return out
