"""
Celery tasks for running the SDLC agent pipeline.

Two tasks implement the approval-gate pattern:
  task_run_until_approval  — sprint → dev → qa → review  (stops at awaiting_approval)
  task_resume_after_approval — policy gate → merge → multi-env deploy

Phase 11 additions: plan quota enforcement before work starts, per-run budget
caps, the Reviewer agent, policy evaluation at the deploy gate, deployment
records, notification fan-out, and memory write-back on success.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from celery_app import celery_app
from app.database import SessionLocal
from app.models.run import Run, RunStep
from app.models.project import Project
from app.models.ticket import Ticket
from app.models.pod import PodAgent
from app.models.agent import Agent
from app.models.insight import Deployment
from app.agents.orchestrator import SDLCState, initial_state
from app.agents.sprint_agent import run_sprint_agent
from app.agents.dev_agent import run_dev_agent
from app.agents.qa_agent import run_qa_agent
from app.agents.review_agent import run_review_agent
from app.agents.devops_agent import run_devops_agent
from app.services import memory_service, metering_service, notifier, policy_service
from app.services.notification_service import emit_run_event

log = logging.getLogger(__name__)


def _owner(db, run: Run) -> tuple:
    """(user_id, org_id, project) — the billing and notification target for a run."""
    project = db.query(Project).filter(Project.id == run.project_id).first()
    if not project:
        return run.triggered_by, None, None
    return project.user_id, project.org_id, project


def _load_state_from_db(run_id: str, db) -> SDLCState | None:
    """Load everything needed to build the initial SDLCState from the DB."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        return None

    project = db.query(Project).filter(Project.id == run.project_id).first()
    if not project:
        return None

    ticket = db.query(Ticket).filter(Ticket.id == run.ticket_id).first() if run.ticket_id else None

    pod_agents_records = (
        db.query(PodAgent)
        .filter(PodAgent.pod_id == run.pod_id)
        .order_by(PodAgent.execution_order)
        .all()
    )
    agent_ids = [str(pa.agent_id) for pa in pod_agents_records]
    agents = {
        str(a.id): a
        for a in db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
    }

    pod_agents_data = [
        {
            "agent_id": str(pa.agent_id),
            "agent_role": agents[str(pa.agent_id)].role if str(pa.agent_id) in agents else "custom",
            "execution_order": pa.execution_order,
            "max_retries": pa.max_retries,
        }
        for pa in pod_agents_records
        if str(pa.agent_id) in agents
    ]

    project_dict = {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "type": project.type,
        "repo_connection_id": str(project.repo_connection_id) if project.repo_connection_id else None,
        "repo_name": project.repo_name,
        "jira_connection_id": str(project.jira_connection_id) if project.jira_connection_id else None,
        "jira_project_key": project.jira_project_key,
        "pod_id": str(project.pod_id) if project.pod_id else None,
        "context_md": project.context_md,
        "deploy_targets": project.deploy_targets or [],
        "org_id": str(project.org_id) if project.org_id else None,
        "user_id": str(project.user_id),
    }

    ticket_dict = {}
    if ticket:
        ticket_dict = {
            "id": str(ticket.id),
            "jira_id": ticket.jira_id,
            "title": ticket.title,
            "description": ticket.description,
            "type": ticket.type,
            "priority": ticket.priority,
            "status": ticket.status,
        }

    max_retries = max((pa.get("max_retries", 2) for pa in pod_agents_data), default=2)

    return initial_state(
        run_id=run_id,
        project=project_dict,
        ticket=ticket_dict,
        pod_agents=pod_agents_data,
        max_dev_retries=max_retries,
    )


