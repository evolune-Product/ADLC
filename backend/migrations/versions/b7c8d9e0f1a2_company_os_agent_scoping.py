"""Company OS steps 10-12 — agent scoping, tool grants, BYO API registry

Adds:
  - agents.department_id / agents.team_id (nullable, additive — see
    app/models/agent.py module docstring)
  - tool_grants (default-open-until-scoped allow-listing for plugins and
    company APIs — see app/services/tool_grants.py)
  - company_apis / company_api_endpoints (the BYO API integration registry —
    see app/models/company_api.py)

Revision ID: b7c8d9e0f1a2
Revises: 5fb70203227c
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b7c8d9e0f1a2"
down_revision = "5fb70203227c"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    # ── step 10: agent department/team scoping ──────────────────────────
    op.add_column("agents", sa.Column("department_id", UUID, sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True))
    op.add_column("agents", sa.Column("team_id", UUID, sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_agents_department", "agents", ["department_id"])
    op.create_index("ix_agents_team", "agents", ["team_id"])

    # ── step 12: BYO API registry (created before tool_grants, which FKs it) ──
    op.create_table(
        "company_apis",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("base_url", sa.Text, nullable=False),
        sa.Column("auth_type", sa.String(20), nullable=False, server_default="none"),
        sa.Column("auth_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("default_headers", JSONB, nullable=True),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="20"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("auth_type IN ('none','api_key','bearer','basic','oauth2')", name="company_apis_auth_type_check"),
        sa.CheckConstraint("status IN ('active','disabled')", name="company_apis_status_check"),
    )
    op.create_index("ix_company_apis_org", "company_apis", ["organization_id"])

    op.create_table(
        "company_api_endpoints",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("company_api_id", UUID, sa.ForeignKey("company_apis.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("method", sa.String(10), nullable=False, server_default="GET"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("request_schema", JSONB, nullable=True),
        sa.Column("response_schema", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("method IN ('GET','POST','PUT','PATCH','DELETE')", name="company_api_endpoints_method_check"),
    )
    op.create_index("ix_company_api_endpoints_api", "company_api_endpoints", ["company_api_id"])

    # ── step 11: tool grants ─────────────────────────────────────────────
    op.create_table(
        "tool_grants",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plugin_key", sa.String(50), nullable=True),
        sa.Column("company_api_id", UUID, sa.ForeignKey("company_apis.id", ondelete="CASCADE"), nullable=True),
        sa.Column("grantee_type", sa.String(20), nullable=False),
        sa.Column("grantee_id", UUID, nullable=False),
        sa.Column("granted_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("grantee_type IN ('agent','department','team','workflow')", name="tool_grants_grantee_type_check"),
        sa.CheckConstraint(
            "(plugin_key IS NOT NULL AND company_api_id IS NULL) OR "
            "(plugin_key IS NULL AND company_api_id IS NOT NULL)",
            name="tool_grants_exactly_one_target_check",
        ),
        sa.UniqueConstraint(
            "organization_id", "plugin_key", "company_api_id", "grantee_type", "grantee_id",
            name="uq_tool_grant_target_grantee",
        ),
    )
    op.create_index("ix_tool_grants_org_plugin", "tool_grants", ["organization_id", "plugin_key"])
    op.create_index("ix_tool_grants_org_api", "tool_grants", ["organization_id", "company_api_id"])


def downgrade() -> None:
    op.drop_index("ix_tool_grants_org_api", table_name="tool_grants")
    op.drop_index("ix_tool_grants_org_plugin", table_name="tool_grants")
    op.drop_table("tool_grants")

    op.drop_index("ix_company_api_endpoints_api", table_name="company_api_endpoints")
    op.drop_table("company_api_endpoints")

    op.drop_index("ix_company_apis_org", table_name="company_apis")
    op.drop_table("company_apis")

    op.drop_index("ix_agents_team", table_name="agents")
    op.drop_index("ix_agents_department", table_name="agents")
    op.drop_column("agents", "team_id")
    op.drop_column("agents", "department_id")
