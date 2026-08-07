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
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class MemoryChunk(Base):
    __tablename__ = "memory_chunks"
    __table_args__ = (
        Index("ix_memory_project_kind", "project_id", "kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))

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
