"""
Ticket write-back — closing the loop back to Jira and Linear.

THE PROBLEM
Tickets sync *in* and nothing ever goes back. A ticket enters a run, agents
plan it, write it, test it, review it, a human approves it and it deploys to
production — and the ticket sits in "To Do" the whole time. Everybody not
watching the ADLC dashboard, which is most of the team and all of the
stakeholders, has no idea any of it happened. Devin and Factory both update the
ticket; this closes the gap.

TWO RULES, AND THEY ARE THE WHOLE DESIGN

1. **A write-back failure can never affect a run.** Jira being down, a workflow
   with no matching transition, a revoked token — none of those are reasons to
   fail a deploy that has already been approved. Every call here is wrapped,
   logged, and returns a bool nobody is obliged to check.

2. **A comment is always attempted, a transition only if configured.** Moving
   someone's ticket between columns is an opinionated act and every team's
   workflow is different; posting a comment saying what happened is safe
   everywhere. So the status map is opt-in per project and an unmatched status
   is a no-op, while the narration always goes out.

WHAT IT WRITES
One comment per milestone, in the voice of a colleague reporting progress —
not a webhook dump. Each one carries the link that makes it actionable: the
pull request, the run, the environment.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.connection import Connection
from app.models.project import Project
from app.models.run import Run
from app.models.ticket import Ticket
from app.services import jira_service, linear_service
from app.services.encryption import decrypt_token

log = logging.getLogger(__name__)

# Sensible defaults for the two workflows almost everyone actually uses. A
# project can override any of them; an empty string means "do not move the
# ticket at this milestone".
DEFAULT_STATUS_MAP = {
    "running": "In Progress",
    "awaiting_approval": "In Review",
    "completed": "Done",
    "failed": "",          # deliberately blank — a failed run is not a ticket state
}


@dataclass
class WritebackTarget:
    provider: str          # 'jira' | 'linear'
    connection: Connection
    ticket: Ticket
    status_map: dict


def _config(project: Project) -> dict:
    return project.writeback or {}


def _target(db: Session, run: Run) -> WritebackTarget | None:
    """Resolve everything needed to write back, or None if this run cannot."""
    project = db.query(Project).filter(Project.id == run.project_id).first()
    if not project or not run.ticket_id:
        return None

    config = _config(project)
    if not config.get("enabled"):
        return None

    connection = (
        db.query(Connection).filter(Connection.id == project.jira_connection_id).first()
        if project.jira_connection_id else None
    )
    ticket = db.query(Ticket).filter(Ticket.id == run.ticket_id).first()
    if not connection or not ticket or connection.status != "connected":
        return None

    provider = (connection.type or "").lower()
    if provider not in ("jira", "linear"):
        return None

    return WritebackTarget(
        provider=provider,
        connection=connection,
        ticket=ticket,
        status_map={**DEFAULT_STATUS_MAP, **(config.get("status_map") or {})},
    )


def _post_comment(target: WritebackTarget, body: str) -> bool:
    connection = target.connection
    try:
        token = decrypt_token(connection.access_token) if connection.access_token else None
        if not token:
            return False

        if target.provider == "jira":
            email = (connection.metadata_ or {}).get("email") or ""
            return jira_service.add_comment(
                connection.workspace_url or "", email, token,
                target.ticket.jira_id, body,
            )

        # Linear's mutations take the issue's internal id, not its identifier.
        # It was captured on sync; without it there is nothing to address.
        issue_id = (target.ticket.raw_payload or {}).get("id")
        if not issue_id:
            return False
        return linear_service.LinearClient(token).comment(issue_id, body)
    except Exception:
        log.info("Write-back comment failed for %s", target.ticket.jira_id, exc_info=True)
        return False


def _move(target: WritebackTarget, milestone: str) -> bool:
    status = (target.status_map.get(milestone) or "").strip()
    if not status:
        return False

    connection = target.connection
    try:
        token = decrypt_token(connection.access_token) if connection.access_token else None
        if not token:
            return False

        if target.provider == "jira":
            email = (connection.metadata_ or {}).get("email") or ""
            return jira_service.transition_issue(
                connection.workspace_url or "", email, token,
                target.ticket.jira_id, status,
            )

        issue_id = (target.ticket.raw_payload or {}).get("id")
        team_key = (target.ticket.jira_id or "").split("-")[0]
        if not issue_id or not team_key:
            return False
        client = linear_service.LinearClient(token)
        state_id = client.state_id(team_key, status)
        return client.move_issue(issue_id, state_id) if state_id else False
    except Exception:
        log.info("Write-back transition failed for %s", target.ticket.jira_id, exc_info=True)
        return False


def _emit(db: Session, run: Run, milestone: str, body: str) -> None:
    """
    The one entry point every milestone goes through.

    Wrapped whole: this is called from inside the Celery task that owns a
    deploy, and an exception escaping here would fail a run because a ticket
    tracker was unreachable.
    """
    try:
        target = _target(db, run)
        if not target:
            return
        commented = _post_comment(target, body)
        moved = _move(target, milestone)
        log.info("Write-back %s for %s: comment=%s moved=%s",
                 milestone, target.ticket.jira_id, commented, moved)
    except Exception:
        log.exception("Write-back raised for run %s at %s — ignored", run.id, milestone)


# ── milestones ──────────────────────────────────────────────────────────────

def on_run_started(db: Session, run: Run, ticket_title: str | None = None) -> None:
    _emit(db, run, "running",
          f"ADLC started an agent run on this ticket.\n"
          f"Follow it live: {_run_link(run)}")


def on_awaiting_approval(db: Session, run: Run, *, pr_url: str | None,
                         review_score: int | None) -> None:
    score = f" The reviewer scored the change {review_score}/100." if review_score is not None else ""
    _emit(db, run, "awaiting_approval",
          f"The agents finished and opened a pull request.{score}\n"
          f"It is now waiting on a human approval before anything can deploy.\n"
          f"{pr_url or ''}\n"
          f"Approve or request changes: {_run_link(run)}")


def on_changes_requested(db: Session, run: Run, comment: str | None) -> None:
    note = f'\n\n"{comment.strip()}"' if comment else ""
    # No status move: the ticket stays where it is, because the work is still
    # in review — it just needs another pass.
    _emit(db, run, "awaiting_approval",
          f"A reviewer requested changes on the agent's pull request.{note}")


def on_deployed(db: Session, run: Run, environment: str) -> None:
    # Only the final environment closes the ticket. Promoting to dev is not
    # "done", and a ticket that flips to Done on the first environment then sits
    # there while prod is still pending is worse than no write-back at all.
    milestone = "completed" if _is_last_environment(db, run, environment) else "running"
    _emit(db, run, milestone,
          f"Deployed to **{environment}** after human approval.\n"
          f"Audit trail: {_run_link(run)}")


def on_failed(db: Session, run: Run, error: str | None) -> None:
    detail = f"\n\n{error.strip()[:400]}" if error else ""
    _emit(db, run, "failed",
          f"The agent run on this ticket failed and did not deploy.{detail}\n"
          f"{_run_link(run)}")


# ── helpers ─────────────────────────────────────────────────────────────────

def _run_link(run: Run) -> str:
    from app.config import settings
    return f"{settings.frontend_url.rstrip('/')}/runs/{run.id}"


def _is_last_environment(db: Session, run: Run, environment: str) -> bool:
    project = db.query(Project).filter(Project.id == run.project_id).first()
    targets = (project.deploy_targets or []) if project else []
    if not targets:
        return True
    last = targets[-1]
    name = last.get("env") if isinstance(last, dict) else last
    return (name or "").lower() == (environment or "").lower()
