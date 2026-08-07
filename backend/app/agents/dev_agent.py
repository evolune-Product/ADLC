"""
Dev Agent — generates code changes via the LLM layer, then applies them to
GitHub or GitLab and opens a PR/MR.

Phase 11 changes:
  * calls through `llm_service` (any provider, BYO key) and meters every token
  * injects retrieved codebase memory so runs stop starting cold
  * enforces the blast-radius half of the approval policy *before* writing —
    protected paths, protected branches and a max-files-changed cap are checked
    against the model's proposed changes rather than discovered at review time
"""
import time

from sqlalchemy.orm import Session

from app.agents._common import (build_system_prompt, call_llm, find_agent,
                                start_step, write_step)
from app.models.agent import Agent
from app.models.connection import Connection
from app.models.project import Project
from app.models.run import Run
from app.services import policy_service
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

_ROLE_INTRO = ("You are an expert Dev Agent. You write clean, production-ready code.\n"
               "ALWAYS use the implement_changes tool to return your code changes. "
               "Never write raw code outside the tool.")


def _resolve_agent(pod_agents: list, db: Session) -> Agent | None:
    agent = find_agent(pod_agents, "dev", db)
    if agent:
        return agent
    for pa in pod_agents:                      # fall back to any agent in the pod
        found = db.query(Agent).filter(Agent.id == pa["agent_id"]).first()
        if found:
            return found
    return None


def run_dev_agent(state: dict, db: Session) -> dict:
    run_id = state["run_id"]
    project = state["project"]
    ticket = state["ticket"]
    pod_agents = state["pod_agents"]
    sprint_plan = state.get("sprint_plan", "")
    dev_retries = state.get("dev_retries", 0)

    start_ms = int(time.time() * 1000)

    agent = _resolve_agent(pod_agents, db)
    if not agent:
        error = "No dev agent found in pod"
        write_step(db, run_id, None, "dev", "code_changes", "failed", {}, {}, error, 0)
        return {**state, "status": "failed", "errors": state.get("errors", []) + [error]}

    start_step(run_id, "code_changes", "dev", db)

    system = build_system_prompt(
        agent, project, role_intro=_ROLE_INTRO, db=db,
        memory_query=f"{ticket.get('title', '')} {ticket.get('description', '')} {sprint_plan[:500]}",
    )
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
        result = call_llm(db, run_id=run_id, agent=agent, agent_role="dev",
                          system=system, user=user_msg, tool=_IMPLEMENT_TOOL, max_tokens=8192)
        changes = result.tool_input
        if not changes:
            raise ValueError("Model did not return an implement_changes tool call")

        branch_name = changes.get("branch_name") or f"agent/{ticket.get('jira_id', 'task').lower()}-auto"
        pr_title = changes.get("pr_title") or f"[Agent] {ticket.get('title', 'Changes')}"
        pr_body = changes.get("pr_body") or sprint_plan
        files = changes.get("files") or []

        # ── Policy pre-flight: what is this agent allowed to touch at all? ────
        project_row = db.query(Project).filter(Project.id == project["id"]).first()
        policy = policy_service.resolve_policy(
            db,
            org_id=project_row.org_id if project_row else None,
            project_id=project_row.id if project_row else None,
        )
        violations = policy_service.check_changes(policy, files=files, branch=branch_name)
        if violations:
            error = "Blocked by approval policy '{}': {}".format(
                policy.get("name", "Default"), "; ".join(violations))
            write_step(db, run_id, str(agent.id), "dev", "code_changes", "failed",
                       {"files": [f.get("path") for f in files]},
                       {"policy_violations": violations, "policy": policy.get("name")},
                       error, int(time.time() * 1000) - start_ms)
            emit_run_event(run_id, "run:policy:blocked",
                           {"runId": str(run_id), "violations": violations,
                            "policy": policy.get("name")})
            return {**state, "status": "failed", "policy_violations": violations,
                    "errors": state.get("errors", []) + [error]}

        log_text = f"Branch: {branch_name}\nFiles: {[f['path'] for f in files]}"
        emit_run_event(run_id, "run:step:log",
                       {"runId": str(run_id), "stepName": "code_changes", "log": log_text})

        pr_url, pr_number = _apply_changes(
            agent=agent, project=project, branch_name=branch_name, pr_title=pr_title,
            pr_body=pr_body, files=files, db=db,
        )

        duration_ms = int(time.time() * 1000) - start_ms
        write_step(db, run_id, str(agent.id), "dev", "code_changes", "success",
                   {"sprint_plan_length": len(sprint_plan)},
                   {"branch_name": branch_name, "pr_url": pr_url, "pr_number": pr_number,
                    "files_changed": len(files), "model": result.model,
                    "cost_usd": round(result.cost_usd, 4)},
                   log_text, duration_ms)

        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.branch_name, run.pr_url, run.pr_number = branch_name, pr_url, pr_number
            db.commit()

        emit_run_event(run_id, "run:step:completed",
                       {"runId": str(run_id), "stepName": "code_changes", "status": "success",
                        "output": {"pr_url": pr_url, "branch_name": branch_name}})

        return {
            **state,
            "branch_name": branch_name,
            "pr_url": pr_url,
            "pr_number": pr_number,
            "changed_files": [f.get("path") for f in files],
            "current_agent": "qa",
            "dev_retries": dev_retries,
        }

    except Exception as e:
        duration_ms = int(time.time() * 1000) - start_ms
        error = f"Dev agent error: {str(e)}"
        write_step(db, run_id, str(agent.id) if agent else None, "dev", "code_changes",
                   "failed", {}, {}, error, duration_ms)
        emit_run_event(run_id, "run:step:failed", {"runId": str(run_id), "error": error})
        return {**state, "status": "failed", "errors": state.get("errors", []) + [error]}


