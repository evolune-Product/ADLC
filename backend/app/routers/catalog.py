"""
Catalog router — the template library and the skill marketplace.

Two jobs:
  * cut time-to-first-run from hours to minutes (built-in skills/agents/pods)
  * create the network effect — published skills accrue installs and ratings,
    and an org with 40 installed skills has a real switching cost

Installing a template materialises a real Skill/Agent/Pod owned by the caller's
workspace; it is a copy, not a link, so upstream changes never mutate a
customer's agent behaviour without them choosing it.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.data.builtin_templates import all_templates
from app.database import get_db
from app.models.agent import Agent, AgentSkill
from app.models.catalog import MarketplaceInstall, MarketplaceListing, Template
from app.models.pod import Pod, PodAgent
from app.models.skill import Skill
from app.models.user import User
from app.routers._helpers import OrgContext, get_optional_org, owner_filter
from app.routers.auth import get_current_user

router = APIRouter()


class PublishBody(BaseModel):
    kind: str = Field(..., description="skill | agent | pod")
    resource_id: uuid.UUID
    visibility: str = "public"
    price_cents: int = 0
    readme_md: str | None = None


class RateBody(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


# ── Seeding ───────────────────────────────────────────────────────────────────

def ensure_builtins(db: Session) -> int:
    """Idempotently load the first-party library. Safe to call on every request."""
    existing = {t.slug for t in db.query(Template.slug).filter(Template.is_builtin.is_(True)).all()}
    created = 0
    for spec in all_templates():
        if spec["slug"] in existing:
            continue
        tpl = Template(is_builtin=True, version="1.0.0", **spec)
        db.add(tpl)
        db.flush()
        db.add(MarketplaceListing(
            template_id=tpl.id, publisher_name="Agentic SDLC",
            visibility="public", price_cents=0, is_verified=True,
            readme_md=spec["payload"].get("md_content"),
        ))
        created += 1
    if created:
        db.commit()
    return created


# ── Browse ────────────────────────────────────────────────────────────────────

def _template_out(t: Template, listing: MarketplaceListing | None = None) -> dict:
    listing = listing or t.listing
    return {
        "id": str(t.id),
        "slug": t.slug,
        "kind": t.kind,
        "name": t.name,
        "description": t.description,
        "category": t.category,
        "tags": t.tags or [],
        "version": t.version,
        "is_builtin": t.is_builtin,
        "payload": t.payload,
        "listing": {
            "id": str(listing.id),
            "publisher_name": listing.publisher_name,
            "visibility": listing.visibility,
            "price_cents": listing.price_cents,
            "install_count": listing.install_count,
            "rating": listing.rating,
            "rating_count": listing.rating_count,
            "is_verified": listing.is_verified,
            "readme_md": listing.readme_md,
        } if listing else None,
    }


@router.get("/templates")
def list_templates(
    kind: Optional[str] = Query(None, description="skill | agent | pod"),
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ensure_builtins(db)
    query = db.query(Template).filter(
        (Template.is_builtin.is_(True)) | owner_filter(Template, current_user, org_ctx))
    if kind:
        query = query.filter(Template.kind == kind)
    if category:
        query = query.filter(Template.category == category)
    rows = query.order_by(Template.is_builtin.desc(), Template.name).all()

    if q:
        needle = q.lower()
        rows = [t for t in rows
                if needle in (t.name or "").lower()
                or needle in (t.description or "").lower()
                or any(needle in tag.lower() for tag in (t.tags or []))]

    return {
        "templates": [_template_out(t) for t in rows],
        "categories": sorted({t.category for t in rows if t.category}),
    }


@router.get("/marketplace")
def browse_marketplace(
    kind: Optional[str] = Query(None),
    sort: str = Query("installs", description="installs | rating | newest"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Public listings. Browsing is intentionally light on auth so this page can
    become the top of the self-serve funnel."""
    ensure_builtins(db)
    q = (db.query(MarketplaceListing, Template)
         .join(Template, Template.id == MarketplaceListing.template_id)
         .filter(MarketplaceListing.visibility == "public"))
    if kind:
        q = q.filter(Template.kind == kind)
    rows = q.all()

    if sort == "rating":
        rows.sort(key=lambda pair: (pair[0].rating, pair[0].install_count), reverse=True)
    elif sort == "newest":
        rows.sort(key=lambda pair: pair[1].created_at or 0, reverse=True)
    else:
        rows.sort(key=lambda pair: pair[0].install_count, reverse=True)

    return [_template_out(t, listing) for listing, t in rows]


