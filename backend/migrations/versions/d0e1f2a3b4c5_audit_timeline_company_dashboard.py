"""Company OS steps 19-20 — audit timeline org/department/team columns

Adds:
  - audit_logs: org_id / department_id / team_id (nullable, FK) — lets the
    unified `/audit` timeline filter server-side instead of the caller
    cross-referencing user_id against org membership per row. Populated going
    forward by AuditMiddleware (org_id, from X-Org-ID) and the new
    app/services/audit_service.py event-sourced writer (all three, at the
    call sites the HTTP middleware can't see: workflow execution status
    transitions, workflow-approval-policy decisions, real CompanyApi/
    ToolGrant usage). Every existing row stays valid with all three null.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("audit_logs", sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("audit_logs", sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_audit_logs_org_id", "audit_logs", "organizations", ["org_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_audit_logs_department_id", "audit_logs", "departments", ["department_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_audit_logs_team_id", "audit_logs", "teams", ["team_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_audit_logs_org", "audit_logs", ["org_id"])
    op.create_index("ix_audit_logs_department", "audit_logs", ["department_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_department", table_name="audit_logs")
    op.drop_index("ix_audit_logs_org", table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_team_id", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_audit_logs_department_id", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_audit_logs_org_id", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "team_id")
    op.drop_column("audit_logs", "department_id")
    op.drop_column("audit_logs", "org_id")
