"""
QA Agent — runs the PR's own tests inside an isolated sandbox, then reviews
the diff with an LLM.

Originally (Phase 7) this only asked Claude to read a diff and vote
PASS/FAIL — real, but with no evidence the change actually runs. It now
executes first: `sandbox_service.execute()` clones the branch and runs the
project's own install/test/lint commands in a network-isolated container (see
that module's docstring for why network is on for install and off for
test/lint, and why an infra failure there is "skipped", never "failed").

  * A real test failure is authoritative and skips the LLM call entirely —
    there is nothing useful for a model to opine on when the suite already
    disagrees with the change. It is retried against `dev`, exactly like a
    request-changes verdict always was, and a `ReviewFinding(severity=
    "critical", category="tests")` is written so the same policy gate that
    blocks on the Reviewer agent's findings also blocks on a failing suite.
  * A "skipped" outcome (no Docker, no recognised project type, sandbox
    disabled, no repo connection, branch not checked out yet) falls back to
    the original LLM-only review — every project this cannot yet execute
    keeps working exactly as it did before this file changed, and the review
    prompt says plainly that no execution backs it.
  * A "passed" outcome is handed to the LLM as grounding, not as a
    replacement for it — a green test suite says nothing about design,
    security or missed edge cases, which is what the review prompt asks for.
"""
import time
import uuid

import anthropic
from github import Github, GithubException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent import Agent
from app.models.connection import Connection
from app.models.insight import ReviewFinding
from app.models.run import Run, RunStep
from app.services import sandbox_service
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

    # ── Execute first: real evidence beats an LLM's opinion of a diff ──────
    exec_result = _execute_tests(db, run_id, agent, project, branch_name)

    if exec_result.outcome == "failed":
        return _fail_from_execution(db, state, agent, exec_result, dev_retries, max_retries, start_ms)

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
        f"{_execution_note(exec_result)}"
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
                    {"execution": exec_result.as_dict()},
                    {"passed": passed, "review": review_text},
                    review_text, duration_ms)

        emit_run_event(run_id, "run:step:completed", {
            "runId": run_id, "stepName": "code_review",
            "status": "success" if passed else "failed",
            "output": {"passed": passed}
        })

        test_results = {"passed": passed, "review": review_text, "retry": dev_retries,
                         "execution": exec_result.as_dict()}

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
                    "success", {"execution": exec_result.as_dict()},
                    {"passed": True, "message": f"QA error (auto-pass): {error}"},
                    error, duration_ms)
        return {**state, "test_results": {"passed": True, "message": f"Auto-pass (QA error)"}, "current_agent": "approval"}


# ── Execution sandbox glue ────────────────────────────────────────────────────

def _execute_tests(db: Session, run_id, agent: Agent | None, project: dict,
                    branch_name: str) -> sandbox_service.ExecutionResult:
    if not branch_name:
        return sandbox_service.ExecutionResult(outcome="skipped", reason="No branch to check out yet")
    creds = _repo_credentials(project, db)
    if not creds:
        return sandbox_service.ExecutionResult(outcome="skipped",
                                                 reason="No repository connection configured")
    token, provider, host = creds

    start_ms = int(time.time() * 1000)
    try:
        result = sandbox_service.execute(
            repo_name=project.get("repo_name", ""), branch=branch_name, token=token,
            provider=provider, host=host, run_id=str(run_id),
        )
    except Exception as exc:                              # noqa: BLE001 — infra must never block QA
        result = sandbox_service.ExecutionResult(outcome="skipped", reason=f"Sandbox error: {exc}")
    duration_ms = int(time.time() * 1000) - start_ms

    log_text = f"Execution: {result.outcome}" + (f" — {result.reason}" if result.reason else "")
    emit_run_event(run_id, "run:step:log",
                   {"runId": str(run_id), "stepName": "execute_tests", "log": log_text})
    _write_step(db, run_id, str(agent.id) if agent else None, "qa", "execute_tests",
                "failed" if result.outcome == "failed" else "success",
                {"branch": branch_name}, result.as_dict(), log_text, duration_ms)
    return result


def _repo_credentials(project: dict, db: Session) -> tuple[str, str, str | None] | None:
    cid = project.get("repo_connection_id")
    if not cid:
        return None
    conn = db.query(Connection).filter(Connection.id == cid).first()
    if not conn or not conn.access_token:
        return None
    try:
        token = decrypt_token(conn.access_token)
    except Exception:
        return None
    provider = (conn.type or "github").lower()
    host = conn.workspace_url if provider == "gitlab" else None
    return token, provider, host


def _execution_note(result: sandbox_service.ExecutionResult) -> str:
    if result.outcome == "skipped":
        return (f"**Automated test execution:** not run ({result.reason}). "
                "This review is LLM-only — treat it as advisory, not proof the change runs.\n\n")
    tail = (result.test_output or "")[-2000:]
    return (f"**Automated test execution: PASSED** (`{result.commands.get('test')}` "
            f"in {result.duration_ms}ms)\n```\n{tail}\n```\n"
            "Tests already confirm the change runs; focus your review on design, security "
            "and edge cases a test suite would not catch.\n\n")


def _fail_from_execution(db: Session, state: dict, agent: Agent | None,
                          result: sandbox_service.ExecutionResult, dev_retries: int,
                          max_retries: int, start_ms: int) -> dict:
    """A real test failure is ground truth — skip the LLM opinion entirely and
    record a critical ReviewFinding so the same severity gate that blocks on
    the Reviewer agent's findings also blocks on a failing test suite."""
    run_id = state["run_id"]
    tail = (result.test_output or "")[-2000:]
    message = f"Test suite failed (exit {result.exit_code}): {tail}"[:4000]
    db.add(ReviewFinding(
        run_id=run_id, agent_id=agent.id if agent else None,
        severity="critical", category="tests", message=message,
    ))
    db.commit()

    duration_ms = int(time.time() * 1000) - start_ms
    _write_step(db, run_id, str(agent.id) if agent else None, "qa", "code_review", "failed",
                {}, {"passed": False, "execution": result.as_dict()},
                f"Tests failed — skipping LLM review.\n{message}", duration_ms)
    emit_run_event(run_id, "run:step:completed",
                   {"runId": run_id, "stepName": "code_review", "status": "failed",
                    "output": {"passed": False}})

    test_results = {"passed": False, "execution": result.as_dict(), "retry": dev_retries}
    if dev_retries >= max_retries:
        return {**state, "test_results": test_results, "status": "failed",
                "errors": state.get("errors", []) + [f"QA failed after {dev_retries} retries (tests did not pass)"]}
    return {**state, "test_results": test_results, "current_agent": "dev", "dev_retries": dev_retries + 1}


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