@celery_app.task(name="run_tasks.trigger_run_until_approval", bind=True, max_retries=0)
def trigger_run_until_approval(self, run_id: str):
    """Run sprint → dev → qa → review. Stops at awaiting_approval or fails."""
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            log.error("Run %s not found", run_id)
            return
        if run.status not in ("queued", "running"):
            return  # Already processed

        user_id, org_id, _project = _owner(db, run)

        # ── Plan quota: the metered half of the business model ────────────────
        quota = metering_service.check_quota(db, user_id, org_id)
        if not quota.allowed:
            _fail_run(run, quota.reason or "Plan limit reached", db)
            notifier.notify_org(
                db, org_id=org_id, fallback_user_id=user_id, type="quota.exceeded",
                title="Run blocked — plan limit reached",
                body=quota.reason, link="/billing", payload=quota.as_dict(),
            )
            return
        metering_service.record_run(db, user_id=user_id, org_id=org_id, run_id=run.id)

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        db.commit()

        emit_run_event(run_id, "run:started", {"runId": run_id})

        state = _load_state_from_db(run_id, db)
        if not state:
            _fail_run(run, "Could not load run data from DB", db)
            return

        budget_cents = metering_service.get_or_create_subscription(db, user_id, org_id).run_budget_cents

        # ── Sprint ──
        state = run_sprint_agent(state, db)
        if state["status"] == "failed":
            _fail_and_notify(db, run_id, state, "Sprint failed")
            return

        # ── Dev (with QA retry loop) ──
        while True:
            state = run_dev_agent(state, db)
            if state["status"] == "failed":
                _fail_and_notify(db, run_id, state, "Dev failed")
                return

            if metering_service.run_over_budget(db, run_id, budget_cents):
                _fail_and_notify(db, run_id, state,
                                 f"Run exceeded the per-run budget of ${budget_cents / 100:.2f}")
                return

            state = run_qa_agent(state, db)
            if state["status"] == "failed":
                _fail_and_notify(db, run_id, state, "QA failed (max retries)")
                return

            if state.get("current_agent") == "approval":
                break   # QA passed

        # ── Review (optional agent; never fails the run on its own) ──
        state = run_review_agent(state, db)

        # ── Awaiting human approval ──
        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.status = "awaiting_approval"
            run.current_step = None
            run.branch_name = state.get("branch_name")
            run.pr_url = state.get("pr_url")
            run.pr_number = state.get("pr_number")
            db.commit()

        emit_run_event(run_id, "run:awaiting_approval", {
            "runId": run_id,
            "prUrl": state.get("pr_url"),
            "prNumber": state.get("pr_number"),
            "reviewScore": state.get("review_score"),
        })

        score = state.get("review_score")
        score_line = f"Reviewer score: {score}/100. " if score is not None else ""
        notifier.notify_org(
            db, org_id=org_id, fallback_user_id=user_id, type="run.awaiting_approval",
            title=f"Approval needed — {(state.get('ticket') or {}).get('title') or 'agent run'}",
            body=(f"{score_line}A pull request is ready for your decision before it can deploy.\n"
                  f"{state.get('pr_url') or ''}"),
            link=f"/runs/{run_id}",
            payload={"run_id": run_id, "pr_url": state.get("pr_url"), "review_score": score},
        )

    except Exception as exc:
        log.exception("Unhandled error in trigger_run_until_approval for %s", run_id)
        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            _fail_run(run, str(exc), db)
        emit_run_event(run_id, "run:failed", {"runId": run_id, "error": str(exc)})
    finally:
        db.close()


@celery_app.task(name="run_tasks.resume_after_approval", bind=True, max_retries=0)
def resume_after_approval(self, run_id: str, decision: str, comment: str | None = None):
    """Resume after human approval: policy gate → PR merge → multi-env deploy loop."""
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            return

        user_id, org_id, project_row = _owner(db, run)

        if decision != "approved":
            run.status = "failed"
            run.error_message = f"Changes requested: {comment or 'No comment'}"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            emit_run_event(run_id, "run:failed", {"runId": run_id, "error": run.error_message})
            notifier.notify_org(
                db, org_id=org_id, fallback_user_id=user_id, type="run.failed",
                title="Changes requested on agent run",
                body=comment or "A reviewer requested changes.", link=f"/runs/{run_id}",
            )
            return

        state = _load_state_from_db(run_id, db)
        if not state:
            _fail_run(run, "Could not reload state from DB", db)
            return

        deploy_targets = state["project"].get("deploy_targets", [])
        current_env_index = run.current_env_index if run.current_env_index is not None else -1
        env_name = (deploy_targets[current_env_index]["env"]
                    if 0 <= current_env_index < len(deploy_targets) else "*")

        # ── Governance gate: does this run satisfy the policy for this env? ───
        policy = policy_service.resolve_policy(
            db, org_id=org_id,
            project_id=project_row.id if project_row else None,
            environment=env_name,
        )
        gate = policy_service.evaluate_deploy(db, run_id=run_id, policy=policy)
        if not gate.allowed:
            reason = "; ".join(gate.reasons)
            run.status = "awaiting_approval"     # stay at the gate, do not fail
            run.error_message = None
            db.commit()
            emit_run_event(run_id, "run:policy:blocked", {"runId": run_id, **gate.as_dict()})
            notifier.notify_org(
                db, org_id=org_id, fallback_user_id=user_id, type="policy.blocked",
                title=f"Deploy blocked by policy '{gate.policy_name}'",
                body=reason, link=f"/runs/{run_id}", payload=gate.as_dict(),
            )
            return

        run.status = "running"
        db.commit()
        emit_run_event(run_id, "run:approved", {"runId": run_id, "decision": "approved"})

        state = {
            **state,
            "branch_name": run.branch_name,
            "pr_url": run.pr_url,
            "pr_number": run.pr_number,
        }

        if current_env_index == -1:
            # ── Step 1: Merge the feature PR ──────────────────────────────
            state = run_devops_agent({**state, "env_index": -1}, db)
            if state["status"] == "failed":
                _fail_and_notify(db, run_id, state, "PR merge failed")
                return

            if not deploy_targets:
                _complete_run(run_id, db, gate)
                return

            # ── Step 2: Deploy to env[0] (PR approval covers the first env) ──
            state = run_devops_agent({**state, "env_index": 0}, db)
            if state["status"] == "failed":
                _fail_and_notify(db, run_id, state, "Deploy to env[0] failed")
                return
            _record_deployment(db, run_id, deploy_targets[0], gate)

            if len(deploy_targets) == 1:
                _complete_run(run_id, db, gate)
            else:
                _await_env_approval(run_id, deploy_targets, next_index=1, db=db,
                                    org_id=org_id, user_id=user_id)

        else:
            # ── Deploy to deploy_targets[current_env_index] ───────────────
            state = run_devops_agent({**state, "env_index": current_env_index}, db)
            if state["status"] == "failed":
                _fail_and_notify(db, run_id, state, "Deploy failed")
                return
            _record_deployment(db, run_id, deploy_targets[current_env_index], gate)

            if current_env_index >= len(deploy_targets) - 1:
                _complete_run(run_id, db, gate)
            else:
                _await_env_approval(run_id, deploy_targets, next_index=current_env_index + 1,
                                    db=db, org_id=org_id, user_id=user_id)

    except Exception as exc:
        log.exception("Unhandled error in resume_after_approval for %s", run_id)
        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            _fail_run(run, str(exc), db)
    finally:
        db.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _record_deployment(db, run_id: str, target: dict, gate=None) -> None:
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        return
    db.add(Deployment(
        run_id=run.id,
        project_id=run.project_id,
        environment=target.get("env", "unknown"),
        branch=target.get("branch"),
        status="succeeded",
        approver_count=gate.approvals_have if gate else 0,
        policy_id=gate.policy_id if gate else None,
        message=f"Promoted to {target.get('env')} via {target.get('branch')}",
        metadata_={"policy": gate.policy_name if gate else None,
                   "review_score": gate.review_score if gate else None},
    ))
    db.commit()


