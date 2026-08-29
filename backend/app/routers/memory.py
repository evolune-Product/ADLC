"""
Codebase memory router — index a project, inspect what the agents know, and
search it the way a run would.

The "what do the agents know?" panel matters as much as the retrieval itself:
memory that a lead cannot inspect is memory they will not trust with a
production repo.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.department import Department
from app.models.memory import MemoryChunk, MemoryIndex
from app.models.project import Project
from app.models.user import User
from app.routers._helpers import OrgContext, can_write, get_optional_org, is_domain_admin, owner_filter
from app.routers.auth import get_current_user
from app.services import embedding_service, memory_service

router = APIRouter()


class SearchBody(BaseModel):
    query: str
    k: int = 6


class NoteBody(BaseModel):
    title: str
    content: str
    kind: str = "convention"


def _assert_project(db: Session, project_id: uuid.UUID, current_user: User,
                    org_ctx: Optional[OrgContext]) -> Project:
    p = db.query(Project).filter(Project.id == project_id,
                                 owner_filter(Project, current_user, org_ctx)).first()
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.get("/projects/{project_id}/memory")
def memory_status(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _assert_project(db, project_id, current_user, org_ctx)
    idx = memory_service.get_index(db, project_id)

    by_kind = {}
    for chunk in db.query(MemoryChunk.kind).filter(MemoryChunk.project_id == project_id).all():
        by_kind[chunk.kind] = by_kind.get(chunk.kind, 0) + 1

    return {
        "status": idx.status,
        "chunk_count": idx.chunk_count,
        "file_count": idx.file_count,
        "embedding_model": idx.embedding_model or embedding_service.model_name(),
        "embedding_backend": embedding_service.backend(),
        "auto_update": idx.auto_update,
        "last_indexed_at": idx.last_indexed_at.isoformat() if idx.last_indexed_at else None,
        "error": idx.error,
        "chunks_by_kind": by_kind,
    }


@router.post("/projects/{project_id}/memory/index", status_code=202)
def start_index(
    project_id: uuid.UUID,
    max_files: int = Query(memory_service.MAX_FILES, ge=10, le=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Kick off indexing in the background; falls back to inline on a broker outage."""
    _assert_project(db, project_id, current_user, org_ctx)
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(403, "Viewers cannot re-index project memory")

    idx = memory_service.get_index(db, project_id)
    idx.status = "indexing"
    idx.error = None
    db.commit()

    try:
        from app.tasks.memory_tasks import index_project_task
        index_project_task.delay(str(project_id), max_files)
        return {"status": "indexing", "queued": True}
    except Exception:
        result = memory_service.index_project(db, project_id, max_files=max_files)
        return {"status": result.status, "queued": False,
                "chunk_count": result.chunk_count, "error": result.error}


