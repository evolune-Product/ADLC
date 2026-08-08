"""
Insights router — ROI analytics, agent scorecards, review findings, run feedback
and deployment history.

This is the retention and upsell surface: "we saved your team N hours last
month, at $X per merged PR, with these agents performing best." Every number is
derived from run rows, so any figure can be traced back to the run that produced
it.
"""
from __future__ import annotations

import csv
import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.insight import Deployment, ReviewFinding, RunFeedback, SourceRead
from app.models.project import Project
from app.models.run import Run
from app.models.user import User
from app.routers._helpers import OrgContext, get_optional_org, owner_filter
from app.routers.auth import get_current_user
from app.services import analytics_service

router = APIRouter()


class FeedbackBody(BaseModel):
    rating: int = Field(..., description="+1 or -1")
    agent_role: str | None = None
    category: str | None = None
    comment: str | None = None
    human_edits_loc: int = 0


def _scoped_project_ids(db: Session, current_user: User, org_ctx: Optional[OrgContext]) -> list[uuid.UUID]:
    return [p.id for p in db.query(Project).filter(owner_filter(Project, current_user, org_ctx)).all()]


def _assert_run_access(db: Session, run_id: uuid.UUID, current_user: User,
                       org_ctx: Optional[OrgContext]) -> Run:
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(404, "Run not found")
    if run.project_id not in _scoped_project_ids(db, current_user, org_ctx):
        raise HTTPException(404, "Run not found")
    return run


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics/summary")
def analytics_summary(
    days: int = Query(30, ge=1, le=365),
    manual_hours: float = Query(analytics_service.DEFAULT_MANUAL_HOURS_PER_TICKET, ge=0, le=80),
    hourly_rate: float = Query(analytics_service.DEFAULT_ENGINEER_HOURLY_USD, ge=0, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Headline ROI. `manual_hours` and `hourly_rate` are query params on purpose —
    an engineering leader defending this number to finance needs to set their
    own baseline rather than inherit ours.
    """
    ids = _scoped_project_ids(db, current_user, org_ctx)
    return analytics_service.summary(db, ids, days=days,
                                     manual_hours=manual_hours, hourly_rate=hourly_rate)


@router.get("/analytics/timeseries")
def analytics_timeseries(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    return analytics_service.timeseries(db, _scoped_project_ids(db, current_user, org_ctx), days=days)


@router.get("/analytics/agents")
def analytics_agents(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    return analytics_service.agent_scorecard(db, _scoped_project_ids(db, current_user, org_ctx), days=days)


@router.get("/analytics/export.csv")
def analytics_export(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    rows = analytics_service.export_rows(db, _scoped_project_ids(db, current_user, org_ctx), days=days)
    buf = io.StringIO()
    fields = ["run_id", "project_id", "status", "branch", "pr_url", "retry_count",
              "cycle_hours", "spend_usd", "created_at", "completed_at"]
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=agentic-sdlc-runs.csv"},
    )


# ── Deployments ───────────────────────────────────────────────────────────────

@router.get("/deployments")
def list_deployments(
    project_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ids = _scoped_project_ids(db, current_user, org_ctx)
    if project_id:
        ids = [i for i in ids if i == project_id]
    return analytics_service.deployment_history(db, ids, limit=limit)


@router.post("/deployments/{deployment_id}/rollback")
def mark_rolled_back(
    deployment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Record that a deployment was rolled back. The rollback itself happens in the
    customer's pipeline; what matters here is that the audit trail shows it.
    """
    dep = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    if not dep or dep.project_id not in _scoped_project_ids(db, current_user, org_ctx):
        raise HTTPException(404, "Deployment not found")
    dep.status = "rolled_back"
    db.commit()
    return {"id": str(dep.id), "status": dep.status}


# ── Review findings ───────────────────────────────────────────────────────────

@router.get("/runs/{run_id}/findings")
def run_findings(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _assert_run_access(db, run_id, current_user, org_ctx)
    rows = db.query(ReviewFinding).filter(ReviewFinding.run_id == run_id).all()
    from app.services.policy_service import SEVERITY_RANK, review_score
    rows.sort(key=lambda r: SEVERITY_RANK.get(r.severity, 0), reverse=True)
    return {
        "score": review_score(rows) if rows else None,
        "count": len(rows),
        "findings": [
            {
                "id": str(r.id),
                "severity": r.severity,
                "category": r.category,
                "file_path": r.file_path,
                "line": r.line,
                "message": r.message,
                "suggestion": r.suggestion,
                "posted_to_vcs": r.posted_to_vcs,
            }
            for r in rows
        ],
    }


# ── Source reads ──────────────────────────────────────────────────────────────

@router.get("/runs/{run_id}/sources")
def run_sources(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    What the agents read from outside the repository on this run, and how well.

    This sits next to the review findings on purpose. Both answer a question the
    approver has to be able to ask at the gate: findings say "is the code any
    good", this says "was the brief the code was written from any good". A plan
    built off a page that turned out to be a bot wall is not a code-quality
    problem, and nothing else in the run trace would show it.
    """
    _assert_run_access(db, run_id, current_user, org_ctx)
    rows = (
        db.query(SourceRead)
        .filter(SourceRead.run_id == run_id)
        .order_by(SourceRead.created_at.asc())
        .all()
    )

    ok = [r for r in rows if r.status == "ok"]
    # Totals are summed from the rows rather than stored, so the figure on
    # screen is always re-derivable from the evidence beneath it.
    tokens_before = sum(r.tokens_before for r in ok)
    tokens_after = sum(r.tokens_after for r in ok)

    return {
        "count": len(rows),
        "failed": len(rows) - len(ok),
        # The weakest read is the one that matters: an average would hide a
        # single unreadable page behind four clean ones.
        "worst_score": min((r.read_score for r in ok if r.read_score is not None), default=None),
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
        "tokens_saved": max(0, tokens_before - tokens_after),
        "sources": [
            {
                "id": str(r.id),
                "url": r.url,
                "title": r.title,
                "agent_role": r.agent_role,
                "status": r.status,
                "error": r.error,
                "read_score": r.read_score,
                "hallucination_risk": r.hallucination_risk,
                "html_bytes": r.html_bytes,
                "markdown_bytes": r.markdown_bytes,
                "tokens_before": r.tokens_before,
                "tokens_after": r.tokens_after,
                "flags": r.flags or [],
                "latency_ms": r.latency_ms,
                "cached": r.cached,
            }
            for r in rows
        ],
    }


# ── Run feedback (the data moat) ──────────────────────────────────────────────

@router.post("/runs/{run_id}/feedback", status_code=201)
def submit_feedback(
    run_id: uuid.UUID,
    body: FeedbackBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Thumbs up/down on agent output. This is what turns run history into an
    improvement loop — agent scorecards read straight from these rows.
    """
    _assert_run_access(db, run_id, current_user, org_ctx)
    if body.rating not in (1, -1):
        raise HTTPException(422, "rating must be +1 or -1")

    fb = RunFeedback(
        run_id=run_id, user_id=current_user.id, agent_role=body.agent_role,
        rating=body.rating, category=body.category, comment=body.comment,
        human_edits_loc=body.human_edits_loc,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return {"id": str(fb.id), "rating": fb.rating, "agent_role": fb.agent_role}


@router.get("/runs/{run_id}/feedback")
def list_feedback(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _assert_run_access(db, run_id, current_user, org_ctx)
    rows = db.query(RunFeedback).filter(RunFeedback.run_id == run_id).all()
    return [
        {
            "id": str(r.id), "rating": r.rating, "agent_role": r.agent_role,
            "category": r.category, "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