def _complete_run(run_id: str, db, gate=None) -> None:
    run = db.query(Run).filter(Run.id == run_id).first()
    if run:
        run.status = "completed"
        run.current_step = None
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
    emit_run_event(run_id, "run:completed", {"runId": run_id, "status": "completed"})

    if not run:
        return

    user_id, org_id, _project = _owner(db, run)
    spend = metering_service.run_spend_millicents(db, run.id) / 100_000

    notifier.notify_org(
        db, org_id=org_id, fallback_user_id=user_id, type="run.completed",
        title="Agent run completed and deployed",
        body=f"{run.branch_name or 'Change'} shipped. Cost ${spend:.3f}.",
        link=f"/runs/{run_id}",
        payload={"run_id": run_id, "pr_url": run.pr_url, "spend_usd": round(spend, 4)},
    )

    # Write-back: the platform gets better at *this* codebase every merged run.
    try:
        ticket = db.query(Ticket).filter(Ticket.id == run.ticket_id).first() if run.ticket_id else None
        lines = [
            f"Ticket: {ticket.jira_id + ' — ' + ticket.title if ticket else 'ad-hoc run'}",
            f"Branch: {run.branch_name}",
            f"PR: {run.pr_url}",
        ]
        for s in db.query(RunStep).filter(RunStep.run_id == run.id).all():
            if s.agent_role == "dev" and isinstance(s.output, dict):
                lines.append(f"{s.output.get('files_changed', 0)} file(s) changed")
        memory_service.remember_outcome(
            db, run.project_id, run_id=run.id,
            title=f"Approved change: {ticket.title if ticket else run.branch_name}",
            content="\n".join(x for x in lines if x),
            kind="decision",
        )
    except Exception:
        log.exception("Memory write-back failed for run %s", run_id)


def _await_env_approval(run_id: str, deploy_targets: list, next_index: int, db,
                        org_id=None, user_id=None) -> None:
    run = db.query(Run).filter(Run.id == run_id).first()
    if run:
        run.status = "awaiting_approval"
        run.current_env_index = next_index
        run.current_step = None
        db.commit()
    next_env = deploy_targets[next_index]
    emit_run_event(run_id, "run:awaiting_env_approval", {
        "runId": run_id,
        "envIndex": next_index,
        "env": next_env["env"],
        "branch": next_env["branch"],
        "totalEnvs": len(deploy_targets),
    })
    if user_id:
        notifier.notify_org(
            db, org_id=org_id, fallback_user_id=user_id, type="run.awaiting_approval",
            title=f"Approval needed to promote to {next_env['env']}",
            body=f"Deploy {next_env['branch']} to {next_env['env']}?",
            link=f"/runs/{run_id}",
            payload={"run_id": run_id, "env": next_env["env"]},
        )


def _fail_and_notify(db, run_id: str, state: dict, fallback: str) -> None:
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        return
    error = state["errors"][-1] if state.get("errors") else fallback
    _fail_run(run, error, db)
    user_id, org_id, _project = _owner(db, run)
    notifier.notify_org(
        db, org_id=org_id, fallback_user_id=user_id, type="run.failed",
        title="Agent run failed", body=error, link=f"/runs/{run_id}",
        payload={"run_id": run_id, "error": error},
    )


def _fail_run(run: Run, error: str, db) -> None:
    run.status = "failed"
    run.error_message = error
    run.current_step = None
    run.completed_at = datetime.now(timezone.utc)
    db.commit()
    emit_run_event(str(run.id), "run:failed", {"runId": str(run.id), "error": error})
