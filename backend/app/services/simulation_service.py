"""
Simulation write-back — turning a SimulationFinding into something a human
sees outside the ADLC dashboard.

WHY THIS IS COMMENT-BASED, NOT "FILE A NEW TICKET"
Fraser's actual behavior is to auto-file a brand-new issue per finding. This
codebase's Jira and Linear connectors (`services/jira_service.py`,
`services/linear_service.py`) only ever grew a comment-on-an-existing-issue and
move-status path — `services/writeback_service.py` narrates run milestones
onto a ticket that already exists. Nothing anywhere in this codebase creates a
new remote issue (checked: no `create_issue` / `issueCreate` call exists for
any provider, GitHub included), and building one was explicitly out of scope
for this feature. So v1's write-back reuses exactly what already exists,
matching `writeback_service`'s own shape:

  * If the `SimulationRun` names an existing ticket (`SimulationRun.ticket_id`
    — "simulate the flow this ticket describes") AND that ticket's project has
    a connected, write-back-enabled Jira/Linear connection, the finding is
    posted as a comment on that real ticket via the same
    `jira_service.add_comment` / `linear_service.LinearClient.comment`
    functions `writeback_service` already calls. No new API-client code.
  * A workspace/Slack notification always fires regardless, via
    `services/notifier.notify_org` — that is what makes a finding visible to
    someone even when no ticket is linked, which is the common case (the v1
    "start a simulation" endpoint only requires a persona + a URL).

A write-back or notification failure can never raise out of here — same rule
`writeback_service._emit` documents for run milestones. A finding that could
not be filed or announced is still a finding worth keeping.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.connection import Connection
from app.models.persona import Persona
from app.models.project import Project
from app.models.simulation import SimulationFinding, SimulationRun
from app.models.ticket import Ticket
from app.services import jira_service, linear_service, notifier
from app.services.encryption import decrypt_token

log = logging.getLogger(__name__)

# Four finding severities mapped onto the three notification severities
# `notifier.py` already fans out on (email/Slack are gated by the recipient's
# own preferences, not by this mapping — see notifier.SEVERITY_BY_TYPE).
notifier.SEVERITY_BY_TYPE.setdefault("simulation.finding.critical", "critical")
notifier.SEVERITY_BY_TYPE.setdefault("simulation.finding.high", "warning")
notifier.SEVERITY_BY_TYPE.setdefault("simulation.finding.medium", "warning")
notifier.SEVERITY_BY_TYPE.setdefault("simulation.finding.low", "info")


def create_finding(
    db: Session, run: SimulationRun, *, severity: str, title: str, description: str,
    reproduction_steps: list | None = None, screenshot_path: str | None = None,
    step_number: int | None = None,
) -> SimulationFinding:
    """Persist a finding, then best-effort file it and notify."""
    finding = SimulationFinding(
        simulation_run_id=run.id,
        severity=severity if severity in ("critical", "high", "medium", "low") else "medium",
        title=(title or "Issue flagged during simulation")[:500],
        description=description or "",
        reproduction_steps=reproduction_steps or [],
        screenshot_path=screenshot_path,
        step_number=step_number,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)

    try:
        _file_and_notify(db, run, finding)
    except Exception:
        log.exception("Write-back/notify failed for simulation finding %s — finding still saved", finding.id)

    return finding


def _file_and_notify(db: Session, run: SimulationRun, finding: SimulationFinding) -> None:
    finding.posted_to_tracker = _post_to_tracker(db, run, finding)
    finding.notified = _notify(db, run, finding)
    db.commit()


def _post_to_tracker(db: Session, run: SimulationRun, finding: SimulationFinding) -> bool:
    """Comment on the linked ticket, if there is one and its project is wired
    up for write-back. See module docstring for why this is a comment on an
    existing ticket rather than a newly created one."""
    if not run.ticket_id:
        return False
    ticket = db.query(Ticket).filter(Ticket.id == run.ticket_id).first()
    if not ticket:
        return False
    project = db.query(Project).filter(Project.id == ticket.project_id).first()
    if not project or not (project.writeback or {}).get("enabled"):
        return False
    connection = (
        db.query(Connection).filter(Connection.id == project.jira_connection_id).first()
        if project.jira_connection_id else None
    )
    if not connection or connection.status != "connected":
        return False
    provider = (connection.type or "").lower()
    if provider not in ("jira", "linear"):
        return False

    body = _comment_body(run, finding)
    try:
        token = decrypt_token(connection.access_token) if connection.access_token else None
        if not token:
            return False
        if provider == "jira":
            email = (connection.metadata_ or {}).get("email") or ""
            return jira_service.add_comment(
                connection.workspace_url or "", email, token, ticket.jira_id, body,
            )
        issue_id = (ticket.raw_payload or {}).get("id")
        if not issue_id:
            return False
        return linear_service.LinearClient(token).comment(issue_id, body)
    except Exception:
        log.info("Tracker write-back failed for simulation finding %s", finding.id, exc_info=True)
        return False


def _comment_body(run: SimulationRun, finding: SimulationFinding) -> str:
    steps = "\n".join(f"- {s}" for s in (finding.reproduction_steps or [])[-8:])
    return (
        f"ADLC's persona simulation flagged a **{finding.severity}** issue while testing "
        f"this ticket's flow at {run.target_url}.\n\n"
        f"**{finding.title}**\n{finding.description}\n\n"
        f"Recent steps:\n{steps or '(no step history recorded)'}"
    )


def _notify(db: Session, run: SimulationRun, finding: SimulationFinding) -> bool:
    persona = db.query(Persona).filter(Persona.id == run.persona_id).first()
    persona_name = persona.name if persona else "A persona"
    try:
        notifier.notify_org(
            db, org_id=run.org_id, fallback_user_id=run.user_id,
            type=f"simulation.finding.{finding.severity}",
            title=f"[{finding.severity.upper()}] {finding.title}",
            body=f"{persona_name} hit this while testing {run.target_url}: {finding.description}",
            link=f"/simulations/{run.id}",
            payload={
                "simulation_run_id": str(run.id), "finding_id": str(finding.id),
                "severity": finding.severity,
            },
        )
        return True
    except Exception:
        log.exception("Notification failed for simulation finding %s", finding.id)
        return False