@router.get("/templates/{slug}")
def get_template(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_builtins(db)
    t = db.query(Template).filter(Template.slug == slug).first()
    if not t:
        raise HTTPException(404, "Template not found")
    return _template_out(t)


# ── Install ───────────────────────────────────────────────────────────────────

@router.post("/templates/{slug}/install", status_code=201)
def install_template(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Materialise a template into this workspace. Pods pull in their agents, and
    agents pull in their skills, so one click on 'Standard SDLC Pod' produces a
    runnable pipeline.
    """
    ensure_builtins(db)
    if org_ctx and org_ctx.role == "viewer":
        raise HTTPException(403, "Viewers cannot install templates")

    tpl = db.query(Template).filter(Template.slug == slug).first()
    if not tpl:
        raise HTTPException(404, "Template not found")

    org_id = org_ctx.org_id if org_ctx else None
    installer = {"skill": _install_skill, "agent": _install_agent, "pod": _install_pod}[tpl.kind]
    resource_id, name = installer(db, tpl, current_user.id, org_id)

    if tpl.listing:
        tpl.listing.install_count += 1
        existing = (
            db.query(MarketplaceInstall)
            .filter(MarketplaceInstall.listing_id == tpl.listing.id,
                    MarketplaceInstall.user_id == current_user.id,
                    MarketplaceInstall.org_id == org_id)
            .first()
        )
        if not existing:
            db.add(MarketplaceInstall(listing_id=tpl.listing.id, user_id=current_user.id,
                                      org_id=org_id, installed_resource_id=resource_id))
        db.commit()

    return {"kind": tpl.kind, "id": str(resource_id), "name": name,
            "message": f"{tpl.name} installed"}


def _install_skill(db: Session, tpl: Template, user_id, org_id) -> tuple[uuid.UUID, str]:
    existing = (
        db.query(Skill)
        .filter(Skill.name == tpl.name, Skill.user_id == user_id, Skill.org_id == org_id)
        .first()
    )
    if existing:
        return existing.id, existing.name
    skill = Skill(
        user_id=user_id, org_id=org_id, name=tpl.name,
        description=tpl.description, category=tpl.category,
        md_content=tpl.payload.get("md_content", ""), version=tpl.version,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill.id, skill.name


def _install_agent(db: Session, tpl: Template, user_id, org_id) -> tuple[uuid.UUID, str]:
    payload = tpl.payload or {}
    agent = Agent(
        user_id=user_id, org_id=org_id, name=tpl.name, role=payload.get("role", "dev"),
        description=tpl.description,
        llm_model=payload.get("llm_model", "claude-sonnet-4-6"),
        config=payload.get("config", {}),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    for priority, skill_slug in enumerate(payload.get("skills", [])):
        skill_tpl = db.query(Template).filter(Template.slug == skill_slug,
                                              Template.kind == "skill").first()
        if not skill_tpl:
            continue
        skill_id, _ = _install_skill(db, skill_tpl, user_id, org_id)
        db.add(AgentSkill(agent_id=agent.id, skill_id=skill_id, priority=priority))
    db.commit()
    return agent.id, agent.name


def _install_pod(db: Session, tpl: Template, user_id, org_id) -> tuple[uuid.UUID, str]:
    pod = Pod(user_id=user_id, org_id=org_id, name=tpl.name, description=tpl.description)
    db.add(pod)
    db.commit()
    db.refresh(pod)

    for slot in (tpl.payload or {}).get("agents", []):
        agent_tpl = db.query(Template).filter(Template.slug == slot["template_slug"],
                                              Template.kind == "agent").first()
        if not agent_tpl:
            continue
        agent_id, _ = _install_agent(db, agent_tpl, user_id, org_id)
        db.add(PodAgent(
            pod_id=pod.id, agent_id=agent_id,
            execution_order=slot.get("execution_order", 1),
            on_failure=slot.get("on_failure", "retry"),
            max_retries=slot.get("max_retries", 2),
        ))
    db.commit()
    return pod.id, pod.name


# ── Publish ───────────────────────────────────────────────────────────────────

@router.post("/marketplace/publish", status_code=201)
def publish(
    body: PublishBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Publish one of your own skills/agents/pods as a marketplace template."""
    if body.kind not in ("skill", "agent", "pod"):
        raise HTTPException(422, "kind must be skill, agent or pod")

    org_id = org_ctx.org_id if org_ctx else None
    payload: dict
    if body.kind == "skill":
        row = db.query(Skill).filter(Skill.id == body.resource_id,
                                     owner_filter(Skill, current_user, org_ctx)).first()
        if not row:
            raise HTTPException(404, "Skill not found")
        name, description, category = row.name, row.description, row.category
        payload = {"md_content": row.md_content, "category": row.category}
    elif body.kind == "agent":
        row = db.query(Agent).filter(Agent.id == body.resource_id,
                                     owner_filter(Agent, current_user, org_ctx)).first()
        if not row:
            raise HTTPException(404, "Agent not found")
        name, description, category = row.name, row.description, row.role
        payload = {"role": row.role, "llm_model": row.llm_model, "config": row.config,
                   "skills": [b.skill.name for b in row.agent_skills if b.skill]}
    else:
        row = db.query(Pod).filter(Pod.id == body.resource_id,
                                   owner_filter(Pod, current_user, org_ctx)).first()
        if not row:
            raise HTTPException(404, "Pod not found")
        name, description, category = row.name, row.description, "pod"
        payload = {"agents": [
            {"role": pa.agent.role if pa.agent else "dev",
             "template_slug": (pa.agent.name.lower().replace(" ", "-") if pa.agent else ""),
             "execution_order": pa.execution_order,
             "on_failure": pa.on_failure, "max_retries": pa.max_retries}
            for pa in row.pod_agents
        ]}

    slug_base = name.lower().replace(" ", "-")[:60]
    slug = slug_base
    n = 1
    while db.query(Template).filter(Template.slug == slug).first():
        n += 1
        slug = f"{slug_base}-{n}"

    tpl = Template(user_id=current_user.id, org_id=org_id, kind=body.kind, slug=slug,
                   name=name, description=description, category=category,
                   tags=[category] if category else [], payload=payload)
    db.add(tpl)
    db.flush()
    listing = MarketplaceListing(
        template_id=tpl.id, publisher_id=current_user.id,
        publisher_name=current_user.name or current_user.email,
        visibility=body.visibility, price_cents=body.price_cents,
        readme_md=body.readme_md,
    )
    db.add(listing)
    db.commit()
    db.refresh(tpl)
    return _template_out(tpl, listing)


@router.post("/marketplace/{listing_id}/rate")
def rate_listing(
    listing_id: uuid.UUID,
    body: RateBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Only installers may rate — otherwise the signal is worthless."""
    org_id = org_ctx.org_id if org_ctx else None
    install = (
        db.query(MarketplaceInstall)
        .filter(MarketplaceInstall.listing_id == listing_id,
                MarketplaceInstall.user_id == current_user.id,
                MarketplaceInstall.org_id == org_id)
        .first()
    )
    if not install:
        raise HTTPException(403, "Install this template before rating it")

    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(404, "Listing not found")

    if install.rating:                       # replace a previous rating
        listing.rating_sum -= install.rating
        listing.rating_count -= 1
    install.rating, install.review_comment = body.rating, body.comment
    listing.rating_sum += body.rating
    listing.rating_count += 1
    db.commit()
    return {"rating": listing.rating, "rating_count": listing.rating_count}


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def unpublish(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    tpl = db.query(Template).filter(Template.id == template_id,
                                    owner_filter(Template, current_user, org_ctx)).first()
    if not tpl or tpl.is_builtin:
        raise HTTPException(404, "Template not found")
    db.delete(tpl)
    db.commit()
