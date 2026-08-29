"""
Codebase memory — the deepest moat.

On project onboarding the repo is indexed into chunks with embeddings. Every
run retrieves the most relevant chunks and injects them into the agent prompt,
so agents stop starting cold. Merged PRs feed learnings back in as `decision`
chunks.

Embeddings are stored as a JSONB float array rather than requiring the pgvector
extension, so the platform installs on stock Postgres 15 (and on managed
providers that do not offer pgvector). Cosine similarity is computed in Python;
`memory_service.retrieve()` is the single place to swap in pgvector later.

Company OS step 14 — hierarchy
-------------------------------
Memory was originally keyed to exactly one Project. It now supports a
Company (org) > Department > Team > Project scope hierarchy: a chunk carries
`organization_id`, `department_id`, `team_id` and/or `project_id`, and
`project_id` is nullable so a chunk can live purely at the org/department/team
level (e.g. a company-wide onboarding doc has no project at all). Exactly one
of the four should be the chunk's *own* scope; `memory_service.retrieve_hierarchical`
is what walks broader scopes on top of a narrow one. `Task`-level memory is
deliberately not added here — there is no persistent Task entity in this
codebase for a chunk to key off (Ticket/Run are the closest analogues and
already have their own row types), so "Task" from the spec's hierarchy is
covered at the Project level; see ADLC_PROJECT_OVERVIEW.md for this session's
notes on the gap.
"""
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, String, Text, Integer, Boolean, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class MemoryChunk(Base):
    __tablename__ = "memory_chunks"
    __table_args__ = (
        Index("ix_memory_project_kind", "project_id", "kind"),
        Index("ix_memory_org", "organization_id"),
        Index("ix_memory_department", "department_id"),
        Index("ix_memory_team", "team_id"),
        CheckConstraint(
            "project_id IS NOT NULL OR department_id IS NOT NULL OR team_id IS NOT NULL OR organization_id IS NOT NULL",
            name="memory_chunks_scope_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable now — a chunk scoped at the org/department/team level has no
    # project at all. Existing project-scoped chunks are unaffected.
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    # Company (org)-level scope. Set on every chunk that has an org, project or
    # not, so a company-wide search never needs to join through Project/Team to
    # find its own tenant's rows.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=True
    )

    kind: Mapped[str] = mapped_column(String(30), default="file")   # file | structure | convention | decision | run_outcome
    path: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSONB, default=list)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    sha: Mapped[str | None] = mapped_column(String(64))
    source_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MemoryIndex(Base):
    """One row per project — tracks indexing status shown in the UI."""
    __tablename__ = "memory_indexes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")   # pending | indexing | ready | failed
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    auto_update: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
