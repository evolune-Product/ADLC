"""
Celery tasks for running the SDLC agent pipeline.

Two tasks implement the approval-gate pattern:
  task_run_until_approval  — sprint → dev → qa  (stops at awaiting_approval)
  task_resume_after_approval — devops  (triggered after human approves)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from celery_app import celery_app
from app.database import SessionLocal
from app.models.run import Run, RunStep
from app.models.project import Project
from app.models.ticket import Ticket
from app.models.pod import Pod, PodAgent
from app.models.agent import Agent
from app.agents.orchestrator import SDLCState, initial_state
from app.agents.sprint_agent import run_sprint_agent
from app.agents.dev_agent import run_dev_agent
from app.agents.qa_agent import run_qa_agent
from app.agents.devops_agent import run_devops_agent
from app.services.notification_service import emit_run_event

log = logging.getLogger(__name__)


def _load_state_from_db(run_id: str, db) -> SDLCState | None:
    """Load everything needed to build the initial SDLCState from the DB."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        return None

    project = db.query(Project).filter(Project.id == run.project_id).first()
    if not project:
        return None

    ticket = db.query(Ticket).filter(Ticket.id == run.ticket_id).first() if run.ticket_id else None

    # Load pod agents (ordered)
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
    """Run sprint → dev → qa. Stops at awaiting_approval or fails."""
    db = SessionLocal()
    try:
        # Mark run as started
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            log.error("Run %s not found", run_id)
            return
        if run.status not in ("queued", "running"):
            return  # Already processed

        run.status     = "running"
        run.started_at = datetime.now(timezone.utc)
        db.commit()

        emit_run_event(run_id, "run:started", {"runId": run_id})

        state = _load_state_from_db(run_id, db)
        if not state:
            _fail_run(run, "Could not load run data from DB", db)
            return

        # ── Sprint ──
        state = run_sprint_agent(state, db)
        if state["status"] == "failed":
            _fail_run(run, state["errors"][-1] if state["errors"] else "Sprint failed", db)
            return

        # ── Dev (with retry loop) ──
        while True:
            state = run_dev_agent(state, db)
            if state["status"] == "failed":
                _fail_run(run, state["errors"][-1] if state["errors"] else "Dev failed", db)
                return

            # ── QA ──
            state = run_qa_agent(state, db)
            if state["status"] == "failed":
                _fail_run(run, state["errors"][-1] if state["errors"] else "QA failed (max retries)", db)
                return

            # QA decision
            if state.get("current_agent") == "approval":
                break   # QA passed
            # else: QA failed, retry dev — loop continues

        # ── Awaiting approval ──
        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.status       = "awaiting_approval"
            run.current_step = None
            run.branch_name  = state.get("branch_name")
            run.pr_url       = state.get("pr_url")
            run.pr_number    = state.get("pr_number")
            db.commit()

        emit_run_event(run_id, "run:awaiting_approval", {
            "runId": run_id,
            "prUrl": state.get("pr_url"),
            "prNumber": state.get("pr_number"),
        })

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
    """Resume run after human approval. Handles PR merge + multi-env deploy loop."""
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            return

        if decision != "approved":
            run.status        = "failed"
            run.error_message = f"Changes requested: {comment or 'No comment'}"
            run.completed_at  = datetime.now(timezone.utc)
            db.commit()
            emit_run_event(run_id, "run:failed", {"runId": run_id, "error": run.error_message})
            return

        run.status = "running"
        db.commit()
        emit_run_event(run_id, "run:approved", {"runId": run_id, "decision": "approved"})

        state = _load_state_from_db(run_id, db)
        if not state:
            _fail_run(run, "Could not reload state from DB", db)
            return

        state = {
            **state,
            "branch_name": run.branch_name,
            "pr_url":      run.pr_url,
            "pr_number":   run.pr_number,
        }

        deploy_targets = state["project"].get("deploy_targets", [])
        current_env_index = run.current_env_index if run.current_env_index is not None else -1

        if current_env_index == -1:
            # ── Step 1: Merge the feature PR ──────────────────────────────
            state = run_devops_agent({**state, "env_index": -1}, db)
            if state["status"] == "failed":
                run = db.query(Run).filter(Run.id == run_id).first()
                if run:
                    _fail_run(run, state["errors"][-1] if state["errors"] else "PR merge failed", db)
                return

            if not deploy_targets:
                # No env targets — single deploy done
                _complete_run(run_id, db)
                return

            # ── Step 2: Deploy to env[0] immediately (PR approval = dev deploy) ──
            state = run_devops_agent({**state, "env_index": 0}, db)
            if state["status"] == "failed":
                run = db.query(Run).filter(Run.id == run_id).first()
                if run:
                    _fail_run(run, state["errors"][-1] if state["errors"] else "Deploy to env[0] failed", db)
                return

            if len(deploy_targets) == 1:
                _complete_run(run_id, db)
            else:
                _await_env_approval(run_id, deploy_targets, next_index=1, db=db)

        else:
            # ── Deploy to deploy_targets[current_env_index] ───────────────
            state = run_devops_agent({**state, "env_index": current_env_index}, db)
            if state["status"] == "failed":
                run = db.query(Run).filter(Run.id == run_id).first()
                if run:
                    _fail_run(run, state["errors"][-1] if state["errors"] else "Deploy failed", db)
                return

            if current_env_index >= len(deploy_targets) - 1:
                _complete_run(run_id, db)
            else:
                _await_env_approval(run_id, deploy_targets, next_index=current_env_index + 1, db=db)

    except Exception as exc:
        log.exception("Unhandled error in resume_after_approval for %s", run_id)
        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            _fail_run(run, str(exc), db)
    finally:
        db.close()


def _complete_run(run_id: str, db) -> None:
    run = db.query(Run).filter(Run.id == run_id).first()
    if run:
        run.status       = "completed"
        run.current_step = None
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
    emit_run_event(run_id, "run:completed", {"runId": run_id, "status": "completed"})


def _await_env_approval(run_id: str, deploy_targets: list, next_index: int, db) -> None:
    run = db.query(Run).filter(Run.id == run_id).first()
    if run:
        run.status            = "awaiting_approval"
        run.current_env_index = next_index
        run.current_step      = None
        db.commit()
    next_env = deploy_targets[next_index]
    emit_run_event(run_id, "run:awaiting_env_approval", {
        "runId":      run_id,
        "envIndex":   next_index,
        "env":        next_env["env"],
        "branch":     next_env["branch"],
        "totalEnvs":  len(deploy_targets),
    })


def _fail_run(run: Run, error: str, db) -> None:
    run.status        = "failed"
    run.error_message = error
    run.current_step  = None
    run.completed_at  = datetime.now(timezone.utc)
    db.commit()
    emit_run_event(str(run.id), "run:failed", {"runId": str(run.id), "error": error})
