"""
The bridge between the conversation and the pipeline.

This module is the reason the chat surface is worth building rather than
integrating. Slack can show you a run; it cannot *be* where the run is
started, approved and recorded, because Slack has no rows for agents, pods or
approval policies. Here all three live in the same database as the message, so
three things become possible that a webhook integration structurally cannot do:

  1. `@qa look at PROJ-214` starts a real run, attributed to the person who
     typed it, counted against their org's quota, subject to the same policy
     gate as a run started from the Runs page.
  2. Run steps narrate themselves into the channel the work belongs to, so the
     conversation and the evidence are the same scroll.
  3. An approval is a message. Pressing Approve in chat writes the same
     `Approval` row and the same `AuditLog` entry as pressing it in the UI —
     there is no second, less-governed path.

Everything here is best-effort. A failure to narrate a run into a channel must
never fail the run: the pipeline is the product, the commentary is not.
"""
from __future__ import annotations

import logging
import re
import uuid

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.department import Department, Team
from app.models.pod import Pod, PodAgent
from app.models.project import Project
from app.models.run import Run
from app.models.ticket import Ticket
from app.models.user import User
from app.models.work import Work
from app.models.workflow import Workflow, WorkflowExecution
from app.models.workspace import Channel, Message
from app.services import org_roles
from app.services import workspace_service as ws

log = logging.getLogger(__name__)

# A ticket key as a human types it: PROJ-214, ABC-7. Matched case-insensitively
# but always compared upper-cased, because nobody types the key in caps in chat.
_TICKET_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-\d+)\b", re.IGNORECASE)

SLASH_HELP = """**Commands**
`/run <TICKET-KEY>` — start a run for that ticket with this channel's project pod
`/status [TICKET-KEY]` — the latest run's state, or the last five runs here
`/approve <run-id> [comment]` — approve a run that is waiting
`/reject <run-id> <reason>` — send a run back
`/catchup` — summarise what you missed in this channel
`/invite @someone` — add a person or an agent to this channel
`/help` — this message

You can also just @mention an agent with a ticket key, e.g. `@dev PROJ-214`."""


# ── Channels that belong to something ─────────────────────────────────────────

def channel_for_project(db: Session, project: Project, *, created_by=None) -> Channel:
    """
    Find or create the channel for a project.

    Auto-created on first need rather than at project creation for the same
    reason the default channels are: projects that predate this feature would
    otherwise never get one.
    """
    existing = db.query(Channel).filter(Channel.project_id == project.id,
                                        Channel.run_id.is_(None)).first()
    if existing:
        return existing

    ch = Channel(
        user_id=project.user_id,
        org_id=project.org_id,
        kind="channel",
        name=project.name,
        slug=ws.slugify(f"proj-{project.name}"),
        topic=f"Runs, approvals and deploys for {project.name}.",
        project_id=project.id,
        created_by=created_by or project.user_id,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)

    ws.ensure_member(db, ch, user_id=project.user_id, role="owner")
    _add_pod_agents(db, ch, project)
    return ch


def _add_pod_agents(db: Session, channel: Channel, project: Project) -> None:
    """Put the project's pod agents in the channel so they can be @mentioned."""
    if not project.pod_id:
        return
    rows = (
        db.query(Agent)
        .join(PodAgent, PodAgent.agent_id == Agent.id)
        .filter(PodAgent.pod_id == project.pod_id)
        .all()
    )
    for agent in rows:
        ws.ensure_member(db, channel, agent_id=agent.id, role="member")


