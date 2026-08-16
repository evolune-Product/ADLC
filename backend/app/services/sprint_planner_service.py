"""
AI Sprint Planner — turns a ticket backlog into a scored, dependency-aware
sprint proposal in one metered LLM call.

WHY THIS EXISTS
None of the execution-layer competitors (Devin, Factory, GitHub Agent HQ,
OpenHands) plan the sprint a ticket comes from — they execute tickets one at a
time (documents/PRODUCT_STRATEGY.md Horizon 4, §5.14). **Correction, logged
2026-08-16:** Atlassian's Rovo does ship a Sprint Planning Agent — capacity-
based story allocation plus backlog dependency-conflict detection — so "no
competitor plans sprints" is false as a category-wide claim; it is true only
of the execution-layer vendors above. See documents/RESEARCH_TRIAGE_2026-08.md.
The differentiation that survives: Rovo is Jira-only and stops at the backlog
— this estimate feeds a governed pipeline (policy gate, cost attribution,
audit trail) across Jira *and* Linear, not a standalone grooming tool tied to
one system of record. This still uses the same provider abstraction,
metering, and quota enforcement every agent run goes through — billed and
BYO-key-aware like everything else, not a side channel.

WHAT "BACKLOG" MEANS HERE
Tickets with zero runs ever started against them. A ticket already in flight
has an opinion (a run, maybe a PR) that estimation shouldn't second-guess;
re-planning a ticket that failed is a human decision, not an automatic one.

HOW THE DEPENDENCY GRAPH IS SCORED
The model returns `depends_on` as a list of *other backlog tickets' jira_ids*
per ticket — it can only point at tickets it was actually shown, which keeps
the graph inside the plan instead of hallucinating cross-project references.
A ticket is `blocked` if it was selected for the sprint but something it
depends on was not. The plan is `at_risk` at 90% of capacity and `blocked` if
any included ticket is blocked — capacity alone doesn't tell you the sprint
is healthy if its first task can't start.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.connection import Connection
from app.models.project import Project
from app.models.run import Run
from app.models.sprint import SprintPlan, TicketEstimate
from app.models.ticket import Ticket
from app.services import jira_service, linear_service, llm_service, metering_service
from app.services.encryption import decrypt_token

log = logging.getLogger(__name__)

MAX_BACKLOG_TICKETS = 60  # keeps the prompt bounded; a >60-ticket backlog needs triage first, not a bigger call

_PLAN_TOOL = {
    "name": "submit_sprint_plan",
    "description": "Submit story-point estimates, dependencies, and a sprint selection for the given backlog.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "2-3 sentence summary of the proposed sprint and any risk."},
            "estimates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "jira_id": {"type": "string", "description": "The ticket's id exactly as given, e.g. PROJ-123."},
                        "story_points": {"type": "integer", "description": "Fibonacci-ish: 1, 2, 3, 5, 8, or 13."},
                        "complexity_reasoning": {"type": "string", "description": "1-2 sentences on why this size."},
                        "depends_on": {
                            "type": "array", "items": {"type": "string"},
                            "description": "jira_ids of OTHER tickets in this same backlog that must land first. Empty if none.",
                        },
                        "include_in_sprint": {"type": "boolean", "description": "Whether this ticket fits within the stated capacity, in priority order."},
                    },
                    "required": ["jira_id", "story_points", "complexity_reasoning", "depends_on", "include_in_sprint"],
                },
            },
        },
        "required": ["summary", "estimates"],
    },
}

_SYSTEM = """You are a senior engineering lead doing sprint planning for an AI-agent-executed \
software delivery pipeline. You will be shown a project's context and a list of backlog tickets \
(never-yet-started). For each ticket:

1. Estimate story points on a Fibonacci-ish scale (1, 2, 3, 5, 8, 13) based on the ticket's \
description, type and priority. A 1 is a trivial config/copy change; a 13 is a multi-system \
change with real design risk.
2. Note any OTHER ticket in this same list it genuinely depends on (must land first) — most \
tickets depend on nothing; do not invent dependencies to seem thorough.
3. Decide whether it fits inside the stated sprint capacity, filling by priority first, then by \
value-to-effort ratio, and respecting dependency order (never include a ticket whose dependency \
you did not also include, unless that dependency already fits on its own).