@router.post("/projects/{project_id}/memory/search")
def search_memory(
    project_id: uuid.UUID,
    body: SearchBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Exactly what an agent would retrieve for this text — no hidden ranking."""
    _assert_project(db, project_id, current_user, org_ctx)
    chunks = memory_service.retrieve(db, project_id, body.query, k=min(body.k, 20))
    return [
        {
            "id": str(c.id), "kind": c.kind, "path": c.path, "title": c.title,
            "tokens": c.tokens,
            "excerpt": c.content[:600] + ("…" if len(c.content) > 600 else ""),
        }
        for c in chunks
    ]


@router.get("/projects/{project_id}/memory/chunks")
def list_chunks(
    project_id: uuid.UUID,
    kind: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _assert_project(db, project_id, current_user, org_ctx)
    q = db.query(MemoryChunk).filter(MemoryChunk.project_id == project_id)
    if kind:
        q = q.filter(MemoryChunk.kind == kind)
    rows = q.order_by(MemoryChunk.updated_at.desc()).limit(limit).all()
    return [
        {"id": str(c.id), "kind": c.kind, "path": c.path, "title": c.title,
         "tokens": c.tokens,
         "updated_at": c.updated_at.isoformat() if c.updated_at else None}
        for c in rows
    ]


@router.post("/projects/{project_id}/memory/notes", status_code=201)
def add_note(
    project_id: uuid.UUID,
    body: NoteBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Teach the agents something the repo doesn't say — a convention, a gotcha, a
    decision. Human-authored memory outranks nothing, but it is retrievable the
    same way, which is how tacit team knowledge gets into agent runs at all.
    """
    _assert_project(db, project_id, current_user, org_ctx)
    chunk = memory_service.remember_outcome(
        db, project_id, run_id=None, title=body.title, content=body.content, kind=body.kind)
    return {"id": str(chunk.id), "kind": chunk.kind, "title": chunk.title}


@router.delete("/projects/{project_id}/memory", status_code=status.HTTP_204_NO_CONTENT)
def clear_memory(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    _assert_project(db, project_id, current_user, org_ctx)
    if org_ctx and not is_domain_admin(org_ctx, "engineering"):
        raise HTTPException(403, "Only owners and admins can clear project memory")
    db.query(MemoryChunk).filter(MemoryChunk.project_id == project_id).delete()
    idx = db.query(MemoryIndex).filter(MemoryIndex.project_id == project_id).first()
    if idx:
        idx.status, idx.chunk_count, idx.file_count = "pending", 0, 0
    db.commit()


# ── Company OS step 14: Company / Department knowledge ─────────────────────
#
# Mirrors the /projects/:id/memory/notes shape exactly (same NoteBody, same
# storage — a MemoryChunk row, same embedding call) one and two levels up the
# org chart, rather than inventing a second knowledge system. No new storage
# mechanism: like the project notes endpoint, this is DB-stored text with a
# JSONB embedding, not a document upload feature.

def _require_org(org_ctx: Optional[OrgContext]) -> OrgContext:
    if org_ctx is None:
        raise HTTPException(400, "This action requires an org context (X-Org-ID header)")
    return org_ctx


def _assert_department(db: Session, org_ctx: OrgContext, department_id: uuid.UUID) -> Department:
    dept = db.query(Department).filter(
        Department.id == department_id, Department.organization_id == org_ctx.org_id,
    ).first()
    if not dept:
        raise HTTPException(404, "Department not found")
    return dept


@router.post("/departments/{department_id}/knowledge/notes", status_code=201)
def add_department_note(
    department_id: uuid.UUID,
    body: NoteBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    if not can_write(ctx):
        raise HTTPException(403, "Read-only role cannot add department knowledge")
    _assert_department(db, ctx, department_id)
    chunk = memory_service.write_note(
        db, organization_id=ctx.org_id, department_id=department_id,
        title=body.title, content=body.content, kind=body.kind,
    )
    return {"id": str(chunk.id), "kind": chunk.kind, "title": chunk.title}


@router.get("/departments/{department_id}/knowledge/chunks")
def list_department_chunks(
    department_id: uuid.UUID,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    _assert_department(db, ctx, department_id)
    rows = (
        db.query(MemoryChunk)
        .filter(MemoryChunk.department_id == department_id)
        .order_by(MemoryChunk.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {"id": str(c.id), "kind": c.kind, "title": c.title, "tokens": c.tokens,
         "updated_at": c.updated_at.isoformat() if c.updated_at else None}
        for c in rows
    ]


@router.post("/departments/{department_id}/knowledge/search")
def search_department_knowledge(
    department_id: uuid.UUID,
    body: SearchBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Hierarchy-aware: also returns company-level chunks (never team/project ones)."""
    ctx = _require_org(org_ctx)
    _assert_department(db, ctx, department_id)
    chunks = memory_service.retrieve_hierarchical(
        db, organization_id=ctx.org_id, department_id=department_id,
        query=body.query, k=min(body.k, 20),
    )
    return [
        {"id": str(c.id), "kind": c.kind, "title": c.title, "scope": _scope_label(c),
         "excerpt": c.content[:600] + ("…" if len(c.content) > 600 else "")}
        for c in chunks
    ]


@router.post("/orgs/{org_id}/knowledge/notes", status_code=201)
def add_company_note(
    org_id: uuid.UUID,
    body: NoteBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ctx = _require_org(org_ctx)
    if str(ctx.org_id) != str(org_id):
        raise HTTPException(403, "X-Org-ID does not match the org in the URL")
    if not can_write(ctx):
        raise HTTPException(403, "Read-only role cannot add company knowledge")
    chunk = memory_service.write_note(
        db, organization_id=org_id, title=body.title, content=body.content, kind=body.kind,
    )
    return {"id": str(chunk.id), "kind": chunk.kind, "title": chunk.title}


@router.post("/orgs/{org_id}/knowledge/search")
def search_company_knowledge(
    org_id: uuid.UUID,
    body: SearchBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Company-wide search. Deliberately narrower-scope-blind: only chunks with
    no department/team/project of their own come back here — a company-wide
    search agent must never accidentally surface one team's private notes.
    """
    ctx = _require_org(org_ctx)
    if str(ctx.org_id) != str(org_id):
        raise HTTPException(403, "X-Org-ID does not match the org in the URL")
    chunks = memory_service.retrieve_hierarchical(db, organization_id=org_id, query=body.query, k=min(body.k, 20))
    return [
        {"id": str(c.id), "kind": c.kind, "title": c.title,
         "excerpt": c.content[:600] + ("…" if len(c.content) > 600 else "")}
        for c in chunks
    ]


def _scope_label(c: MemoryChunk) -> str:
    if c.project_id:
        return "project"
    if c.team_id:
        return "team"
    if c.department_id:
        return "department"
    return "company"
