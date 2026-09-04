"""Approval policy conditions — monetary thresholds and risk-level escalation

Adds ApprovalPolicy.conditions (JSONB, default []). See
app/services/policy_service.py::resolve_condition_override for the field
vocabulary and evaluation. An empty list is the default for every existing
row, so this is additive-only — no existing policy's behaviour changes.

Revision ID: a2b3c4d5e6f7
Revises: f3338312ddf0
Create Date: 2026-09-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a2b3c4d5e6f7"
down_revision = "f3338312ddf0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "approval_policies",
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()),
                   nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("approval_policies", "conditions")
