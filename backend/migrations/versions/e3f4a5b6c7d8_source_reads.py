"""Source reads — external URLs an agent read while planning, and how well

Adds: source_reads.

Revision ID: e3f4a5b6c7d8
Revises: d7e8f9a0b1c2
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e3f4a5b6c7d8"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "source_reads",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("run_id", UUID, sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_role", sa.String(50), nullable=True),

        sa.Column("url", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ok"),
        sa.Column("error", sa.Text, nullable=True),

        # Null when the read failed — there is no score for a page we never got.
        sa.Column("read_score", sa.Integer, nullable=True),
        sa.Column("hallucination_risk", sa.String(10), nullable=True),

        sa.Column("html_bytes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("markdown_bytes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_before", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_after", sa.Integer, nullable=False, server_default="0"),

        sa.Column("flags", JSONB, nullable=False, server_default="[]"),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cached", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Read back per run, oldest first — the only access pattern there is.
    op.create_index("ix_source_reads_run", "source_reads", ["run_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_source_reads_run", table_name="source_reads")
    op.drop_table("source_reads")