# ── VCS application (GitHub or GitLab) ────────────────────────────────────────

def _apply_changes(*, agent, project: dict, branch_name: str, pr_title: str,
                   pr_body: str, files: list, db: Session) -> tuple[str, int]:
    repo_connection_id = project.get("repo_connection_id")
    repo_name = project.get("repo_name")
    if not repo_connection_id or not repo_name:
        raise ValueError("Project has no repository connection or repo configured")

    conn = db.query(Connection).filter(Connection.id == repo_connection_id).first()
    if not conn or not conn.access_token:
        raise ValueError("Repository connection not found or missing token")

    token = decrypt_token(conn.access_token)
    if (conn.type or "github").lower() == "gitlab":
        return _apply_gitlab(token, conn.workspace_url, agent, repo_name,
                             branch_name, pr_title, pr_body, files)
    return _apply_github(token, agent, repo_name, branch_name, pr_title, pr_body, files)


def _apply_github(token, agent, repo_name, branch_name, pr_title, pr_body, files) -> tuple[str, int]:
    from github import Github, GithubException

    repo = Github(token).get_repo(repo_name)
    default_branch = agent.default_branch or repo.default_branch or "main"
    base_sha = repo.get_branch(default_branch).commit.sha

    try:
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
    except GithubException as e:
        if e.status != 422:          # 422 = branch already exists
            raise

    for file in files:
        path, content = file["path"], file["content"]
        msg = f"agent: {file.get('action', 'create')} {path}"
        try:
            existing = repo.get_contents(path, ref=branch_name)
            repo.update_file(path, msg, content, existing.sha, branch=branch_name)
        except GithubException:
            repo.create_file(path, msg, content, branch=branch_name)

    pr = repo.create_pull(title=pr_title, body=pr_body, head=branch_name, base=default_branch)
    return pr.html_url, pr.number


def _apply_gitlab(token, host, agent, repo_name, branch_name, pr_title, pr_body, files) -> tuple[str, int]:
    from app.services.gitlab_service import GitLabClient

    client = GitLabClient(token, host)
    default_branch = agent.default_branch or client.default_branch(repo_name)
    client.create_branch(repo_name, branch_name, default_branch)
    client.commit_files(repo_name, branch_name, f"agent: {pr_title}", files)
    mr = client.create_merge_request(repo_name, source=branch_name, target=default_branch,
                                     title=pr_title, description=pr_body)
    return mr["url"], mr["number"]
