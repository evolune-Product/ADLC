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
