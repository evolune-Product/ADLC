"""
Sprint Agent — reads ticket + skill MDs + project context, produces sprint plan.
"""
import time
import uuid
from datetime import datetime, timezone

import anthropic
from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent import Agent
from app.models.run import Run, RunStep
from app.models.skill import Skill
from app.services.notification_service import emit_run_event


def _find_agent(pod_agents: list, role: str, db: Session) -> Agent | None:
    for pa in pod_agents:
        if pa.get("agent_role") == role:
            agent = db.query(Agent).filter(Agent.id == pa["agent_id"]).first()
            if agent:
                return agent
    # fallback: first agent in pod
    if pod_agents:
        return db.query(Agent).filter(Agent.id == pod_agents[0]["agent_id"]).first()
    return None


def _build_system_prompt(agent: Agent, project: dict, ticket: dict) -> str:
    parts = ["You are an expert Sprint Planning Agent responsible for breaking down software tickets into clear, actionable implementation plans.\n"]

    # Inject skill MDs
    if agent.agent_skills:
        parts.append("## Your Skills & Context\n")
        for binding in sorted(agent.agent_skills, key=lambda x: x.priority):
            skill = binding.skill
            if skill and skill.md_content:
                parts.append(f"### {skill.name}\n{skill.md_content}\n")

    # Project context
    if project.get("context_md"):
        parts.append(f"\n## Project Context\n{project['context_md']}\n")

    parts.append(f"\n## Project: {project.get('name', 'Unknown')}")
    if project.get("repo_name"):
        parts.append(f"\nRepository: {project['repo_name']}")
    if project.get("type"):
        parts.append(f"\nType: {project['type']}")

    return "\n".join(parts)


def run_sprint_agent(state: dict, db: Session) -> dict:
    run_id = state["run_id"]
    project = state["project"]
    ticket = state["ticket"]
    pod_agents = state["pod_agents"]

    start_ms = int(time.time() * 1000)

    # Find sprint agent
    agent = _find_agent(pod_agents, "sprint", db)
    if not agent:
        error = "No sprint agent found in pod"
        _write_step(db, run_id, None, "sprint", "create_plan", "failed",
                    {}, {}, error, 0)
        return {**state, "status": "failed", "errors": state.get("errors", []) + [error]}

    emit_run_event(run_id, "run:step:started", {
        "runId": run_id, "stepName": "create_plan", "agentRole": "sprint"
    })

    # Update run current_step
    run = db.query(Run).filter(Run.id == run_id).first()
    if run:
        run.current_step = "sprint:create_plan"
        db.commit()

    # Build prompt
    system = _build_system_prompt(agent, project, ticket)
    user_msg = (
        f"Create a detailed sprint plan for this ticket:\n\n"
        f"**Ticket ID:** {ticket.get('jira_id', 'N/A')}\n"
        f"**Title:** {ticket.get('title', '')}\n"
        f"**Type:** {ticket.get('type', '')}\n"
        f"**Priority:** {ticket.get('priority', '')}\n"
        f"**Description:**\n{ticket.get('description', 'No description provided.')}\n\n"
        "Your sprint plan must include:\n"
        "1. Summary of what needs to be implemented\n"
        "2. List of files to create or modify (with full paths)\n"
        "3. Step-by-step implementation guide\n"
        "4. Edge cases and error handling to consider\n"
        "5. Suggested branch name (format: agent/{ticket_id}-{short-slug})\n\n"
        "Be specific and actionable. The Dev agent will implement exactly what you specify."
    )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=agent.llm_model or "claude-sonnet-4-6",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        sprint_plan = response.content[0].text
        duration_ms = int(time.time() * 1000) - start_ms

        emit_run_event(run_id, "run:step:log", {
            "runId": run_id, "stepName": "create_plan", "log": sprint_plan[:500] + "..."
        })

        _write_step(db, run_id, str(agent.id), "sprint", "create_plan", "success",
                    {"ticket": ticket}, {"sprint_plan": sprint_plan}, sprint_plan, duration_ms)

        emit_run_event(run_id, "run:step:completed", {
            "runId": run_id, "stepName": "create_plan", "status": "success"
        })

        return {**state, "sprint_plan": sprint_plan, "current_agent": "dev"}

    except Exception as e:
        duration_ms = int(time.time() * 1000) - start_ms
        error = f"Sprint agent error: {str(e)}"
        _write_step(db, run_id, str(agent.id) if agent else None, "sprint", "create_plan",
                    "failed", {}, {}, error, duration_ms)
        emit_run_event(run_id, "run:step:failed", {"runId": run_id, "stepName": "create_plan", "error": error})
        return {**state, "status": "failed", "errors": state.get("errors", []) + [error]}


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
