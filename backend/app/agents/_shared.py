"""
Shared helpers used by all four agent modules.

Eliminates the duplicated _write_step / _find_agent functions that were
copy-pasted across sprint_agent.py, dev_agent.py, qa_agent.py, devops_agent.py.
"""
from __future__ import annotations

import uuid
import anthropic

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.run import RunStep
from app.models.user import User
from app.models.organization import Organization
from app.services.encryption import decrypt_token
from app.config import settings


def write_run_step(
    db: Session,
    run_id: str,
    agent_id: str | None,
    agent_role: str,
    step_name: str,
    status: str,
    input_: dict,
    output: dict,
    log_text: str | None,
    duration_ms: int,
) -> RunStep:
    """Create and persist a RunStep record. Returns the new step."""
    step = RunStep(
        id=uuid.uuid4(),
        run_id=run_id,
        agent_id=agent_id,
        agent_role=agent_role,
        step_name=step_name,
        status=status,
        input=input_,
        output=output,
        log=log_text,
        duration_ms=duration_ms,
    )
    db.add(step)
    db.commit()
    return step


def find_agent_by_role(pod_agents: list, role: str, db: Session) -> Agent | None:
    """
    Find the first agent in pod_agents whose agent_role matches `role`.
    Returns None if no match — callers decide whether that is a hard error.
    """
    for pa in pod_agents:
        if pa.get("agent_role") == role:
            agent = db.query(Agent).filter(Agent.id == pa["agent_id"]).first()
            if agent:
                return agent
    return None


def get_llm_client(user: User, org_id: str | None, db: Session) -> anthropic.Anthropic:
    """
    Get LLM client using user or org config (BYOK model).

    Priority:
    1. If org_id provided, use org's LLM config
    2. Otherwise use user's personal LLM config
    3. Fallback to global platform config

    Args:
        user: Current user
        org_id: Organization ID if in org context
        db: Database session

    Returns:
        Anthropic client instance
    """
    api_key = None

    # Try org config first if in org context
    if org_id:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if org and org.llm_api_key_encrypted:
            api_key = decrypt_token(org.llm_api_key_encrypted)

    # Fallback to user's personal config
    if not api_key and user.llm_api_key_encrypted:
        api_key = decrypt_token(user.llm_api_key_encrypted)

    # Final fallback to global platform config
    if not api_key:
        api_key = settings.anthropic_api_key

    # Create and return client
    return anthropic.Anthropic(api_key=api_key)