Call submit_sprint_plan with every ticket you were shown — omitting one is not an option, even if \
you would give it 0 points confidence; use your best estimate instead."""


def _ticket_lines(tickets: list[Ticket]) -> str:
    lines = []
    for t in tickets:
        desc = (t.description or "").strip().replace("\n", " ")[:400]
        lines.append(f"- {t.jira_id} [{t.type or 'task'}/{t.priority or 'normal'}] {t.title}\n  {desc}")
    return "\n".join(lines)


def resolve_estimate(e: dict, by_jira_id: dict, included_ids: set[str]) -> dict | None:
    """
    Pure: turn one raw tool-call estimate into the row-shaped dict plan_sprint
    persists. Split out from plan_sprint so the blocked/points-clamping logic
    is testable without a DB session or an LLM call.
    """
    ticket = by_jira_id.get(e.get("jira_id"))
    if not ticket:
        return None  # model referenced a ticket it wasn't shown — drop rather than guess
    included = e.get("jira_id") in included_ids
    depends_on = [d for d in (e.get("depends_on") or []) if d in by_jira_id and d != e.get("jira_id")]
    blocked = included and any(d not in included_ids for d in depends_on)
    points = max(1, min(21, int(e.get("story_points") or 1)))
    return {
        "ticket": ticket, "story_points": points,
        "complexity_reasoning": (e.get("complexity_reasoning") or "").strip()[:1000],
        "depends_on": depends_on, "included_in_sprint": included,
        "risk": "blocked" if blocked else "on_track",
    }


def plan_health(capacity_points: int, committed_points: int, any_blocked: bool) -> str:
    """Pure. Blocked beats at_risk: a sprint that can't start its first ticket
    isn't merely close to full, it cannot proceed as planned regardless of
    capacity math."""
    if any_blocked:
        return "blocked"
    if capacity_points and committed_points >= capacity_points * 0.9:
        return "at_risk"
    return "on_track"


def backlog(db: Session, project_id) -> list[Ticket]:
    """Tickets with no run ever started — see module docstring."""
    started_ticket_ids = {r.ticket_id for r in db.query(Run.ticket_id)
                          .filter(Run.project_id == project_id, Run.ticket_id.isnot(None)).all()}
    all_tickets = (db.query(Ticket).filter(Ticket.project_id == project_id)
                   .order_by(Ticket.synced_at.desc()).all())
    return [t for t in all_tickets if t.id not in started_ticket_ids][:MAX_BACKLOG_TICKETS]


def plan_sprint(db: Session, project: Project, *, capacity_points: int,
                user_id, org_id, byo_provider: str | None, byo_key: str | None) -> SprintPlan:
    tickets = backlog(db, project.id)
    if not tickets:
        raise ValueError("No unstarted tickets in this project's backlog to plan from.")

    user_prompt = (
        f"Project context:\n{(project.context_md or '(none given)').strip()[:2000]}\n\n"
        f"Sprint capacity: {capacity_points} story points.\n\n"
        f"Backlog ({len(tickets)} tickets):\n{_ticket_lines(tickets)}"
    )

    result = llm_service.complete(
        system=_SYSTEM, user=user_prompt, tool=_PLAN_TOOL,
        byo_provider=byo_provider, byo_key=byo_key,
    )
    metering_service.record_llm_call(
        db, user_id=user_id, org_id=org_id, run_id=None, agent_role="sprint_planner",
        model=result.model, provider=result.provider,
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        cost_millicents=result.cost_millicents, billable=byo_key is None,
    )

    by_jira_id = {t.jira_id: t for t in tickets}
    raw_estimates = (result.tool_input or {}).get("estimates", [])

    plan = SprintPlan(project_id=project.id, capacity_points=capacity_points, summary=(result.tool_input or {}).get("summary"))
    db.add(plan)
    db.flush()  # need plan.id for the FK below

    included_ids: set[str] = set()
    for e in raw_estimates:
        if e.get("include_in_sprint") and e.get("jira_id") in by_jira_id:
            included_ids.add(e["jira_id"])

    committed = 0
    rows: list[TicketEstimate] = []
    for e in raw_estimates:
        resolved = resolve_estimate(e, by_jira_id, included_ids)
        if not resolved:
            continue
        if resolved["included_in_sprint"]:
            committed += resolved["story_points"]
        rows.append(TicketEstimate(
            sprint_plan_id=plan.id, ticket_id=resolved["ticket"].id,
            story_points=resolved["story_points"], complexity_reasoning=resolved["complexity_reasoning"],
            depends_on=resolved["depends_on"], included_in_sprint=resolved["included_in_sprint"],
            risk=resolved["risk"],
        ))
    db.add_all(rows)

    plan.committed_points = committed
    plan.health = plan_health(capacity_points, committed, any(r.risk == "blocked" for r in rows))
    db.commit()
    db.refresh(plan)
    return plan


def write_back_estimates(db: Session, plan: SprintPlan) -> int:
    """
    Post one comment per estimated ticket, same opt-in convention as
    services/writeback_service.py: project.writeback.enabled gates it, a
    failure here can never raise — a stale tracker connection shouldn't stop
    a planning session that already succeeded and is already saved.
    Returns the number of comments actually posted.
    """
    project = plan.project
    config = project.writeback or {}
    if not config.get("enabled") or not project.jira_connection_id:
        return 0

    connection = db.query(Connection).filter(Connection.id == project.jira_connection_id).first()
    if not connection or connection.status != "connected":
        return 0

    provider = (connection.type or "").lower()
    if provider not in ("jira", "linear"):
        return 0

    token = decrypt_token(connection.access_token) if connection.access_token else None
    if not token:
        return 0

    posted = 0
    for estimate in plan.estimates:
        ticket = estimate.ticket
        body = (
            f"ADLC sprint planning estimated this ticket at **{estimate.story_points} points**.\n"
            f"{estimate.complexity_reasoning or ''}\n"
            + (f"Depends on: {', '.join(estimate.depends_on)}\n" if estimate.depends_on else "")
            + (f"Selected for the current sprint (capacity {plan.capacity_points})."
               if estimate.included_in_sprint else "Not selected for the current sprint.")
        )
        try:
            if provider == "jira":
                email = (connection.metadata_ or {}).get("email") or ""
                ok = jira_service.add_comment(connection.workspace_url or "", email, token, ticket.jira_id, body)
            else:
                issue_id = (ticket.raw_payload or {}).get("id")
                ok = bool(issue_id) and linear_service.LinearClient(token).comment(issue_id, body)
            posted += 1 if ok else 0
        except Exception:
            log.info("Sprint estimate write-back failed for %s", ticket.jira_id, exc_info=True)

    plan.written_back = posted > 0
    db.commit()
    return posted
