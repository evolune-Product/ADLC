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
from dataclasses import dataclass, field

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.billing import Subscription
from app.models.integration import ModelCredential
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


@dataclass
class WorkspaceCredential:
    """Which key, endpoint and rates to use for one model call."""
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    price_overrides: dict = field(default_factory=dict)

    @property
    def is_byo(self) -> bool:
        """True when the workspace supplied the credential, key or not — a
        local Ollama with no key is still their infrastructure, not ours, and
        must not be billed as platform spend."""
        return bool(self.provider or self.api_key)


def workspace_credential(db: Session, user_id, org_id, model: str | None = None) -> WorkspaceCredential:
    """
    The credential this workspace wants used for `model`.

    Looks in two places, newest first:

      1. `ModelCredential` rows — one per provider, which is what lets a team
         run Claude for the Dev agent and a local Ollama for QA in the same
         workspace.
      2. `Subscription.byo_llm_*` — the original single key. Still honoured so
         no existing workspace breaks on upgrade; nothing new writes to it.

    Returns an empty credential when neither exists, which sends the call to
    the platform key if this deployment has one configured.
    """
    provider = llm_service.provider_for_model(model or llm_service.DEFAULT_MODEL)

    cred = (
        db.query(ModelCredential)
        .filter(
            ModelCredential.provider == provider,
            ModelCredential.is_active.is_(True),
            ModelCredential.org_id == org_id if org_id
            else and_(ModelCredential.user_id == user_id, ModelCredential.org_id.is_(None)),
        )
        .first()
    )
    if cred:
        key = None
        if cred.api_key:
            try:
                key = decrypt_token(cred.api_key)
            except Exception:
                # A key that will not decrypt is a broken credential, not a
                # reason to silently fall back to the platform key and bill
                # this workspace for spend it thought was on its own account.
                log.warning("Could not decrypt model credential %s", cred.id)
                raise llm_service.LLMError(
                    f"The stored {provider} key could not be decrypted — re-enter it in Settings"
                )
        return WorkspaceCredential(
            provider=cred.provider,
            api_key=key,
            base_url=cred.base_url,
            price_overrides=cred.price_overrides or {},
        )

    q = db.query(Subscription)
    sub = (q.filter(Subscription.org_id == org_id).first() if org_id
           else q.filter(Subscription.user_id == user_id, Subscription.org_id.is_(None)).first())
    if not sub or not sub.byo_llm_key:
        return WorkspaceCredential()
    try:
        return WorkspaceCredential(provider=sub.byo_llm_provider,
                                   api_key=decrypt_token(sub.byo_llm_key))
    except Exception:
        log.warning("Could not decrypt BYO LLM key for subscription %s", getattr(sub, "id", None))
        return WorkspaceCredential()


def byo_llm(db: Session, user_id, org_id) -> tuple[str | None, str | None]:
    """Back-compat shim for callers that only need (provider, key)."""
    cred = workspace_credential(db, user_id, org_id)
    return cred.provider, cred.api_key


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
    image_base64: str | None = None, image_media_type: str = "image/png",
    user_id=None, org_id=None,
) -> llm_service.LLMResult:
    """
    One metered model call. Every token this platform spends flows through here.

    `run_id` resolves (user_id, org_id) for billing when the caller has a real
    SDLC `Run` row — every existing agent does. `simulation_agent.py` has no
    `Run` (a `SimulationRun` is a different table), so it passes `user_id`/
    `org_id` directly instead; `run_id` stays `None` for it and is never used
    to look anything up in that case.
    """
    if run_id is not None:
        user_id, org_id = run_owner(db, run_id)
    model = (agent.llm_model if agent and agent.llm_model else llm_service.DEFAULT_MODEL)
    # Resolved per model, not per workspace: an agent set to a local Ollama and
    # one set to Claude are two different credentials in the same workspace.
    cred = workspace_credential(db, user_id, org_id, model)

    result = llm_service.complete(
        system=system, user=user, model=model, max_tokens=max_tokens,
        tool=tool, byo_provider=cred.provider, byo_key=cred.api_key,
        byo_base_url=cred.base_url, price_overrides=cred.price_overrides,
        image_base64=image_base64, image_media_type=image_media_type,
    )

    metering_service.record_llm_call(
        db, user_id=user_id, org_id=org_id, run_id=run_id, agent_role=agent_role,
        model=result.model, provider=result.provider,
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        cost_millicents=result.cost_millicents,
        billable=not cred.is_byo,      # BYO spend is theirs, not ours
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


def read_sources(db: Session, *, run_id, agent_role: str, text: str,
                 limit: int = 3) -> str:
    """
    Read the URLs a ticket points at, and return them as a prompt block.

    A ticket that says "implement per the spec" and pastes a link used to give
    the agent a bare string. Fetching the raw page instead is not the fix — a
    typical page is ~800 kB of HTML wrapping ~8 kB of content, and this platform
    pays for every byte of that in tokens. So each URL goes through
    `reader_service`, which extracts the article and returns Markdown; on the
    docs pages this was tested against that is a ~90% token reduction.

    Every attempt is recorded as a `SourceRead` — successes *and* failures —
    because the run trace at the approval gate needs to show what the agent was
    actually working from. A page that turned out to be a bot wall is exactly
    the thing an approver should see before they approve a plan built on it.

    Failures are never fatal. If a link is dead, the agent plans without it and
    the row says so.
    """
    from app.models.insight import SourceRead
    from app.services import reader_service

    urls = reader_service.extract_urls(text or "", limit=limit)
    if not urls:
        return ""

    blocks: list[str] = []
    for url in urls:
        row = SourceRead(id=uuid.uuid4(), run_id=run_id, agent_role=agent_role, url=url)
        try:
            result = reader_service.read_url(url)
        except Exception as exc:                      # noqa: BLE001 — see docstring
            log.info("Source read failed for %s: %s", url, exc)
            row.status = "failed"
            row.error = str(exc)[:500]
            db.add(row)
            continue

        row.status = "ok"
        row.title = result.title[:500]
        row.read_score = result.read_score
        row.hallucination_risk = result.hallucination_risk
        row.html_bytes = result.html_bytes
        row.markdown_bytes = result.markdown_bytes
        row.tokens_before = result.tokens_before
        row.tokens_after = result.tokens_after
        row.flags = [f.as_dict() for f in result.flags]
        row.latency_ms = result.latency_ms
        row.cached = result.cached
        db.add(row)

        # The score travels with the content into the prompt, so the model is
        # told how much to trust what it is about to read rather than being
        # handed a degraded page as if it were the spec.
        caveat = ""
        if result.hallucination_risk != "low":
            caveat = (
                f"\n> This page did not read cleanly (score {result.read_score}/100). "
                "Treat details from it as unconfirmed, and say so in your plan "
                "rather than inventing specifics.\n"
            )
        blocks.append(
            f"### Source: {result.title}\n"
            f"<{result.url}>{caveat}\n"
            f"{result.markdown[:12000]}\n"
        )

    db.commit()

    if not blocks:
        return ""
    return "\n## Linked sources\n\n" + "\n---\n".join(blocks)
