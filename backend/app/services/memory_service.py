"""
Codebase memory — the deepest moat in the roadmap.

Every competitor's agent starts each task cold. After a project is indexed here,
each run retrieves the chunks most relevant to *this* ticket and injects them
into the agent prompt; merged PRs and run outcomes are written back as
`decision` and `run_outcome` chunks. Six months in, the org's memory is worth
more than the tool, and none of it is portable to a competitor.

Indexing walks the repo tree via the existing VCS connection, keeps
source-shaped files under a size cap, chunks them, embeds them, and records
per-project status for the UI.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.connection import Connection
from app.models.memory import MemoryChunk, MemoryIndex
from app.models.project import Project
from app.services import embedding_service
from app.services.encryption import decrypt_token

log = logging.getLogger(__name__)

CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rb", ".java", ".kt", ".rs",
    ".php", ".cs", ".swift", ".c", ".cc", ".cpp", ".h", ".hpp", ".sql",
    ".sh", ".yml", ".yaml", ".toml", ".json", ".md", ".vue", ".svelte",
}
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "vendor", "__pycache__", ".venv",
    "venv", "target", ".next", ".nuxt", "coverage", "migrations", ".terraform",
}
MAX_FILES = 400
MAX_FILE_BYTES = 120_000
CHUNK_CHARS = 2_400
CHUNK_OVERLAP = 200


# ── Status ────────────────────────────────────────────────────────────────────

def get_index(db: Session, project_id: uuid.UUID) -> MemoryIndex:
    idx = db.query(MemoryIndex).filter(MemoryIndex.project_id == project_id).first()
    if not idx:
        idx = MemoryIndex(project_id=project_id, status="pending")
        db.add(idx)
        db.commit()
        db.refresh(idx)
    return idx


# ── Indexing ──────────────────────────────────────────────────────────────────

def index_project(db: Session, project_id: uuid.UUID, *, max_files: int = MAX_FILES) -> MemoryIndex:
    """Full re-index. Safe to re-run: existing file chunks are replaced."""
    idx = get_index(db, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        idx.status, idx.error = "failed", "Project not found"
        db.commit()
        return idx

    idx.status, idx.error = "indexing", None
    db.commit()

    try:
        files = _fetch_repo_files(db, project, max_files)
        if not files:
            raise ValueError("No readable source files found in the repository")

        db.query(MemoryChunk).filter(
            MemoryChunk.project_id == project_id,
            MemoryChunk.kind.in_(["file", "structure"]),
        ).delete(synchronize_session=False)
        db.commit()

        # A structure chunk lets an agent answer "where does X live?" without
        # retrieving every file.
        tree = "\n".join(sorted(p for p, _ in files))
        _add_chunks(db, project_id, [(
            "structure", None, f"{project.name} — repository structure",
            f"Repository: {project.repo_name}\nFiles:\n{tree}",
        )])

        batch: list[tuple[str, str | None, str, str]] = []
        chunk_count = 0
        for path, content in files:
            for i, piece in enumerate(_chunk(content)):
                batch.append(("file", path, f"{path} (part {i + 1})", piece))
                if len(batch) >= 32:
                    chunk_count += _add_chunks(db, project_id, batch)
                    batch = []
        if batch:
            chunk_count += _add_chunks(db, project_id, batch)

        idx.status = "ready"
        idx.chunk_count = db.query(MemoryChunk).filter(MemoryChunk.project_id == project_id).count()
        idx.file_count = len(files)
        idx.embedding_model = embedding_service.model_name()
        idx.last_indexed_at = datetime.now(timezone.utc)
        idx.error = None
        db.commit()
        log.info("Indexed project %s: %s files, %s chunks", project_id, len(files), chunk_count)
    except Exception as exc:
        log.exception("Memory indexing failed for project %s", project_id)
        idx.status, idx.error = "failed", str(exc)[:500]
        db.commit()

    db.refresh(idx)
    return idx


def _fetch_repo_files(db: Session, project: Project, max_files: int) -> list[tuple[str, str]]:
    if not project.repo_connection_id or not project.repo_name:
        raise ValueError("Project has no repository connection configured")

    conn = db.query(Connection).filter(Connection.id == project.repo_connection_id).first()
    if not conn or not conn.access_token:
        raise ValueError("Repository connection is missing or has no token")

    token = decrypt_token(conn.access_token)

    if (conn.type or "github").lower() == "gitlab":
        from app.services.gitlab_service import GitLabClient
        return GitLabClient(token, conn.workspace_url).read_source_files(
            project.repo_name, max_files=max_files,
            extensions=CODE_EXTENSIONS, skip_dirs=SKIP_DIRS, max_bytes=MAX_FILE_BYTES,
        )

    from github import Github
    repo = Github(token).get_repo(project.repo_name)
    default_branch = repo.default_branch
    tree = repo.get_git_tree(default_branch, recursive=True)

    out: list[tuple[str, str]] = []
    for element in tree.tree:
        if len(out) >= max_files:
            break
        if element.type != "blob":
            continue
        path = element.path
        if any(part in SKIP_DIRS for part in path.split("/")):
            continue
        if not any(path.endswith(ext) for ext in CODE_EXTENSIONS):
            continue
        if (element.size or 0) > MAX_FILE_BYTES:
            continue
        try:
            blob = repo.get_contents(path, ref=default_branch)
            text = blob.decoded_content.decode("utf-8", errors="ignore")
            if text.strip():
                out.append((path, text))
        except Exception:
            continue
    return out


def _chunk(text: str) -> list[str]:
    if len(text) <= CHUNK_CHARS:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        end = start + CHUNK_CHARS
        # prefer a line boundary so functions aren't split mid-statement
        if end < len(text):
            nl = text.rfind("\n", start + CHUNK_CHARS // 2, end)
            if nl != -1:
                end = nl
        chunks.append(text[start:end])
        start = max(end - CHUNK_OVERLAP, end)
    return chunks


def _add_chunks(db: Session, project_id: uuid.UUID, items: list[tuple[str, str | None, str, str]]) -> int:
    vectors = embedding_service.embed_batch([content for _, _, _, content in items])
    for (kind, path, title, content), vec in zip(items, vectors):
        db.add(MemoryChunk(
            project_id=project_id, kind=kind, path=path, title=title,
            content=content, embedding=vec, tokens=max(1, len(content) // 4),
        ))
    db.commit()
    return len(items)


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(db: Session, project_id: uuid.UUID, query: str, *, k: int = 6,
             max_chars: int = 9000) -> list[MemoryChunk]:
    """
    Top-k chunks by cosine similarity.

    Scoring happens in Python against JSONB vectors — correct and dependency
    free at the scale one project's index reaches (hundreds to low thousands of
    chunks). This function is the single seam to swap for a pgvector
    `ORDER BY embedding <=> :q LIMIT k` when a customer's repo outgrows it.
    """
    chunks = db.query(MemoryChunk).filter(MemoryChunk.project_id == project_id).all()
    if not chunks:
        return []

    qvec = embedding_service.embed(query)
    scored = sorted(
        ((embedding_service.cosine(qvec, c.embedding or []), c) for c in chunks),
        key=lambda pair: pair[0],
        reverse=True,
    )

    picked, used = [], 0
    for score, chunk in scored:
        if score <= 0:
            break
        if used + len(chunk.content) > max_chars:
            continue
        picked.append(chunk)
        used += len(chunk.content)
        if len(picked) >= k:
            break
    return picked


def build_context(db: Session, project_id: uuid.UUID, query: str, *, k: int = 6) -> str:
    """Prompt-ready block. Empty string when the project has no memory yet."""
    chunks = retrieve(db, project_id, query, k=k)
    if not chunks:
        return ""
    parts = ["## Codebase memory (retrieved for this ticket)\n"]
    for c in chunks:
        header = c.path or c.title or c.kind
        parts.append(f"### {header}\n```\n{c.content}\n```\n")
    return "\n".join(parts)


# ── Write-back: the platform learns from what humans approved ─────────────────

def remember_outcome(db: Session, project_id: uuid.UUID, *, run_id, title: str, content: str,
                     kind: str = "run_outcome") -> MemoryChunk:
    vec = embedding_service.embed(f"{title}\n{content}")
    chunk = MemoryChunk(
        project_id=project_id, kind=kind, title=title, content=content,
        embedding=vec, tokens=max(1, len(content) // 4), source_run_id=run_id,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk
