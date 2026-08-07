"""
Reviewer Agent — the fifth agent, and the one that makes the approval gate real.

Why this exists: review capacity is the 2026 bottleneck (review time is up ~91%
on high-AI-adoption teams), and standalone AI review costs $24–30/dev/month.
Bundling review into the run beats the specialists on price, and — unlike a
generic reviewer — this one is trained on *your* skills and *your* coding
standards, then feeds a machine-checkable score into the deploy policy.

Output: structured ReviewFinding rows (severity, category, file, line, message,
suggestion) + a 0–100 score, posted back to the PR/MR as a single review comment.
"""
from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from app.agents._common import (build_system_prompt, call_llm, find_agent,
                                start_step, write_step)
from app.models.connection import Connection
from app.models.insight import ReviewFinding
from app.models.run import Run
from app.services.encryption import decrypt_token
from app.services.notification_service import emit_run_event
from app.services.policy_service import SEVERITY_RANK, review_score

log = logging.getLogger(__name__)

MAX_DIFF_CHARS = 60_000

_REVIEW_TOOL = {
    "name": "submit_review",
    "description": "Submit a structured code review of the pull request diff.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "2-4 sentence verdict on the change."},
            "verdict": {"type": "string", "enum": ["approve", "comment", "request_changes"]},
            "findings": {
                "type": "array",
                "description": "Concrete problems. Empty array if the change is clean.",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string",
                                     "enum": ["info", "low", "medium", "high", "critical"]},
                        "category": {"type": "string",
                                     "enum": ["security", "correctness", "tests",
                                              "performance", "style", "quality"]},
                        "file_path": {"type": "string"},
                        "line": {"type": "integer", "description": "Line in the new file, 0 if unknown."},
                        "message": {"type": "string", "description": "What is wrong and why it matters."},
                        "suggestion": {"type": "string", "description": "Concrete fix."},
                    },
                    "required": ["severity", "category", "message"],
                },
            },
        },
        "required": ["summary", "verdict", "findings"],
    },
}

_ROLE_INTRO = """You are a senior Reviewer Agent performing a pre-merge code review.

Report every real issue you find, including ones you are uncertain about or
consider low-severity — a downstream policy gate ranks and filters them, so
coverage matters more than self-filtering here. For each finding give a severity
and a category so that filter can work.

Judge the diff on: correctness and edge cases, security (injection, authz,
secrets, unsafe deserialization), missing or weak tests, performance traps, and
adherence to the coding standards in your skills. Do not invent problems in code
that is fine — an empty findings list is a valid and useful answer."""


def run_review_agent(state: dict, db: Session) -> dict:
    run_id = state["run_id"]
    project = state["project"]
    ticket = state["ticket"]
    pod_agents = state["pod_agents"]
    pr_number = state.get("pr_number")

    start_ms = int(time.time() * 1000)
    agent = find_agent(pod_agents, "reviewer", db)

    # Reviewer is optional: a pod without one skips straight to the human gate.
    if not agent:
        return {**state, "review_score": None, "review_skipped": True}

    start_step(run_id, "code_review", "reviewer", db)

    try:
        diff = _fetch_diff(project, pr_number, db)
        if not diff:
            raise ValueError("No diff available to review")

        system = build_system_prompt(
            agent, project, role_intro=_ROLE_INTRO, db=db,
            memory_query=f"{ticket.get('title', '')} {ticket.get('description', '')}",
        )
        user = (
            f"Ticket {ticket.get('jira_id', '')}: {ticket.get('title', '')}\n"
            f"{ticket.get('description', '') or ''}\n\n"
            f"Sprint plan:\n{state.get('sprint_plan', '(none)')}\n\n"
            f"Review this diff:\n\n{diff}"
        )

        result = call_llm(db, run_id=run_id, agent=agent, agent_role="reviewer",
                          system=system, user=user, tool=_REVIEW_TOOL, max_tokens=8192)

        payload = result.tool_input or {"summary": result.text or "No review produced",
                                        "verdict": "comment", "findings": []}
        findings = payload.get("findings") or []

        db.query(ReviewFinding).filter(ReviewFinding.run_id == run_id).delete(synchronize_session=False)
        rows = []
        for f in findings:
            row = ReviewFinding(
                run_id=run_id,
                agent_id=agent.id,
                severity=(f.get("severity") or "info").lower(),
                category=(f.get("category") or "quality").lower(),
                file_path=f.get("file_path"),
                line=f.get("line") or None,
                message=f.get("message", "")[:4000],
                suggestion=(f.get("suggestion") or None),
            )
            db.add(row)
            rows.append(row)
        db.commit()

        score = review_score(rows)
        worst = max((SEVERITY_RANK.get(r.severity, 0) for r in rows), default=0)
        worst_label = next((k for k, v in SEVERITY_RANK.items() if v == worst), "info")

        posted = _post_to_vcs(project, pr_number, payload, rows, score, db)
        if posted:
            for r in rows:
                r.posted_to_vcs = True
            db.commit()

        log_text = (
            f"Verdict: {payload.get('verdict')} · score {score}/100 · "
            f"{len(rows)} finding(s), worst = {worst_label}\n{payload.get('summary', '')}"
        )
        emit_run_event(run_id, "run:step:log",
                       {"runId": str(run_id), "stepName": "code_review", "log": log_text})

        output = {
            "score": score,
            "verdict": payload.get("verdict"),
            "summary": payload.get("summary"),
            "finding_count": len(rows),
            "worst_severity": worst_label,
            "posted_to_vcs": posted,
            "findings": [
                {"severity": r.severity, "category": r.category, "file_path": r.file_path,
                 "line": r.line, "message": r.message, "suggestion": r.suggestion}
                for r in rows
            ],
        }
        write_step(db, run_id, str(agent.id), "reviewer", "code_review", "success",
                   {"pr_number": pr_number, "diff_chars": len(diff)}, output,
                   log_text, int(time.time() * 1000) - start_ms)

        emit_run_event(run_id, "run:review:completed",
                       {"runId": str(run_id), "score": score, "verdict": payload.get("verdict"),
                        "findingCount": len(rows), "worstSeverity": worst_label})
        emit_run_event(run_id, "run:step:completed",
                       {"runId": str(run_id), "stepName": "code_review",
                        "status": "success", "output": {"score": score}})

        return {**state, "review_score": score, "review_verdict": payload.get("verdict"),
                "review_findings": len(rows)}

    except Exception as exc:
        error = f"Reviewer agent error: {exc}"
        log.exception("Review failed for run %s", run_id)
        write_step(db, run_id, str(agent.id) if agent else None, "reviewer", "code_review",
                   "failed", {"pr_number": pr_number}, {}, error,
                   int(time.time() * 1000) - start_ms)
        emit_run_event(run_id, "run:step:failed",
                       {"runId": str(run_id), "stepName": "code_review", "error": error})
        # A failed review must not fail the run — it degrades to "no machine
        # verdict", and the policy decides whether that is enough to block.
        return {**state, "review_score": None, "review_error": error}


