"""
Shared plumbing for agent nodes.

Every agent needs the same four things: find its agent record in the pod, build a
system prompt from skills (+ codebase memory), call an LLM through the provider
abstraction while metering the spend, and write a RunStep. Keeping that here
means adding a fifth agent is a prompt and a tool schema, not another 80 lines
of boilerplate.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.billing import Subscription
from app.models.project import Project
from app.models.run import Run, RunStep
from app.services import llm_service, memory_service, metering_service
from app.services.encryption import decrypt_token
from app.services.notification_service import emit_run_event

log = logging.getLogger(__name__)


def find_agent(pod_agents: list, role: str, db: Session) -> Agent | None:
    for pa in pod_agents:
        if pa.get("agent_role") == role:
            agent = db.query(Agent).filter(Agent.id == pa["agent_id"]).first()
            if agent:
                return agent
    return None


def run_owner(db: Session, run_id) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """(user_id, org_id) for a run — the billing and notification target."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        return None, None
    project = db.query(Project).filter(Project.id == run.project_id).first()
    if not project:
        return run.triggered_by, None
    return project.user_id, project.org_id


def byo_llm(db: Session, user_id, org_id) -> tuple[str | None, str | None]:
    """Decrypted bring-your-own LLM credentials for this workspace, if any."""
    q = db.query(Subscription)
    sub = (q.filter(Subscription.org_id == org_id).first() if org_id
           else q.filter(Subscription.user_id == user_id, Subscription.org_id.is_(None)).first())
    if not sub or not sub.byo_llm_key:
        return None, None
    try:
        return sub.byo_llm_provider, decrypt_token(sub.byo_llm_key)
    except Exception:
        log.warning("Could not decrypt BYO LLM key for subscription %s", getattr(sub, "id", None))
        return None, None


def build_system_prompt(agent: Agent | None, project: dict, *, role_intro: str,
                        db: Session | None = None, memory_query: str | None = None) -> str:
    """
    Skills (ordered by priority) + project context + retrieved codebase memory.

    The memory block is what makes a run stop starting cold: after a project is
    indexed, the agent sees the parts of the repo that actually relate to the
    ticket, not just the ticket text.
    """
    parts = [role_intro, ""]

    if agent and agent.agent_skills:
        parts.append("## Your Skills\n")
        for binding in sorted(agent.agent_skills, key=lambda x: x.priority):
            skill = binding.skill
            if skill and skill.md_content:
                parts.append(f"### {skill.name}\n{skill.md_content}\n")

    if project.get("context_md"):
        parts.append(f"\n## Project Context\n{project['context_md']}\n")

    if db is not None and memory_query and project.get("id"):
        try:
            memory = memory_service.build_context(db, uuid.UUID(str(project["id"])), memory_query)
            if memory:
                parts.append("\n" + memory)
        except Exception:
            log.exception("Memory retrieval failed for project %s", project.get("id"))

    return "\n".join(parts)


def call_llm(
    db: Session, *, run_id, agent: Agent | None, agent_role: str,
    system: str, user: str, tool: dict | None = None, max_tokens: int = 8192,
) -> llm_service.LLMResult:
    """One metered model call. Every token this platform spends flows through here."""
    user_id, org_id = run_owner(db, run_id)
    provider, key = byo_llm(db, user_id, org_id)
    model = (agent.llm_model if agent and agent.llm_model else llm_service.DEFAULT_MODEL)

    result = llm_service.complete(
        system=system, user=user, model=model, max_tokens=max_tokens,
        tool=tool, byo_provider=provider, byo_key=key,
    )

    metering_service.record_llm_call(
        db, user_id=user_id, org_id=org_id, run_id=run_id, agent_role=agent_role,
        model=result.model, provider=result.provider,
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        cost_millicents=result.cost_millicents,
        billable=key is None,          # BYO-key spend is theirs, not ours
    )
    return result


def write_step(db: Session, run_id, agent_id, agent_role: str, step_name: str,
               status: str, input_: dict, output: dict, log_text: str | None,
               duration_ms: int) -> RunStep:
    step = RunStep(
        id=uuid.uuid4(), run_id=run_id, agent_id=agent_id, agent_role=agent_role,
        step_name=step_name, status=status, input=input_, output=output,
        log=log_text, duration_ms=duration_ms,
    )
    db.add(step)
    db.commit()
    return step


def start_step(run_id, step_name: str, agent_role: str, db: Session) -> None:
    emit_run_event(run_id, "run:step:started",
                   {"runId": str(run_id), "stepName": step_name, "agentRole": agent_role})
    run = db.query(Run).filter(Run.id == run_id).first()
    if run:
        run.current_step = f"{agent_role}:{step_name}"
        db.commit()
