"""
Event-sourced audit writer — Company OS step 19.

`AuditMiddleware` already logs every successful HTTP mutation, mapped from
the URL path. That covers "a person clicked something". It cannot see what
happens *inside* a request: a workflow execution walking through several
node types over one `advance()` call, a policy decision inside
`evaluate_workflow_approval`, or a real (not merely checked) tool
invocation. Those call sites use `record()` directly so the row lands in the
same `audit_logs` table the middleware already writes to — one table, one
query surface, not a parallel audit mechanism.

`record()` is best-effort by the same convention every other audit/narration
call in this codebase follows (see `workflow_engine._narrate`,
`writeback_service._emit`): a failure to write an audit row must never fail
the business action it is describing. It commits on the caller's session
rather than opening a new one, because these call sites are already deep
inside a unit of work that commits shortly after — opening a second
connection here would just be a second round trip for the same durability
guarantee.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog

log = logging.getLogger(__name__)


def record(
    db: Session,
    *,
    action: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | str | None = None,
    user_id: uuid.UUID | str | None = None,
    org_id: uuid.UUID | str | None = None,
    department_id: uuid.UUID | str | None = None,
    team_id: uuid.UUID | str | None = None,
    metadata: dict | None = None,
) -> None:
    try:
        db.add(AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            org_id=org_id,
            department_id=department_id,
            team_id=team_id,
            metadata_=metadata or {},
        ))
        db.commit()
    except Exception:
        log.debug("Event-sourced audit write failed (non-fatal): action=%s", action, exc_info=True)
        db.rollback()
