"""
Dev Agent — generates code changes via Claude, then applies them via PyGithub.
"""
import time
import uuid
import json

import anthropic
from github import Github, GithubException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent import Agent
from app.models.connection import Connection
from app.models.run import Run, RunStep
from app.services.encryption import decrypt_token
from app.services.notification_service import emit_run_event


_IMPLEMENT_TOOL = {
    "name": "implement_changes",
    "description": "Return the exact code changes to implement the sprint plan.",
    "input_schema": {
        "type": "object",
        "properties": {
            "branch_name": {
                "type": "string",
                "description": "Git branch name (format: agent/<ticket-id>-<short-slug>)",
            },
            "pr_title": {"type": "string"},
            "pr_body": {"type": "string"},
            "files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Full file path from repo root"},
                        "content": {"type": "string", "description": "Complete file content (not a diff)"},
                        "action": {"type": "string", "enum": ["create", "update"]},
                    },
                    "required": ["path", "content", "action"],
                },
            },
        },
        "required": ["branch_name", "pr_title", "pr_body", "files"],
    },
}


def _find_agent(pod_agents: list, role: str, db: Session) -> Agent | None:
    for pa in pod_agents:
        if pa.get("agent_role") == role:
            agent = db.query(Agent).filter(Agent.id == pa["agent_id"]).first()
            if agent:
                return agent
    return None


def _build_system_prompt(agent: Agent, project: dict) -> str:
    parts = ["You are an expert Dev Agent. You write clean, production-ready code.\n"]
    if agent.agent_skills:
        parts.append("## Your Skills\n")
        for binding in sorted(agent.agent_skills, key=lambda x: x.priority):
            skill = binding.skill
            if skill and skill.md_content:
                parts.append(f"### {skill.name}\n{skill.md_content}\n")
    if project.get("context_md"):
        parts.append(f"\n## Project Context\n{project['context_md']}\n")
    parts.append("\nALWAYS use the implement_changes tool to return your code changes. Never write raw code outside the tool.")
    return "\n".join(parts)


def run_dev_agent(state: dict, db: Session) -> dict:
    run_id = state["run_id"]
    project = state["project"]
    ticket = state["ticket"]
    pod_agents = state["pod_agents"]
    sprint_plan = state.get("sprint_plan", "")
    dev_retries = state.get("dev_retries", 0)

    start_ms = int(time.time() * 1000)

    agent = _find_agent(pod_agents, "dev", db)
    if not agent:
        # Fall back to first available agent
        for pa in pod_agents:
            agent = db.query(Agent).filter(Agent.id == pa["agent_id"]).first()
            if agent:
                break
    if not agent:
        error = "No dev agent found in pod"
        _write_step(db, run_id, None, "dev", "code_changes", "failed", {}, {}, error, 0)
        return {**state, "status": "failed", "errors": state.get("errors", []) + [error]}

    emit_run_event(run_id, "run:step:started", {
        "runId": run_id, "stepName": "code_changes", "agentRole": "dev"
    })

    run = db.query(Run).filter(Run.id == run_id).first()
    if run:
        run.current_step = "dev:code_changes"
        db.commit()

    # ── Call Claude with tool use ──
    system = _build_system_prompt(agent, project)
    user_msg = (
        f"Implement the following sprint plan:\n\n{sprint_plan}\n\n"
        f"Ticket: {ticket.get('jira_id')} — {ticket.get('title')}\n"
        f"Repository: {project.get('repo_name', 'unknown/repo')}\n"
        f"Default branch: {agent.default_branch or 'main'}\n"
        f"Branch prefix: {agent.branch_prefix or 'agent/'}\n\n"
        "Return all file changes using the implement_changes tool. "
        "Include complete file content (not diffs). "
        "Keep changes minimal and focused on the sprint plan."
    )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=agent.llm_model or "claude-sonnet-4-6",
            max_tokens=8192,
            system=system,
            tools=[_IMPLEMENT_TOOL],
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": user_msg}],
        )

        # Extract tool use block
        tool_block = next(
            (b for b in response.content if b.type == "tool_use" and b.name == "implement_changes"),
            None,
        )
        if not tool_block:
            raise ValueError("Claude did not return implement_changes tool call")

        changes = tool_block.input
        branch_name = changes.get("branch_name", f"agent/{ticket.get('jira_id', 'task').lower()}-auto")
        pr_title    = changes.get("pr_title", f"[Agent] {ticket.get('title', 'Changes')}")
        pr_body     = changes.get("pr_body", sprint_plan)
        files       = changes.get("files", [])

        log_text = f"Branch: {branch_name}\nFiles: {[f['path'] for f in files]}"
        emit_run_event(run_id, "run:step:log", {
            "runId": run_id, "stepName": "code_changes", "log": log_text
        })

        # ── Apply changes via PyGithub ──
        pr_url, pr_number = _apply_github_changes(
            agent=agent,
            project=project,
            branch_name=branch_name,
            pr_title=pr_title,
            pr_body=pr_body,
            files=files,
            db=db,
        )

        duration_ms = int(time.time() * 1000) - start_ms
        _write_step(db, run_id, str(agent.id), "dev", "code_changes", "success",
                    {"sprint_plan_length": len(sprint_plan)},
                    {"branch_name": branch_name, "pr_url": pr_url, "pr_number": pr_number,
                     "files_changed": len(files)},
                    log_text, duration_ms)

        # Update run with PR info
        if run:
            run.branch_name = branch_name
            run.pr_url      = pr_url
            run.pr_number   = pr_number
            db.commit()

        emit_run_event(run_id, "run:step:completed", {
            "runId": run_id, "stepName": "code_changes", "status": "success",
            "output": {"pr_url": pr_url, "branch_name": branch_name}
        })

        return {
            **state,
            "branch_name": branch_name,
            "pr_url": pr_url,
            "pr_number": pr_number,
            "current_agent": "qa",
            "dev_retries": dev_retries,
        }

    except Exception as e:
        duration_ms = int(time.time() * 1000) - start_ms
        error = f"Dev agent error: {str(e)}"
        _write_step(db, run_id, str(agent.id) if agent else None, "dev", "code_changes",
                    "failed", {}, {}, error, duration_ms)
        emit_run_event(run_id, "run:step:failed", {"runId": run_id, "error": error})
        return {**state, "status": "failed", "errors": state.get("errors", []) + [error]}


def _apply_github_changes(
    agent: Agent,
    project: dict,
    branch_name: str,
    pr_title: str,
    pr_body: str,
    files: list,
    db: Session,
) -> tuple[str, int]:
    """Create branch, commit files, open PR. Returns (pr_url, pr_number)."""
    repo_connection_id = project.get("repo_connection_id")
    repo_name = project.get("repo_name")

    if not repo_connection_id or not repo_name:
        raise ValueError("Project has no GitHub connection or repo configured")

    conn = db.query(Connection).filter(Connection.id == repo_connection_id).first()
    if not conn or not conn.access_token:
        raise ValueError("GitHub connection not found or missing token")

    token = decrypt_token(conn.access_token)
    g = Github(token)
    repo = g.get_repo(repo_name)

    default_branch = agent.default_branch or repo.default_branch or "main"
    base_sha = repo.get_branch(default_branch).commit.sha

    # Create branch
    try:
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
    except GithubException as e:
        if e.status == 422:  # branch already exists
            pass
        else:
            raise

    # Commit each file
    for file in files:
        path    = file["path"]
        content = file["content"]
        action  = file.get("action", "create")
        msg     = f"agent: {action} {path}"
        try:
            existing = repo.get_contents(path, ref=branch_name)
            repo.update_file(path, msg, content, existing.sha, branch=branch_name)
        except GithubException:
            repo.create_file(path, msg, content, branch=branch_name)

    # Open PR
    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base=default_branch,
    )
    return pr.html_url, pr.number


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
