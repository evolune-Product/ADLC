"""
Sprint Agent — turns a ticket into a file-level implementation plan.

Two things this node does that the others do not:

**It reads what the ticket points at.** Real tickets say "implement per the
spec" and paste a link — a Notion page, an RFC, a vendor's API docs. Until this
agent could open those, it was planning around a bare URL string. It now reads
them through `reader_service`, which extracts the article and hands over
Markdown instead of ~800 kB of page furniture, and records how well each read
went so the person at the approval gate can see what the plan was built from.

**It is metered.** This node used to call `anthropic.Anthropic()` directly,
which meant the first LLM call of every single run bypassed cost attribution,
BYO-key routing and the per-run budget cap entirely — a run could not be
stopped before its planning spend, and the spend never appeared on the bill.
Everything now goes through `_common.call_llm`, like every other agent.
"""
from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from app.agents._common import (build_system_prompt, call_llm, find_agent,
                                read_sources, start_step, write_step)
from app.models.agent import Agent
from app.services.notification_service import emit_run_event

log = logging.getLogger(__name__)

# Enough for a spec page or two without letting a link-heavy ticket dominate the
# context window — the ticket itself is still the brief.
MAX_SOURCES = 3

_ROLE_INTRO = (
    "You are an expert Sprint Planning Agent responsible for breaking down "
    "software tickets into clear, actionable implementation plans."
)


def run_sprint_agent(state: dict, db: Session) -> dict:
    run_id = state["run_id"]
    project = state["project"]
    ticket = state["ticket"]
    pod_agents = state["pod_agents"]

    start_ms = int(time.time() * 1000)

    agent = find_agent(pod_agents, "sprint", db)
    if not agent and pod_agents:
        # Falling back to the pod's first agent keeps a single-agent pod
        # working; a pod with no agents at all is a configuration error.
        agent = db.query(Agent).filter(Agent.id == pod_agents[0]["agent_id"]).first()
    if not agent:
        error = "No sprint agent found in pod"
        write_step(db, run_id, None, "sprint", "create_plan", "failed", {}, {}, error, 0)
        return {**state, "status": "failed", "errors": state.get("errors", []) + [error]}

    start_step(run_id, "create_plan", "sprint", db)

    title = ticket.get("title", "")
    description = ticket.get("description") or "No description provided."

    system = build_system_prompt(
        agent, project, role_intro=_ROLE_INTRO, db=db,
        memory_query=f"{title}\n{description}",
    )

    # Read before prompting, so the sources are context rather than something
    # the model is told to imagine. Never fatal: a dead link costs the plan one
    # source and leaves a row saying why.
    sources = read_sources(
        db, run_id=run_id, agent_role="sprint",
        text=f"{description}\n{project.get('context_md') or ''}",
        limit=MAX_SOURCES,
    )
    if sources:
        system = f"{system}\n{sources}"

    user_msg = (
        f"Create a detailed sprint plan for this ticket:\n\n"
        f"**Ticket ID:** {ticket.get('jira_id', 'N/A')}\n"
        f"**Title:** {title}\n"
        f"**Type:** {ticket.get('type', '')}\n"
        f"**Priority:** {ticket.get('priority', '')}\n"
        f"**Description:**\n{description}\n\n"
        "Your sprint plan must include:\n"
        "1. Summary of what needs to be implemented\n"
        "2. List of files to create or modify (with full paths)\n"
        "3. Step-by-step implementation guide\n"
        "4. Edge cases and error handling to consider\n"
        "5. Suggested branch name (format: agent/{ticket_id}-{short-slug})\n\n"
        "Be specific and actionable. The Dev agent will implement exactly what you specify.\n"
        "If a linked source could not be read cleanly, plan around the gap and say so "
        "explicitly — do not invent the detail it would have contained."
    )

    try:
        result = call_llm(
            db, run_id=run_id, agent=agent, agent_role="sprint",
            system=system, user=user_msg, max_tokens=4096,
        )
        sprint_plan = result.text
        duration_ms = int(time.time() * 1000) - start_ms

        emit_run_event(run_id, "run:step:log", {
            "runId": str(run_id), "stepName": "create_plan",
            "log": sprint_plan[:500] + "...",
        })

        write_step(db, run_id, str(agent.id), "sprint", "create_plan", "success",
                   {"ticket": ticket}, {"sprint_plan": sprint_plan}, sprint_plan, duration_ms)

        emit_run_event(run_id, "run:step:completed", {
            "runId": str(run_id), "stepName": "create_plan", "status": "success",
        })

        return {**state, "sprint_plan": sprint_plan, "current_agent": "dev"}

    except Exception as e:
        duration_ms = int(time.time() * 1000) - start_ms
        error = f"Sprint agent error: {str(e)}"
        log.exception("Sprint agent failed for run %s", run_id)
        write_step(db, run_id, str(agent.id) if agent else None, "sprint", "create_plan",
                   "failed", {}, {}, error, duration_ms)
        emit_run_event(run_id, "run:step:failed",
                       {"runId": str(run_id), "stepName": "create_plan", "error": error})
        return {**state, "status": "failed", "errors": state.get("errors", []) + [error]}
