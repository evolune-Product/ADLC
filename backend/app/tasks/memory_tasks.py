"""
Background tasks for codebase memory and periodic housekeeping.

Indexing a repo means hundreds of API calls and embedding requests — far too
slow for a request/response cycle, and exactly what the existing Celery worker
is for.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from celery_app import celery_app
from app.config import settings
from app.database import SessionLocal
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.services import memory_service

log = logging.getLogger(__name__)


@celery_app.task(name="memory_tasks.index_project", bind=True, max_retries=1)
def index_project_task(self, project_id: str, max_files: int = memory_service.MAX_FILES):
    db = SessionLocal()
    try:
        idx = memory_service.index_project(db, project_id, max_files=max_files)
        return {"status": idx.status, "chunks": idx.chunk_count, "files": idx.file_count}
    finally:
        db.close()


@celery_app.task(name="memory_tasks.prune_retention")
def prune_retention_task():
    """
    Data-retention enforcement. SOC 2 asks for a documented retention policy;
    a policy nobody executes is a finding, so this is the executor.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        removed = {}

        if settings.audit_retention_days:
            cutoff = now - timedelta(days=settings.audit_retention_days)
            removed["audit_logs"] = (
                db.query(AuditLog).filter(AuditLog.created_at < cutoff)
                .delete(synchronize_session=False)
            )

        # Read notifications older than 30 days are noise, not evidence.
        cutoff = now - timedelta(days=30)
        removed["notifications"] = (
            db.query(Notification)
            .filter(Notification.created_at < cutoff, Notification.read_at.isnot(None))
            .delete(synchronize_session=False)
        )

        db.commit()
        log.info("Retention prune removed: %s", removed)
        return removed
    finally:
        db.close()
