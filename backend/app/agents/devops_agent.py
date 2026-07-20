"""
DevOps Agent — handles one deploy operation per call.

env_index == -1  →  merge the feature PR (initial approval)
env_index == 0   →  merge PR's base branch → deploy_targets[0].branch
env_index == N   →  merge deploy_targets[N-1].branch → deploy_targets[N].branch

The caller (run_tasks.py) controls run status and decides whether to loop.
"""
import time
import uuid
from datetime import datetime, timezone

from github import Github, GithubException
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.connection import Connection
from app.models.run import Run, RunStep
from app.services.encryption import decrypt_token
from app.services.notification_service import emit_run_event


def _find_agent(pod_agents: list, role: str, db: Session) -> Agent | None:
    for pa in pod_agents:
        if pa.get("agent_role") == role:
            agent = db.query(Agent).filter(Agent.id == pa["agent_id"]).first()
            if agent:
                return agent
    return None


def run_devops_agent(state: dict, db: Session) -> dict:
    """
    Executes one deploy step. Returns state with status="deployed" or "failed".
    Does NOT update run.status — the task controls that.
    """
    run_id      = state["run_id"]
    project     = state["project"]
    pod_agents  = state["pod_agents"]
    pr_number   = state.get("pr_number")
    env_index   = state.get("env_index", -1)
    deploy_targets = project.get("deploy_targets", [])

    start_ms = int(time.time() * 1000)
    agent = _find_agent(pod_agents, "devops", db)

    run = db.query(Run).filter(Run.id == run_id).first()

    if env_index == -1:
        # ── Merge the feature PR ──────────────────────────────────────────
        step_name = "merge_pr"
        emit_run_event(run_id, "run:step:started", {
            "runId": run_id, "stepName": step_name, "agentRole": "devops"
        })
        if run:
            run.current_step = f"devops:{step_name}"
            db.commit()

        result = _merge_pr(project, pr_number, db)
        success = result["merged"]
        output = {**result, "type": "pr_merge"}

    else:
        # ── Deploy between environment branches ───────────────────────────
        if env_index == 0:
            # Source = the branch the PR was merged into (PR's base)
            source_branch = _get_pr_base_branch(project, pr_number, db) or "main"
        else:
            source_branch = deploy_targets[env_index - 1]["branch"]

        target = deploy_targets[env_index]
        step_name = f"deploy_to_{target['env']}"

        emit_run_event(run_id, "run:step:started", {
            "runId": run_id, "stepName": step_name, "agentRole": "devops"
        })
        if run:
            run.current_step = f"devops:{step_name}"
            db.commit()

        result = _merge_branches(project, source_branch, target["branch"], db)
        success = result["merged"]
        output = {**result, "type": "env_deploy", "env": target["env"], "branch": target["branch"]}

    duration_ms = int(time.time() * 1000) - start_ms
    _write_step(
        db, run_id,
        str(agent.id) if agent else None,
        "devops", step_name,
        "success" if success else "failed",
        {}, output, output.get("message"), duration_ms,
    )

    if not success:
        error = output.get("message", "Deploy failed")
        emit_run_event(run_id, "run:step:failed", {"runId": run_id, "stepName": step_name, "error": error})
        return {**state, "status": "failed", "errors": state.get("errors", []) + [error]}

    emit_run_event(run_id, "run:step:completed", {
        "runId": run_id, "stepName": step_name, "status": "success", "output": output
    })
    return {**state, "status": "deployed"}


# ─── GitHub helpers ────────────────────────────────────────────────────────────

def _get_github_repo(project: dict, db: Session):
    conn = db.query(Connection).filter(Connection.id == project["repo_connection_id"]).first()
    if not conn or not conn.access_token:
        return None
    token = decrypt_token(conn.access_token)
    return Github(token).get_repo(project["repo_name"])


def _merge_pr(project: dict, pr_number: int | None, db: Session) -> dict:
    if not pr_number or not project.get("repo_connection_id") or not project.get("repo_name"):
        return {"merged": False, "message": "No PR number or repo configured"}
    try:
        repo = _get_github_repo(project, db)
        if not repo:
            return {"merged": False, "message": "GitHub connection missing"}
        pr = repo.get_pull(pr_number)
        if pr.merged:
            return {"merged": True, "message": "PR was already merged"}
        result = pr.merge(merge_method="squash")
        return {"merged": result.merged, "message": result.message or "Merged successfully"}
    except GithubException as e:
        msg = e.data.get("message", str(e)) if hasattr(e, "data") and e.data else str(e)
        return {"merged": False, "message": f"GitHub error: {msg}"}
    except Exception as e:
        return {"merged": False, "message": str(e)}


def _get_pr_base_branch(project: dict, pr_number: int | None, db: Session) -> str | None:
    """Return the branch the PR was merged into (e.g. 'develop', 'main')."""
    if not pr_number or not project.get("repo_connection_id") or not project.get("repo_name"):
        return None
    try:
        repo = _get_github_repo(project, db)
        if not repo:
            return None
        return repo.get_pull(pr_number).base.ref
    except Exception:
        return None


def _merge_branches(project: dict, source: str, target: str, db: Session) -> dict:
    """Fast-forward/merge source branch into target branch on GitHub."""
    if not project.get("repo_connection_id") or not project.get("repo_name"):
        return {"merged": False, "message": "Repo not configured"}
    try:
        repo = _get_github_repo(project, db)
        if not repo:
            return {"merged": False, "message": "GitHub connection missing"}
        commit = repo.merge(target, source, f"Deploy: merge {source} into {target}")
        if commit is None:
            return {"merged": True, "message": f"{source} is already up-to-date with {target}"}
        return {"merged": True, "message": f"Merged {source} into {target}", "sha": commit.sha}
    except GithubException as e:
        msg = e.data.get("message", str(e)) if hasattr(e, "data") and e.data else str(e)
        if "already up-to-date" in msg.lower():
            return {"merged": True, "message": "Already up-to-date"}
        return {"merged": False, "message": f"GitHub error: {msg}"}
    except Exception as e:
        return {"merged": False, "message": str(e)}


# ─── Step writer ───────────────────────────────────────────────────────────────

def _write_step(db: Session, run_id: str, agent_id: str | None, agent_role: str,
                step_name: str, status: str, input_: dict, output: dict,
                log: str | None, duration_ms: int):
    step = RunStep(
        id=uuid.uuid4(),
        run_id=run_id,
        agent_id=agent_id,
        agent_role=agent_role,
        step_name=step_name,
        status=status,
        input=input_,
        output=output,
        log=log,
        duration_ms=duration_ms,
    )
    db.add(step)
    db.commit()
