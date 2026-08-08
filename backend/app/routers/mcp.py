"""
MCP server — ADLC as a set of tools any agent can call.

WHY
By 2026 the Model Context Protocol is how agents reach anything: Claude Code,
Cursor, Continue and every major framework speak it. A governance platform that
can only be driven through its own web UI is a governance platform that gets
routed around the moment a developer is working inside an agent instead.

WHAT MAKES THIS DIFFERENT FROM A REST WRAPPER
The interesting tool here is `approve_run`, and the interesting thing about it
is that it is *deliberately hard to reach*. Every other platform exposing
itself over MCP gives an agent tools to do more work. This one gives an agent a
tool to find work that has stopped, and a separate, separately-scoped tool to
release it. An agent holding a `runs:write` key can start a run and cannot
approve it — the split exists so that "let the agent do it end to end" requires
someone to deliberately hand over a key that says `runs:approve`, rather than
happening by accident.

TRANSPORT
Streamable HTTP: one `POST /mcp` speaking JSON-RPC 2.0. No SSE stream, because
nothing here is long-running from the client's point of view — a run is started
and then polled, which is what `get_run` is for.

AUTH
The same `adlc_live_…` scoped API keys the REST API uses, as a bearer token.
There is no second credential system and no OAuth dance: an MCP client config
takes a header, and a key that already carries scopes is exactly the right
shape for this.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.governance import ApiKey
from app.models.project import Project
from app.models.run import Approval, Run
from app.routers.public_api import _run_out, _scoped_projects, get_api_key
from app.services import metering_service, reader_service

log = logging.getLogger(__name__)

router = APIRouter()

# The Streamable HTTP revision this server implements.
PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "adlc", "title": "ADLC — governed agent delivery", "version": "1.0.0"}

# JSON-RPC 2.0 error codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class ToolError(RuntimeError):
    """A tool failed in a way the *model* should see and can act on — a missing
    project, a run that is not at the gate. Returned as an MCP tool error, not
    a JSON-RPC protocol error, because the distinction is what lets an agent
    retry sensibly instead of giving up."""


# ── tool definitions ────────────────────────────────────────────────────────
#
# Descriptions are written for a model, not for a docs page: they say when to
# reach for the tool and what it will not do, because that is what stops an
# agent from calling `approve_run` on everything it can see.

TOOLS: list[dict] = [
    {
        "name": "list_projects",
        "description": "List the projects this API key can see, with their repository and pod.",
        "scope": "projects:read",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_runs",
        "description": (
            "List recent delivery runs. Filter by status to find work in a particular "
            "state: queued, running, awaiting_approval, completed, failed."
        ),
        "scope": "runs:read",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Optional status filter."},
                "limit": {"type": "integer", "description": "Default 20, maximum 100."},
            },
        },
    },
    {
        "name": "get_run",
        "description": (
            "Full detail for one run: status, current step, branch, pull request, "
            "the reviewer's findings, and any external sources the agents read while "
            "planning. Use this to answer 'what happened on this run'."
        ),
        "scope": "runs:read",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "start_run",
        "description": (
            "Start a delivery run for a project. The run plans, writes, tests and "
            "reviews the change, then STOPS at the approval gate. It will not deploy "
            "and cannot be made to deploy by this tool."
        ),
        "scope": "runs:write",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "ticket_id": {"type": "string", "description": "Optional ticket to run."},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "list_pending_approvals",
        "description": (
            "Every run currently stopped at the approval gate, with its pull request "
            "and reviewer score. This is the queue a human is expected to work "
            "through — use it to report what is waiting, not to clear it."
        ),
        "scope": "runs:read",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "approve_run",
        "description": (
            "Release a run from the approval gate, or send it back for changes. "
            "This authorises a deployment to production and is recorded in the audit "
            "log against the owner of this API key. Requires the separate "
            "'runs:approve' scope: a key that can start work deliberately cannot "
            "approve it. Do not call this on a human's behalf without being asked to."
        ),
        "scope": "runs:approve",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "decision": {"type": "string", "enum": ["approved", "changes_requested"]},
                "comment": {"type": "string"},
            },
            "required": ["run_id", "decision"],
        },
    },
    {
        "name": "read_url",
        "description": (
            "Fetch a web page and return it as clean Markdown instead of raw HTML, "
            "with a 0-100 score for how well it could be read. Use this before "
            "quoting any external page: it typically costs ~90% fewer tokens, and a "
            "low score means the page did not extract properly and its details "
            "should not be trusted."
        ),
        "scope": None,  # any valid key — this is a utility, not a data access
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
]

_BY_NAME = {t["name"]: t for t in TOOLS}


def _public_tools() -> list[dict]:
    """The manifest, without our internal `scope` bookkeeping."""
    return [{k: v for k, v in t.items() if k != "scope"} for t in TOOLS]


# ── tool implementations ────────────────────────────────────────────────────

def _tool_list_projects(db: Session, key: ApiKey, args: dict) -> Any:
    ids = _scoped_projects(db, key)
    rows = db.query(Project).filter(Project.id.in_(ids)).all() if ids else []
    return [
        {"id": str(p.id), "name": p.name, "repo": p.repo_name,
         "pod_id": str(p.pod_id) if p.pod_id else None, "status": p.status}
        for p in rows
    ]


def _tool_list_runs(db: Session, key: ApiKey, args: dict) -> Any:
    ids = _scoped_projects(db, key)
    if not ids:
        return []
    limit = min(int(args.get("limit") or 20), 100)
    q = db.query(Run).filter(Run.project_id.in_(ids))
    if args.get("status"):
        q = q.filter(Run.status == args["status"])
    return [_run_out(r) for r in q.order_by(Run.created_at.desc()).limit(limit).all()]


def _tool_get_run(db: Session, key: ApiKey, args: dict) -> Any:
    from app.models.insight import ReviewFinding, SourceRead

    run = _require_run(db, key, args.get("run_id"))
    findings = db.query(ReviewFinding).filter(ReviewFinding.run_id == run.id).all()
    sources = db.query(SourceRead).filter(SourceRead.run_id == run.id).all()

    from app.services.policy_service import review_score

    return {
        **_run_out(run),
        "review": {
            "score": review_score(findings) if findings else None,
            "findings": [
                {"severity": f.severity, "category": f.category, "file": f.file_path,
                 "line": f.line, "message": f.message}
                for f in findings
            ],
        },
        # Surfaced here for the same reason it is surfaced in the run trace: an
        # agent summarising a run should be able to say "the spec it planned
        # from did not read cleanly".
        "sources": [
            {"url": s.url, "status": s.status, "read_score": s.read_score,
             "risk": s.hallucination_risk}
            for s in sources
        ],
    }


def _tool_start_run(db: Session, key: ApiKey, args: dict) -> Any:
    project = db.query(Project).filter(Project.id == _as_uuid(args.get("project_id"))).first()
    if not project or project.id not in _scoped_projects(db, key):
        raise ToolError("No project with that id is visible to this API key.")

    pod_id = project.pod_id
    if not pod_id:
        raise ToolError(f"Project '{project.name}' has no pod configured, so there is nothing to run.")

    quota = metering_service.check_quota(db, project.user_id, project.org_id)
    if not quota.allowed:
        raise ToolError(quota.reason or "This workspace has reached its plan limit.")

    run = Run(project_id=project.id, ticket_id=_as_uuid(args.get("ticket_id")),
              pod_id=pod_id, status="queued", triggered_by=key.user_id)
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        from app.tasks.run_tasks import trigger_run_until_approval
        trigger_run_until_approval.delay(str(run.id))
    except Exception as exc:
        run.status = "failed"
        run.error_message = f"Failed to dispatch task: {exc}"
        db.commit()
        raise ToolError(f"The run was created but could not be dispatched: {exc}")

    return {**_run_out(run), "note": "Started. It will stop at the approval gate."}


def _tool_list_pending_approvals(db: Session, key: ApiKey, args: dict) -> Any:
    from app.models.insight import ReviewFinding
    from app.services.policy_service import review_score

    ids = _scoped_projects(db, key)
    if not ids:
        return []
    runs = (
        db.query(Run)
        .filter(Run.project_id.in_(ids), Run.status == "awaiting_approval")
        .order_by(Run.created_at.asc())
        .all()
    )
    out = []
    for run in runs:
        findings = db.query(ReviewFinding).filter(ReviewFinding.run_id == run.id).all()
        out.append({
            **_run_out(run),
            "review_score": review_score(findings) if findings else None,
            "blocking_findings": sum(1 for f in findings if f.severity in ("high", "critical")),
        })
    return out


def _tool_approve_run(db: Session, key: ApiKey, args: dict) -> Any:
    run = _require_run(db, key, args.get("run_id"))
    decision = args.get("decision")

    if decision not in ("approved", "changes_requested"):
        raise ToolError("decision must be 'approved' or 'changes_requested'.")
    if run.status != "awaiting_approval":
        raise ToolError(f"This run is not at the approval gate (status: {run.status}).")

    db.add(Approval(
        run_id=run.id, reviewer_id=key.user_id, decision=decision,
        # The audit log has to be able to say this came from a machine. An
        # approval that reads like a person's when it was an agent's is the one
        # thing that would make this whole trail worthless.
        comment=args.get("comment") or f"via MCP, API key {key.prefix}",
    ))
    db.commit()

    try:
        from app.tasks.run_tasks import resume_after_approval
        resume_after_approval.delay(str(run.id), decision, args.get("comment"))
    except Exception as exc:
        raise ToolError(f"The decision was recorded but the run could not be resumed: {exc}")

    db.refresh(run)
    return {**_run_out(run), "decision": decision, "recorded_against": key.prefix}


def _tool_read_url(db: Session, key: ApiKey, args: dict) -> Any:
    try:
        result = reader_service.read_url(str(args.get("url") or ""))
    except reader_service.ReadError as exc:
        raise ToolError(str(exc))

    payload = result.as_dict()
    # The Markdown itself, which the summary dict deliberately omits.
    payload["markdown"] = result.markdown[:40000]
    return payload


HANDLERS: dict[str, Callable[[Session, ApiKey, dict], Any]] = {
    "list_projects": _tool_list_projects,
    "list_runs": _tool_list_runs,
    "get_run": _tool_get_run,
    "start_run": _tool_start_run,
    "list_pending_approvals": _tool_list_pending_approvals,
    "approve_run": _tool_approve_run,
    "read_url": _tool_read_url,
}


def _as_uuid(value: Any) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError):
        raise ToolError(f"'{value}' is not a valid id.")


def _require_run(db: Session, key: ApiKey, run_id: Any) -> Run:
    run = db.query(Run).filter(Run.id == _as_uuid(run_id)).first()
    # Same 404-shaped answer whether it does not exist or belongs to someone
    # else. Distinguishing them tells a caller what other tenants have.
    if not run or run.project_id not in _scoped_projects(db, key):
        raise ToolError("No run with that id is visible to this API key.")
    return run


# ── JSON-RPC plumbing ───────────────────────────────────────────────────────

def _result(rpc_id: Any, payload: dict) -> dict:
    return {"jsonrpc": "2.0", "id": rpc_id, "result": payload}


def _error(rpc_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}


def _text_content(payload: Any) -> dict:
    import json
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2, default=str)}]}


@router.post("/mcp")
async def mcp_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    key: ApiKey = Depends(get_api_key),
    accept: str = Header(default="application/json"),
):
    """
    One endpoint, JSON-RPC 2.0 in and out.

    Point an MCP client at it with the API key as a bearer token:

        {"mcpServers": {"adlc": {
           "url": "https://your-adlc/mcp",
           "headers": {"Authorization": "Bearer adlc_live_…"}}}}
    """
    try:
        body = await request.json()
    except Exception:
        return _error(None, PARSE_ERROR, "Request body is not valid JSON")

    # Batches are legal JSON-RPC and clients do send them.
    if isinstance(body, list):
        responses = [r for r in (_dispatch(msg, db, key) for msg in body) if r is not None]
        return responses or {}

    response = _dispatch(body, db, key)
    # A notification (no id) gets no response body at all.
    return response if response is not None else {}


def _dispatch(message: Any, db: Session, key: ApiKey) -> dict | None:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(None, INVALID_REQUEST, "Expected a JSON-RPC 2.0 message")

    rpc_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    is_notification = "id" not in message

    if method == "initialize":
        return _result(rpc_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": (
                "ADLC runs governed software delivery: agents plan, write, test and "
                "review a change, then every run stops at a human approval gate. You "
                "can inspect runs and start them. Approving one authorises a "
                "production deploy and is written to an immutable audit log — only do "
                "it when a human has explicitly asked you to."
            ),
        })

    if method in ("notifications/initialized", "notifications/cancelled"):
        return None

    if method == "ping":
        return _result(rpc_id, {})

    if method == "tools/list":
        return _result(rpc_id, {"tools": _public_tools()})

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        spec = _BY_NAME.get(name)
        if not spec:
            return _error(rpc_id, METHOD_NOT_FOUND, f"No tool named '{name}'")

        scope = spec.get("scope")
        if scope and scope not in (key.scopes or []):
            # A scope failure is returned as a tool error rather than a
            # protocol error on purpose: the model should be able to read it,
            # tell the user which scope is missing, and stop — not retry.
            return _result(rpc_id, {
                **_text_content({
                    "error": f"This API key is missing the '{scope}' scope.",
                    "key": key.prefix,
                    "has_scopes": key.scopes or [],
                }),
                "isError": True,
            })

        try:
            payload = HANDLERS[name](db, key, args)
        except ToolError as exc:
            return _result(rpc_id, {**_text_content({"error": str(exc)}), "isError": True})
        except Exception:
            log.exception("MCP tool %s failed", name)
            return _result(rpc_id, {
                **_text_content({"error": "The tool failed unexpectedly."}), "isError": True,
            })

        return _result(rpc_id, _text_content(payload))

    if is_notification:
        return None
    return _error(rpc_id, METHOD_NOT_FOUND, f"Unknown method '{method}'")