def channel_for_department(db: Session, department: Department, *, created_by=None) -> Channel:
    """
    Find or create the channel for a department. Same lazy-on-first-need
    shape as `channel_for_project` — a department that predates this feature,
    or one created before workspace was ever touched, still gets a channel
    the first time it needs one (a mention dispatch, or department creation
    itself, which calls this eagerly — see routers/departments.py).
    """
    existing = db.query(Channel).filter(Channel.department_id == department.id, Channel.team_id.is_(None)).first()
    if existing:
        return existing

    ch = Channel(
        user_id=created_by or department.head_user_id,
        org_id=department.organization_id,
        kind="channel",
        name=department.name,
        slug=ws.slugify(f"dept-{department.name}"),
        topic=f"Work, workflows and updates for {department.name}.",
        department_id=department.id,
        created_by=created_by or department.head_user_id,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    if department.head_user_id:
        ws.ensure_member(db, ch, user_id=department.head_user_id, role="owner")
    return ch


def channel_for_team(db: Session, team: Team, *, created_by=None) -> Channel:
    """Find or create the channel for a team. Same shape as `channel_for_department`."""
    existing = db.query(Channel).filter(Channel.team_id == team.id).first()
    if existing:
        return existing

    ch = Channel(
        user_id=created_by,
        org_id=team.organization_id,
        kind="channel",
        name=team.name,
        slug=ws.slugify(f"team-{team.name}"),
        topic=f"Work and updates for {team.name}.",
        department_id=team.department_id,
        team_id=team.id,
        created_by=created_by,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return ch


def default_deploys_channel(db: Session, *, user_id, org_id) -> Channel | None:
    """The workspace-wide #deploys channel, if it exists yet."""
    scope = (
        Channel.org_id == org_id if org_id
        else and_(Channel.user_id == user_id, Channel.org_id.is_(None))
    )
    return db.query(Channel).filter(scope, Channel.slug == "deploys").first()


# ── Run narration ─────────────────────────────────────────────────────────────

# Which run events are worth a message. The step-level firehose
# (`run:step:log`) is deliberately absent — it belongs on the run trace page,
# not in a channel a human is trying to read.
NARRATED = {
    "run:started": ("Run started", "info"),
    "run:awaiting_approval": ("Waiting for approval", "warning"),
    "run:approved": ("Approved", "info"),
    "run:completed": ("Run completed", "success"),
    "run:failed": ("Run failed", "critical"),
    "run:policy:blocked": ("Blocked by policy", "warning"),
    "deploy:succeeded": ("Deployed", "success"),
    "deploy:failed": ("Deploy failed", "critical"),
}


def narrate_run_event(db: Session, run_id, event: str, data: dict | None = None) -> Message | None:
    """
    Post a run event into the channel that owns the work.

    Called from the run pipeline. Wrapped in a blanket try/except by design:
    the caller is a Celery task in the middle of a deploy, and a missing
    channel must not become a failed run.
    """
    if event not in NARRATED:
        return None
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            return None
        project = db.query(Project).filter(Project.id == run.project_id).first()
        if not project:
            return None

        channel = channel_for_project(db, project)
        title, severity = NARRATED[event]
        ticket = db.query(Ticket).filter(Ticket.id == run.ticket_id).first() if run.ticket_id else None
        label = ticket.jira_id if ticket and ticket.jira_id else str(run.id)[:8]

        # An approval request is not narration, it is a gate. It renders with
        # buttons and it is the one run event allowed to page people.
        kind = "approval_request" if event == "run:awaiting_approval" else "system"

        body = f"{title} — {label}"
        if ticket and ticket.title:
            body += f": {ticket.title}"
        if event == "run:failed" and (data or {}).get("error"):
            body += f"\n{str(data['error'])[:300]}"

        return ws.post_message(
            db,
            channel=channel,
            body=body,
            kind=kind,
            payload={
                "event": event,
                "run_id": str(run.id),
                "ticket_key": label,
                "severity": severity,
                "pr_url": run.pr_url,
                "pr_number": run.pr_number,
                "status": run.status,
                **(data or {}),
            },
            notify=(kind == "approval_request"),
        )
    except Exception:
        log.exception("Could not narrate %s for run %s", event, run_id)
        return None


# ── Workflow narration (steps 15-16 item 3) ────────────────────────────────────
#
# Same shape as `narrate_run_event` on purpose — a `WorkflowExecution` status
# change is narrated into whichever channel the linked Work item (or, failing
# that, the workflow's department) owns, exactly the way a Run's status change
# is narrated into its project's channel. Best-effort by the same rule: a
# failure to post a chat message must never fail a workflow step.

WORKFLOW_NARRATED = {
    "workflow:started": ("Workflow started", "info"),
    "workflow:awaiting_approval": ("Waiting for approval", "warning"),
    "workflow:human_task": ("Waiting on a person", "warning"),
    "workflow:completed": ("Workflow completed", "success"),
    "workflow:failed": ("Workflow failed", "critical"),
}


def _channel_for_execution(db: Session, execution: WorkflowExecution, workflow: Workflow) -> Channel | None:
    """
    The channel a workflow execution's narration belongs in: the Work item's
    department/team channel if it has one, otherwise the workflow's own
    department channel, otherwise nothing (no channel to narrate into, which
    is a normal state for a department-less org-wide workflow).
    """
    if execution.work_id:
        work = db.query(Work).filter(Work.id == execution.work_id).first()
        if work:
            if work.team_id:
                team = db.query(Team).filter(Team.id == work.team_id).first()
                if team:
                    return channel_for_team(db, team, created_by=team.department.head_user_id if team.department else None) or None
            if work.department_id:
                dept = db.query(Department).filter(Department.id == work.department_id).first()
                if dept:
                    return channel_for_department(db, dept)
    if workflow.department_id:
        dept = db.query(Department).filter(Department.id == workflow.department_id).first()
        if dept:
            return channel_for_department(db, dept)
    return None


def narrate_workflow_event(db: Session, execution_id, event: str, data: dict | None = None) -> Message | None:
    """Post a workflow execution status change into the channel that owns the work."""
    if event not in WORKFLOW_NARRATED:
        return None
    try:
        execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        if not execution:
            return None
        workflow = db.query(Workflow).filter(Workflow.id == execution.workflow_id).first()
        if not workflow:
            return None
        channel = _channel_for_execution(db, execution, workflow)
        if not channel:
            return None

        title, severity = WORKFLOW_NARRATED[event]
        body = f"{title} — {workflow.name}"
        if event == "workflow:failed" and execution.error:
            body += f"\n{execution.error[:300]}"

        kind = "approval_request" if event == "workflow:awaiting_approval" else "system"
        return ws.post_message(
            db, channel=channel, body=body, kind=kind,
            payload={
                "event": event, "execution_id": str(execution.id),
                "workflow_id": str(workflow.id), "severity": severity,
                "status": execution.status, **(data or {}),
            },
            notify=(kind == "approval_request"),
        )
    except Exception:
        log.exception("Could not narrate %s for workflow execution %s", event, execution_id)
        return None


# ── Dispatching work from a message ───────────────────────────────────────────

def resolve_ticket(db: Session, project: Project, text: str) -> Ticket | None:
    """Find the ticket a message is talking about, by key."""
    keys = [m.group(1).upper() for m in _TICKET_RE.finditer(text or "")]
    if not keys:
        return None
    return (
        db.query(Ticket)
        .filter(Ticket.project_id == project.id, func_upper_in(Ticket.jira_id, keys))
        .first()
    )


def func_upper_in(column, keys: list[str]):
    """Case-insensitive IN. Kept explicit so the index decision stays visible:
    ticket keys are stored as the tracker returned them, which is upper-case in
    Jira and Linear both, so this almost always hits the plain index."""
    return or_(*[column.ilike(k) for k in keys])


def dispatch_agent_mention(
    db: Session,
    *,
    channel: Channel,
    message: Message,
    current_user: User,
    agent_ids: list[str],
    org_ctx,
) -> list[dict]:
    """
    An agent was @mentioned. Decide whether that is a request to do work.

    A mention only starts a run when all three of these hold: the channel is
    attached to a project, the message names a ticket, and the project has a
    pod. Anything less is ambiguous, and a platform that guesses at "start
    autonomous work on production" is a platform nobody will approve for
    purchase. When it cannot act it says exactly what is missing.
    """
    if not agent_ids:
        return []

    if not channel.project_id:
        _reply(db, channel, message,
               "I can only start runs in a channel attached to a project. "
               "Open the project and use its channel, or say `/help`.")
        return []

    project = db.query(Project).filter(Project.id == channel.project_id).first()
    if not project:
        return []

    ticket = resolve_ticket(db, project, message.body)
    if not ticket:
        _reply(db, channel, message,
               "Name a ticket and I'll pick it up — for example `@dev PROJ-214`. "
               "I don't start work on an unnamed task.")
        return []

    if not project.pod_id:
        _reply(db, channel, message,
               f"{project.name} has no pod assigned, so there is nothing to run the ticket through. "
               "Assign one in the project settings first.")
        return []

    # Read-only members can talk; they cannot spend the org's quota. Same rule
    # as the Runs page, enforced here rather than trusted from the client.
    if org_ctx and not org_roles.can_write(org_ctx.role):
        _reply(db, channel, message, "You have read-only access and can't trigger runs.")
        return []

    pod = db.query(Pod).filter(Pod.id == project.pod_id).first()

    # Same creation path as the Runs page and the public API, so the project's
    # concurrency cap applies to a chat mention exactly as it does to a button.
    from app.routers.runs import create_and_dispatch_run
    from fastapi import HTTPException
    try:
        run = create_and_dispatch_run(
            db,
            project_id=project.id,
            ticket_id=ticket.id,
            pod_id=project.pod_id,
            triggered_by=current_user.id,
            org_id=org_ctx.org_id if org_ctx else None,
        )
    except HTTPException as e:
        # The queue is full. Say so in the channel rather than failing silently.
        _reply(db, channel, message, str(e.detail))
        return []
    except Exception as e:
        _reply(db, channel, message, f"Could not start the run: {e}")
        return []

    held = run.status == "queued"

    agent = db.query(Agent).filter(Agent.id == uuid.UUID(agent_ids[0])).first()
    body = (
        f"Queued **{ticket.jira_id or ticket.title}** — {ticket.title}. "
        f"This project is at its concurrent-run limit; I'll start as soon as a slot frees."
        if held else
        f"Picking up **{ticket.jira_id or ticket.title}** — {ticket.title}"
    )
    ws.post_message(
        db,
        channel=channel,
        body=body,
        agent_id=agent.id if agent else None,
        kind="agent",
        parent_id=message.id,
        payload={"run_id": str(run.id), "ticket_key": ticket.jira_id,
                 "pod": pod.name if pod else None,
                 "event": "run:held" if held else "run:queued"},
        org_ctx=org_ctx,
        notify=False,
    )
    return [{"run_id": str(run.id), "ticket": ticket.jira_id, "status": run.status}]


# ── @department / @team mentions → generic Work (steps 15-16 item 2) ──────────
#
# Deterministic only, per the spec: an explicit `@deptname` or `@teamname`
# token resolved against that org's own Department/Team slugs and names,
# never free-form NLU over the rest of the sentence. `@sales please follow up
# with Acme` creates a Work item titled from the message text, routes it
# through the same `routing_service.route_work` a manually-created Work item
# goes through (explicit department always wins there too), and replies in
# the channel with what was created and where it landed — the same
# "narrate exactly what happened" convention `dispatch_agent_mention` follows.

_MENTION_TOKEN_RE = re.compile(r"@([a-zA-Z][a-zA-Z0-9_-]*)")


def resolve_dept_team_mentions(db: Session, text: str, org_id) -> list:
    """
    Every Department/Team whose slug or name an @token in `text` matches
    exactly (case-insensitive), in org `org_id`. Deterministic exact match —
    no fuzzy matching, no substring guessing at what a human might have meant.
    """
    if not org_id:
        return []
    tokens = {m.group(1).lower() for m in _MENTION_TOKEN_RE.finditer(text or "")}
    if not tokens:
        return []

    hits: list = []
    depts = db.query(Department).filter(Department.organization_id == org_id, Department.status == "active").all()
    for d in depts:
        if d.slug.lower() in tokens or (d.name or "").lower() in tokens:
            hits.append(("department", d))
    teams = db.query(Team).filter(Team.organization_id == org_id, Team.status == "active").all()
    for t in teams:
        if t.slug.lower() in tokens or (t.name or "").lower() in tokens:
            hits.append(("team", t))
    return hits


def dispatch_department_mention(
    db: Session, *, channel: Channel, message: Message, current_user: User, org_ctx,
) -> list[dict]:
    """
    An @department or @team was mentioned in a message. Create a Work item
    from the message text, route it (explicit department/team from the
    mention always wins, same as a manually-filled Work.department_id), and
    reply in the channel with what happened. Read-only members can talk but
    not spend the org's quota — same rule `dispatch_agent_mention` enforces.
    """
    if not org_ctx or not org_ctx.org_id:
        return []
    hits = resolve_dept_team_mentions(db, message.body, org_ctx.org_id)
    if not hits:
        return []
    if not org_roles.can_write(org_ctx.role):
        _reply(db, channel, message, "You have read-only access and can't open a work request.")
        return []

    from app.services.routing_service import route_work

    created = []
    # De-dup: a message mentioning both a team and its own department should
    # not open two Work items for the same request.
    seen_dept_ids = set()
    for kind, obj in hits:
        dept_id = obj.id if kind == "department" else obj.department_id
        if dept_id in seen_dept_ids:
            continue
        seen_dept_ids.add(dept_id)

        work = Work(
            organization_id=org_ctx.org_id,
            department_id=dept_id if kind == "department" else obj.department_id,
            team_id=obj.id if kind == "team" else None,
            requester_user_id=current_user.id,
            type="chat_request",
            title=(message.body or "").strip()[:500] or f"Request from #{channel.name or 'chat'}",
            status="new",
        )
        decision = route_work(db, work)
        # The mention itself is the explicit routing signal, so it always
        # wins — `route_work` returns "explicit" unchanged whenever
        # department_id is already set, which it is here.
        work.routing_confidence = decision.confidence
        work.routing_reasoning = decision.reasoning or f"Routed by explicit @{obj.slug} mention in chat."
        db.add(work)
        db.commit()
        db.refresh(work)

        target_channel = channel_for_team(db, obj, created_by=current_user.id) if kind == "team" else \
            channel_for_department(db, obj, created_by=current_user.id)
        label = f"team {obj.name}" if kind == "team" else f"department {obj.name}"
        _reply(
            db, channel, message,
            f"Opened work item **{work.title[:80]}** for {label}"
            + (f" — see #{target_channel.slug}" if target_channel and target_channel.id != channel.id else "."),
        )
        created.append({"work_id": str(work.id), "department_id": str(work.department_id) if work.department_id else None,
                        "team_id": str(work.team_id) if work.team_id else None, "kind": kind})
    return created


def _reply(db: Session, channel: Channel, parent: Message, body: str) -> Message:
    """A system reply in the thread of the message that prompted it."""
    return ws.post_message(db, channel=channel, body=body, kind="system",
                           parent_id=parent.id, notify=False)


# ── Slash commands ────────────────────────────────────────────────────────────

def handle_slash(
    db: Session,
    *,
    channel: Channel,
    body: str,
    current_user: User,
    org_ctx,
) -> dict | None:
    """
    Run a slash command. Returns a result dict, or None if this wasn't one.

    Commands post their own output as a `system` message so the answer stays in
    the channel for everyone — a private ephemeral reply is the right default
    in a general-purpose chat tool and the wrong one here, where "who approved
    that and when" is the question the product exists to answer.
    """
    text = (body or "").strip()
    if not text.startswith("/"):
        return None

    parts = text[1:].split(maxsplit=1)
    cmd = parts[0].lower()
    rest = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "help":
        _system(db, channel, SLASH_HELP)
        return {"command": "help"}

    if cmd == "catchup":
        member = ws.is_member(db, channel.id, current_user.id)
        result = ws.summarize_channel(db, channel, since=member.last_read_at if member else None)
        _system(db, channel, f"**Catch-up** ({result['message_count']} messages)\n\n{result['summary']}")
        return {"command": "catchup", **result}

    if cmd == "status":
        return _cmd_status(db, channel, rest)

    if cmd == "run":
        return _cmd_run(db, channel, rest, current_user, org_ctx)

    if cmd in ("approve", "reject"):
        return _cmd_decision(db, channel, cmd, rest, current_user, org_ctx)

    if cmd == "invite":
        return _cmd_invite(db, channel, rest, org_ctx)

    _system(db, channel, f"Unknown command `/{cmd}`. Try `/help`.")
    return {"command": cmd, "error": "unknown"}


def _system(db: Session, channel: Channel, body: str, payload: dict | None = None) -> Message:
    return ws.post_message(db, channel=channel, body=body, kind="system",
                           payload=payload or {}, notify=False)


def _cmd_status(db: Session, channel: Channel, rest: str) -> dict:
    if not channel.project_id:
        _system(db, channel, "This channel isn't attached to a project, so there's no run history here.")
        return {"command": "status", "runs": []}

    q = db.query(Run).filter(Run.project_id == channel.project_id)
    project = db.query(Project).filter(Project.id == channel.project_id).first()
    if rest and project:
        ticket = resolve_ticket(db, project, rest)
        if ticket:
            q = q.filter(Run.ticket_id == ticket.id)

    runs = q.order_by(Run.created_at.desc()).limit(5).all()
    if not runs:
        _system(db, channel, "No runs yet in this project.")
        return {"command": "status", "runs": []}

    lines = []
    for r in runs:
        ticket = db.query(Ticket).filter(Ticket.id == r.ticket_id).first() if r.ticket_id else None
        key = ticket.jira_id if ticket and ticket.jira_id else str(r.id)[:8]
        step = f" · {r.current_step}" if r.current_step else ""
        lines.append(f"- `{key}` **{r.status}**{step}" + (f" · [PR #{r.pr_number}]({r.pr_url})" if r.pr_url else ""))

    _system(db, channel, "**Recent runs**\n" + "\n".join(lines))
    return {"command": "status", "runs": [str(r.id) for r in runs]}


def _cmd_run(db: Session, channel: Channel, rest: str, current_user: User, org_ctx) -> dict:
    """`/run TICKET-KEY` — the explicit form of an @agent mention."""
    if not rest:
        _system(db, channel, "Usage: `/run PROJ-214`")
        return {"command": "run", "error": "missing_ticket"}

    placeholder = ws.post_message(db, channel=channel, body=f"/run {rest}",
                                  author=current_user, kind="user",
                                  org_ctx=org_ctx, notify=False)
    # Reuse the mention path so there is exactly one code path that starts a
    # run from chat. The "agent" is whichever dev agent the pod holds; the
    # dispatcher resolves it from the project's pod.
    agents = _project_agent_ids(db, channel)
    started = dispatch_agent_mention(
        db, channel=channel, message=placeholder, current_user=current_user,
        agent_ids=agents, org_ctx=org_ctx,
    )
    return {"command": "run", "started": started}


def _project_agent_ids(db: Session, channel: Channel) -> list[str]:
    if not channel.project_id:
        return []
    project = db.query(Project).filter(Project.id == channel.project_id).first()
    if not project or not project.pod_id:
        return []
    rows = (
        db.query(Agent.id)
        .join(PodAgent, PodAgent.agent_id == Agent.id)
        .filter(PodAgent.pod_id == project.pod_id)
        .order_by(PodAgent.execution_order)
        .all()
    )
    return [str(r[0]) for r in rows]


def _cmd_decision(db: Session, channel: Channel, cmd: str, rest: str,
                  current_user: User, org_ctx) -> dict:
    """
    `/approve <run-id> [comment]` — the same gate as the button, from chat.

    Deliberately delegates to the same `runs` router logic rather than writing
    an Approval row here. Two places that can approve a deploy is one place too
    many, and the router is where the policy gate, the audit entry and the
    resume-task dispatch already live.
    """
    if not rest:
        _system(db, channel, f"Usage: `/{cmd} <run-id> [comment]`")
        return {"command": cmd, "error": "missing_run"}

    parts = rest.split(maxsplit=1)
    try:
        run_id = uuid.UUID(parts[0])
    except ValueError:
        _system(db, channel, f"`{parts[0]}` isn't a run id. Copy it from the run card above.")
        return {"command": cmd, "error": "bad_run_id"}

    comment = parts[1] if len(parts) > 1 else None
    if cmd == "reject" and not comment:
        _system(db, channel, "A rejection needs a reason: `/reject <run-id> not enough test coverage`")
        return {"command": cmd, "error": "missing_reason"}

    from app.routers.runs import apply_run_decision
    try:
        result = apply_run_decision(
            db, run_id=run_id, decision="approve" if cmd == "approve" else "reject",
            comment=comment, current_user=current_user, org_ctx=org_ctx,
        )
    except Exception as e:
        _system(db, channel, f"Could not {cmd} that run: {e}")
        return {"command": cmd, "error": str(e)}

    who = current_user.name or current_user.email
    verb = "approved" if cmd == "approve" else "rejected"
    _system(db, channel, f"**{who} {verb}** run `{str(run_id)[:8]}`" + (f" — {comment}" if comment else ""),
            payload={"run_id": str(run_id), "decision": cmd, "event": f"run:{verb}"})
    return {"command": cmd, "run_id": str(run_id), "result": result}


def _cmd_invite(db: Session, channel: Channel, rest: str, org_ctx) -> dict:
    """`/invite @someone` — humans and agents, same command."""
    if not rest:
        _system(db, channel, "Usage: `/invite @priya` or `/invite @qa`")
        return {"command": "invite", "error": "missing_target"}

    mentions = ws.parse_mentions(db, rest, channel, org_ctx)
    added = []
    for uid in mentions.get("users") or []:
        ws.ensure_member(db, channel, user_id=uuid.UUID(uid))
        u = db.query(User).filter(User.id == uuid.UUID(uid)).first()
        added.append(u.name or u.email if u else uid)
    for aid in mentions.get("agents") or []:
        ws.ensure_member(db, channel, agent_id=uuid.UUID(aid))
        a = db.query(Agent).filter(Agent.id == uuid.UUID(aid)).first()
        added.append(f"{a.name} (agent)" if a else aid)

    if not added:
        _system(db, channel, f"Couldn't find anyone matching `{rest}` in this workspace.")
        return {"command": "invite", "added": []}

    _system(db, channel, f"Added {', '.join(added)} to this channel.")
    return {"command": "invite", "added": added}
