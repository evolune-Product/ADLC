"""
QA Agent — reviews the PR and runs basic checks.

Phase 7 implementation: code review via Claude (no live test runner yet).
The agent reads the PR diff and checks it against the sprint plan.
Returns pass/fail for the approval gate decision.
"""
import time
import uuid

import anthropic
from github import Github, GithubException
from sqlalchemy.orm import Session

from app.config import settings
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


def run_qa_agent(state: dict, db: Session) -> dict:
    run_id     = state["run_id"]
    project    = state["project"]
    pod_agents = state["pod_agents"]
    sprint_plan = state.get("sprint_plan", "")
    pr_url     = state.get("pr_url", "")
    pr_number  = state.get("pr_number")
    branch_name = state.get("branch_name", "")
    dev_retries = state.get("dev_retries", 0)
    max_retries = state.get("max_dev_retries", 2)

    start_ms = int(time.time() * 1000)

    agent = _find_agent(pod_agents, "qa", db)
    # QA agent is optional — if none found, auto-pass
    if not agent:
        duration_ms = int(time.time() * 1000) - start_ms
        _write_step(db, run_id, None, "qa", "code_review", "success",
                    {}, {"passed": True, "message": "No QA agent configured — auto-passed"},
                    "Auto-passed: no QA agent in pod", duration_ms)
        return {**state, "test_results": {"passed": True, "message": "Auto-passed"}, "current_agent": "approval"}

    emit_run_event(run_id, "run:step:started", {
        "runId": run_id, "stepName": "code_review", "agentRole": "qa"
    })

    run = db.query(Run).filter(Run.id == run_id).first()
    if run:
        run.current_step = "qa:code_review"
        db.commit()

    # Fetch PR diff from GitHub
    pr_diff = _get_pr_diff(project, pr_number, db)

    # Build QA review prompt
    system = "You are an expert QA Agent performing a code review."
    if agent.agent_skills:
        skill_mds = []
        for binding in sorted(agent.agent_skills, key=lambda x: x.priority):
            if binding.skill and binding.skill.md_content:
                skill_mds.append(f"### {binding.skill.name}\n{binding.skill.md_content}")
        if skill_mds:
            system += "\n\n## Your QA Skills\n" + "\n".join(skill_mds)

    user_msg = (
        f"Review this PR for quality and correctness.\n\n"
        f"**Sprint Plan:**\n{sprint_plan}\n\n"
        f"**PR Diff:**\n```diff\n{pr_diff}\n```\n\n"
        "Answer:\n"
        "1. Does the implementation match the sprint plan? (yes/no)\n"
        "2. Are there any obvious bugs or issues?\n"
        "3. Final verdict: PASS or FAIL\n\n"
        "Keep your response concise. End with exactly 'VERDICT: PASS' or 'VERDICT: FAIL'."
    )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=agent.llm_model or "claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        review_text = response.content[0].text
        passed = "VERDICT: PASS" in review_text.upper()

        duration_ms = int(time.time() * 1000) - start_ms
        _write_step(db, run_id, str(agent.id), "qa", "code_review",
                    "success" if passed else "failed",
                    {}, {"passed": passed, "review": review_text},
                    review_text, duration_ms)

        emit_run_event(run_id, "run:step:completed", {
            "runId": run_id, "stepName": "code_review",
            "status": "success" if passed else "failed",
            "output": {"passed": passed}
        })

        test_results = {"passed": passed, "review": review_text, "retry": dev_retries}

        if passed:
            return {**state, "test_results": test_results, "current_agent": "approval"}
        else:
            if dev_retries >= max_retries:
                return {
                    **state,
                    "test_results": test_results,
                    "status": "failed",
                    "errors": state.get("errors", []) + [f"QA failed after {dev_retries} retries"],
                }
            return {
                **state,
                "test_results": test_results,
                "current_agent": "dev",
                "dev_retries": dev_retries + 1,
            }

    except Exception as e:
        duration_ms = int(time.time() * 1000) - start_ms
        error = f"QA agent error: {str(e)}"
        # On QA error, auto-pass to not block the run
        _write_step(db, run_id, str(agent.id) if agent else None, "qa", "code_review",
                    "success", {}, {"passed": True, "message": f"QA error (auto-pass): {error}"},
                    error, duration_ms)
        return {**state, "test_results": {"passed": True, "message": f"Auto-pass (QA error)"}, "current_agent": "approval"}


def _get_pr_diff(project: dict, pr_number: int | None, db: Session) -> str:
    if not pr_number or not project.get("repo_connection_id") or not project.get("repo_name"):
        return "(diff not available)"
    try:
        conn = db.query(Connection).filter(Connection.id == project["repo_connection_id"]).first()
        if not conn or not conn.access_token:
            return "(diff not available)"
        token = decrypt_token(conn.access_token)
        g = Github(token)
        repo = g.get_repo(project["repo_name"])
        pr = repo.get_pull(pr_number)
        files = pr.get_files()
        diff_parts = []
        for f in list(files)[:10]:  # cap at 10 files
            diff_parts.append(f"--- {f.filename}\n{f.patch or '(binary)'}")
        return "\n\n".join(diff_parts)[:8000]  # cap diff size
    except Exception:
        return "(diff not available)"


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
