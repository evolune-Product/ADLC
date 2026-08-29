"""
Rule-based routing for generic Work requests.

Only rule-based this session, on purpose. AI-assisted routing needs an LLM
call, its own cost/latency/failure-mode handling, and its own careful review —
that is real work and does not belong bolted onto this pass. The extension
point is `route_work`'s return value: an AI router can later be tried first
and fall through to this function, without either caller changing.

Routing precedence:
  1. Explicit — Work.department_id was already set by the caller. Their
     choice always wins; routing never overrides an explicit assignment.
  2. Matched — a case-insensitive substring match between the department's
     name and the work's title/description.
  3. Unmatched — no department could be determined. department_id stays
     None and the work's status is left at "new" so a human triages it.
     Never guess wrong and silently misroute a request.

Routing chooses *where* work goes; it never grants write access. The router
still runs every request through the same `can_write` / department-team
cross-tenant checks a manual `department_id` assignment goes through — see
`backend/app/routers/work.py::_validate_dept_team`, called identically
whether department_id arrived on the request body or was filled in by
`route_work` after the fact.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.work import Work


@dataclass
class RoutingDecision:
    department_id: object  # uuid.UUID | None
    confidence: str        # "explicit" | "matched" | "unmatched"
    reasoning: str


def route_work(db: Session, work: Work) -> RoutingDecision:
    """
    Decide (or confirm) which department a Work item belongs to.

    Never mutates `work` — the caller applies the decision, so it stays free
    to log/display the reasoning before or after committing the change.
    """
    if work.department_id is not None:
        return RoutingDecision(
            department_id=work.department_id,
            confidence="explicit",
            reasoning="Department was explicitly set on this request; routing left it unchanged.",
        )

    haystack = f"{work.title or ''} {work.description or ''}".lower()
    if not haystack.strip():
        return RoutingDecision(
            department_id=None,
            confidence="unmatched",
            reasoning="No title or description text to match against — needs a human to triage.",
        )

    departments = (
        db.query(Department)
        .filter(Department.organization_id == work.organization_id, Department.status == "active")
        .order_by(Department.name)
        .all()
    )
    for dept in departments:
        name = (dept.name or "").strip().lower()
        if name and name in haystack:
            return RoutingDecision(
                department_id=dept.id,
                confidence="matched",
                reasoning=f"Matched department '{dept.name}' by name appearing in the request's title/description.",
            )

    return RoutingDecision(
        department_id=None,
        confidence="unmatched",
        reasoning=(
            "No department name matched the request text (simple substring rule; not ML-driven). "
            "Left unrouted for a human to triage rather than guessing. AI-assisted routing is a "
            "documented future extension point, not attempted here."
        ),
    )
