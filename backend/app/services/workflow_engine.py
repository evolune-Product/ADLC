"""
Generic workflow engine — walks a Workflow.definition node graph.

Deliberately a linear/branching walk, not a general DAG scheduler: `next` on
a node is either a single node id, a one-item list (kept as a shape a future
fan-out could extend without a schema change, but only ever [0] is followed
today), or a branch spec for "condition" nodes. No parallel joins.

Two-task pattern, same shape as `app/tasks/run_tasks.py`
----------------------------------------------------------
`human_task` and `approval` nodes never block a worker waiting for a person.
`advance()` creates a linked `Work` row, marks the step "waiting", sets the
execution's status, and returns — exactly like `trigger_run_until_approval`
stopping at `awaiting_approval`. Something external (here: `Work`'s own
status-update endpoint, when the linked Work reaches "completed") calls
`resume_execution()`, the counterpart to `resume_after_approval`.

Approval integration — what's real vs stubbed
-----------------------------------------------
`ApprovalPolicy` (app/models/governance.py) is deploy-gate-specific — scoped
to a Run's environment, not a general-purpose approval primitive a workflow
node can point at. Rather than fake integration with it, the `approval` node
reuses Work's own status machine as the real approval record: it creates a
`Work(type="workflow_approval", status="new")` row, and any user with
`can_write` in this org can act on it through the *existing*, already-tested
`PUT /work/{id}/status` endpoint — moving it to "completed" (approved) or
"failed" (rejected) resumes or fails the execution. This is a real, working
approval record acted on through a real API, not a duplicate approval system
— but it does not yet carry `ApprovalPolicy`'s richer rules (min_approvers,
approver_roles, review-score gating). That richer integration is future work.

api_call nodes
---------------
Real as of Company OS step 12: `_run_api_call` calls
`company_api_service.call_endpoint`, which loads the org-scoped `CompanyApi`
+ `CompanyApiEndpoint` the node's config points at, checks the ToolGrant
allow-list, SSRF-guards and normalizes the resolved URL, decrypts auth
just-in-time, and makes the real bounded-timeout/bounded-retry httpx call.
Node config shape: `{"company_api_id": "...", "endpoint_id": "...",
"body": {...}, "path_params": {...}}` — `body`/`path_params` may also be
`{{context.path}}` templates, rendered the same way `agent_task`'s
`prompt_template` is. A `CompanyApiError` (not found, disabled, unauthorized,
SSRF-refused, unreachable) fails the execution loudly via the normal
exception path below — never silently no-ops.

webhook nodes
--------------
Recognized and stored, but deliberately NOT implemented — see module-level
NotImplementedError below. A webhook call is an *inbound* delivery mechanism
(the workflow needs to receive one, not send one) and needs its own signing/
retry/delivery-log design (`WebhookDelivery` exists for the *outbound*
governance-event webhooks in `governance.py`, a different shape); reusing
that half-fits and was deliberately not forced here. Reaching this node type
fails the execution loudly with a clear message rather than silently
no-opping or faking a call.

sub_workflow nodes
--------------------
Also stubbed with the same clear, loud boundary — nesting workflow
executions is real design work (recursion limits, shared context scoping)
not attempted this session.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agents._common import workspace_credential
from app.models.agent import Agent
from app.models.work import Work
from app.models.workflow import Workflow, WorkflowExecution, WorkflowExecutionStep
from app.services import company_api_service, llm_service, metering_service, notifier

SYNC_NODE_TYPES = (
    "trigger", "completion", "transform", "notification", "condition",
    "agent_task", "delay", "api_call",
)
WAITING_NODE_TYPES = ("human_task", "approval")
UNIMPLEMENTED_NODE_TYPES = ("webhook", "sub_workflow")


def _now():
    return datetime.now(timezone.utc)


def _nodes_by_id(workflow: Workflow) -> dict[str, dict]:
    return {n["id"]: n for n in (workflow.definition or {}).get("nodes", [])}


def _get_path(context: dict, path: str | None) -> Any:
    if not path:
        return None
    value: Any = context
    for key in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _resolve_next(node: dict, context: dict) -> str | None:
    nxt = node.get("next")
    if nxt is None:
        return None
    if isinstance(nxt, str):
        return nxt
    if isinstance(nxt, list):
        return nxt[0] if nxt else None
    if isinstance(nxt, dict):
        value = _get_path(context, nxt.get("field"))
        branches = nxt.get("branches") or {}
        key = str(value) if value is not None else None
        if key is not None and key in branches:
            return branches[key]
        return nxt.get("default")
    return None


def _render_template(template: str, context: dict) -> str:
    """{{a.b}} -> str(context path a.b or ''). No eval, no arbitrary code."""
    def repl(match: "re.Match[str]") -> str:
        value = _get_path(context, match.group(1).strip())
        return "" if value is None else str(value)
    return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", repl, template or "")


def _create_linked_work(db: Session, workflow: Workflow, execution: WorkflowExecution, node: dict, kind: str) -> Work:
    cfg = node.get("config") or {}
    work = Work(
        organization_id=workflow.organization_id,
        department_id=workflow.department_id,
        requester_user_id=workflow.created_by,
        type=f"workflow_{kind}",
        title=cfg.get("title") or f"Workflow {kind}: {workflow.name}",
        description=cfg.get("description"),
        status="new",
        workflow_id=str(execution.id),
    )
    db.add(work)
    db.commit()
    db.refresh(work)
    return work


def _run_agent_task(db: Session, workflow: Workflow, execution: WorkflowExecution, node: dict) -> dict:
    cfg = node.get("config") or {}
    agent_id = cfg.get("agent_id")
    if not agent_id:
        raise ValueError("agent_task node config is missing 'agent_id'")
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.org_id == workflow.organization_id).first()
    if not agent:
        raise ValueError(f"agent_id {agent_id} does not belong to this organization")

    prompt = _render_template(cfg.get("prompt_template", ""), execution.context)
    system = cfg.get("system") or f"You are {agent.name}, a {agent.role} agent, taking part in an automated workflow."

    user_id = workflow.created_by
    cred = workspace_credential(db, user_id, workflow.organization_id, agent.llm_model)
    result = llm_service.complete(
        system=system, user=prompt, model=agent.llm_model,
        byo_provider=cred.provider, byo_key=cred.api_key,
        byo_base_url=cred.base_url, price_overrides=cred.price_overrides,
    )
    # Same metering path as every other model call in this platform (see
    # sprint_planner_service.plan_sprint for the precedent of an LLM call
    # with no Run behind it — run_id=None, billable keyed off is_byo).
    metering_service.record_llm_call(
        db, user_id=user_id, org_id=workflow.organization_id, run_id=None,
        agent_role=agent.role, model=result.model, provider=result.provider,
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        cost_millicents=result.cost_millicents, billable=not cred.is_byo,
    )
    return {"agent_id": str(agent.id), "output_text": result.text, "model": result.model}


def _render_deep(value: Any, context: dict) -> Any:
    """Apply `_render_template` to every string leaf of a dict/list, so an
    api_call node's `body`/`path_params` can reference `{{context.path}}`
    the same way `agent_task`'s `prompt_template` does."""
    if isinstance(value, str):
        return _render_template(value, context)
    if isinstance(value, dict):
        return {k: _render_deep(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_render_deep(v, context) for v in value]
    return value


def _run_api_call(db: Session, workflow: Workflow, execution: WorkflowExecution, node: dict) -> dict:
    cfg = node.get("config") or {}
    company_api_id = cfg.get("company_api_id")
    endpoint_id = cfg.get("endpoint_id")
    if not company_api_id or not endpoint_id:
        raise ValueError("api_call node config requires 'company_api_id' and 'endpoint_id'")

    body = _render_deep(cfg.get("body"), execution.context) if cfg.get("body") is not None else None
    path_params = _render_deep(cfg.get("path_params"), execution.context) if cfg.get("path_params") is not None else None

    result = company_api_service.call_endpoint(
        db, company_api_id, endpoint_id, workflow.organization_id,
        body=body, path_params=path_params,
        workflow_id=workflow.id,
    )
    return result


def start_execution(db: Session, workflow: Workflow, work: Work | None = None,
                     initial_context: dict | None = None) -> WorkflowExecution:
    definition = workflow.definition or {}
    start_id = definition.get("start_node_id")
    execution = WorkflowExecution(
        workflow_id=workflow.id,
        organization_id=workflow.organization_id,
        work_id=work.id if work else None,
        status="pending",
        current_node_id=start_id,
        context=initial_context or {},
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    if start_id is None:
        execution.status = "failed"
        execution.error = "Workflow definition has no start_node_id"
        execution.completed_at = _now()
        db.commit()
        return execution
    return advance(db, execution)


def advance(db: Session, execution: WorkflowExecution) -> WorkflowExecution:
    """Process the current node, and every synchronous node after it, until
    the execution finishes, fails, or reaches a waiting node."""
    workflow = db.query(Workflow).filter(Workflow.id == execution.workflow_id).first()
    if not workflow:
        execution.status = "failed"
        execution.error = "Parent workflow no longer exists"
        execution.completed_at = _now()
        db.commit()
        return execution

    nodes = _nodes_by_id(workflow)
    execution.status = "running"
    db.commit()

    while execution.current_node_id:
        node = nodes.get(execution.current_node_id)
        if node is None:
            return _fail(db, execution, f"Unknown node id '{execution.current_node_id}' in workflow definition")

        node_type = node.get("type")
        step = WorkflowExecutionStep(
            execution_id=execution.id, node_id=node["id"], node_type=node_type,
            status="running", input=node.get("config") or {},
        )
        db.add(step)
        db.commit()
        db.refresh(step)

        try:
            if node_type in UNIMPLEMENTED_NODE_TYPES:
                raise NotImplementedError(
                    "'webhook' nodes (inbound delivery) are not implemented this session — "
                    "see the module docstring"
                    if node_type == "webhook" else
                    "'sub_workflow' nodes are not implemented this session"
                )

            if node_type in WAITING_NODE_TYPES:
                kind = "approval" if node_type == "approval" else "human_task"
                work_row = _create_linked_work(db, workflow, execution, node, kind)
                step.status = "waiting"
                step.output = {"work_id": str(work_row.id)}
                db.commit()
                execution.current_node_id = node["id"]
                execution.status = "awaiting_approval" if node_type == "approval" else "running"
                db.commit()
                return execution

            if node_type == "trigger":
                pass
            elif node_type == "transform":
                merge = (node.get("config") or {}).get("merge") or {}
                execution.context = {**execution.context, **merge}
            elif node_type == "notification":
                cfg = node.get("config") or {}
                target_user = cfg.get("user_id") or workflow.created_by
                notifier.notify_user(
                    db, user_id=target_user, org_id=workflow.organization_id,
                    type=cfg.get("type", "workflow.notification"),
                    title=cfg.get("title", f"Workflow: {workflow.name}"),
                    body=cfg.get("body"), link=cfg.get("link"),
                    payload={"execution_id": str(execution.id), "node_id": node["id"]},
                )
            elif node_type == "condition":
                pass  # next resolved below via _resolve_next(context)
            elif node_type == "agent_task":
                output = _run_agent_task(db, workflow, execution, node)
                execution.context = {**execution.context, node["id"]: output}
                step.output = output
            elif node_type == "api_call":
                try:
                    output = _run_api_call(db, workflow, execution, node)
                except company_api_service.CompanyApiError as exc:
                    # Surfaced through the same failure path as any other
                    # node exception — loud, not a silent no-op.
                    raise RuntimeError(f"api_call node '{node['id']}' failed: {exc}") from exc
                execution.context = {**execution.context, node["id"]: output}
                step.output = output
            elif node_type == "delay":
                # No scheduler this session — a documented no-op pass-through,
                # not a fake wait.
                step.output = {"note": "delay is a no-op boundary this session; no scheduler wired up yet"}
            elif node_type == "completion":
                step.status = "completed"
                step.completed_at = _now()
                db.commit()
                execution.status = "completed"
                execution.current_node_id = None
                execution.completed_at = _now()
                db.commit()
                return execution
            else:
                raise NotImplementedError(f"Unknown node type '{node_type}'")

            if step.output is None:
                step.output = dict(execution.context) if node_type == "transform" else {}
            step.status = "completed"
            step.completed_at = _now()
            db.commit()

            next_id = _resolve_next(node, execution.context)
            if node_type == "condition" and next_id is None:
                return _fail(db, execution, f"condition node '{node['id']}' matched no branch and has no default")

        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            step.completed_at = _now()
            db.commit()
            return _fail(db, execution, str(exc))

        execution.current_node_id = next_id
        db.commit()

    # Ran off the end of the graph with no explicit completion node.
    execution.status = "completed"
    execution.completed_at = _now()
    db.commit()
    return execution


def _fail(db: Session, execution: WorkflowExecution, message: str) -> WorkflowExecution:
    execution.status = "failed"
    execution.error = message
    execution.completed_at = _now()
    db.commit()
    return execution


def resume_execution(db: Session, execution: WorkflowExecution) -> WorkflowExecution:
    """Move past the current waiting node (human_task/approval) and continue.

    Called once the Work item that node created has reached a terminal
    state. The caller (Work's status-update endpoint) decides whether that
    means success or rejection before calling this — see
    `backend/app/routers/work.py`.
    """
    if execution.status not in ("running", "awaiting_approval"):
        return execution

    workflow = db.query(Workflow).filter(Workflow.id == execution.workflow_id).first()
    if not workflow:
        return _fail(db, execution, "Parent workflow no longer exists")

    nodes = _nodes_by_id(workflow)
    node = nodes.get(execution.current_node_id)
    if node is None:
        return _fail(db, execution, f"Unknown node id '{execution.current_node_id}' on resume")

    next_id = _resolve_next(node, execution.context)
    execution.status = "running"
    execution.current_node_id = next_id
    db.commit()

    if next_id is None:
        execution.status = "completed"
        execution.completed_at = _now()
        db.commit()
        return execution

    return advance(db, execution)


def fail_execution(db: Session, execution: WorkflowExecution, reason: str) -> WorkflowExecution:
    """Called when the Work behind a waiting node was rejected/failed rather
    than completed — e.g. an approval denied."""
    return _fail(db, execution, reason)