# ── VCS helpers (GitHub + GitLab) ─────────────────────────────────────────────

def _connection(project: dict, db: Session) -> Connection | None:
    cid = project.get("repo_connection_id")
    return db.query(Connection).filter(Connection.id == cid).first() if cid else None


def _fetch_diff(project: dict, pr_number: int | None, db: Session) -> str:
    conn = _connection(project, db)
    if not conn or not conn.access_token or not pr_number:
        return ""
    token = decrypt_token(conn.access_token)

    if (conn.type or "github").lower() == "gitlab":
        from app.services.gitlab_service import GitLabClient
        files = GitLabClient(token, conn.workspace_url).merge_request_changes(
            project["repo_name"], pr_number)
    else:
        from github import Github
        pr = Github(token).get_repo(project["repo_name"]).get_pull(pr_number)
        files = [
            {"filename": f.filename, "status": f.status, "additions": f.additions,
             "deletions": f.deletions, "patch": f.patch or ""}
            for f in list(pr.get_files())[:30]
        ]

    parts, total = [], 0
    for f in files:
        block = (f"--- {f['filename']} ({f.get('status')}, "
                 f"+{f.get('additions', 0)}/-{f.get('deletions', 0)}) ---\n{f.get('patch', '')}\n")
        if total + len(block) > MAX_DIFF_CHARS:
            parts.append(f"\n[diff truncated — {len(files) - len(parts)} more file(s) not shown]")
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts)


def _post_to_vcs(project: dict, pr_number: int | None, payload: dict,
                 rows: list[ReviewFinding], score: int, db: Session) -> bool:
    """One consolidated comment — inline noise is what makes AI review unwelcome."""
    conn = _connection(project, db)
    if not conn or not conn.access_token or not pr_number:
        return False

    body = _format_comment(payload, rows, score)
    try:
        token = decrypt_token(conn.access_token)
        if (conn.type or "github").lower() == "gitlab":
            from app.services.gitlab_service import GitLabClient
            GitLabClient(token, conn.workspace_url).comment(project["repo_name"], pr_number, body)
        else:
            from github import Github
            Github(token).get_repo(project["repo_name"]).get_pull(pr_number).create_issue_comment(body)
        return True
    except Exception:
        log.exception("Could not post review comment to the pull request")
        return False


_ICON = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}


def _format_comment(payload: dict, rows: list[ReviewFinding], score: int) -> str:
    verdict = payload.get("verdict", "comment")
    header = {"approve": "✅ Approved by Reviewer Agent",
              "comment": "💬 Reviewer Agent comments",
              "request_changes": "🛑 Reviewer Agent requests changes"}.get(verdict, "Review")

    lines = [f"## {header}", "", f"**Score: {score}/100** · {len(rows)} finding(s)", "",
             payload.get("summary", ""), ""]
    if rows:
        lines.append("| | Severity | Category | Location | Finding |")
        lines.append("|---|---|---|---|---|")
        for r in sorted(rows, key=lambda x: -SEVERITY_RANK.get(x.severity, 0))[:25]:
            loc = f"`{r.file_path}`" + (f":{r.line}" if r.line else "") if r.file_path else "—"
            lines.append(f"| {_ICON.get(r.severity, '⚪')} | {r.severity} | {r.category} | "
                         f"{loc} | {r.message[:180]} |")
        lines.append("")
        suggested = [r for r in rows if r.suggestion]
        if suggested:
            lines.append("<details><summary>Suggested fixes</summary>\n")
            for r in suggested[:10]:
                lines.append(f"**{r.file_path or 'general'}** — {r.suggestion}\n")
            lines.append("</details>\n")
    lines.append("---")
    lines.append("_Generated by your Agentic SDLC Reviewer Agent using this org's skills. "
                 "A human still approves before anything deploys._")
    return "\n".join(lines)
