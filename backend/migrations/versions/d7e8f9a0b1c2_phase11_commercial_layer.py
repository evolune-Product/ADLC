"""Phase 11 — commercial, governance and intelligence layer

Adds: subscriptions, usage_records, notifications, notification_settings,
approval_policies, api_keys, webhooks, webhook_deliveries, templates,
marketplace_listings, marketplace_installs, memory_chunks, memory_indexes,
review_findings, run_feedback, deployments.

Revision ID: d7e8f9a0b1c2
Revises: c1d2e3f4a5b6
Create Date: 2026-08-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d7e8f9a0b1c2"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    # ── Billing ───────────────────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("plan", sa.String(50), server_default="free"),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("seats", sa.Integer(), server_default="1"),
        sa.Column("included_runs", sa.Integer(), server_default="25"),
        sa.Column("overage_cents_per_run", sa.Integer(), server_default="0"),
        sa.Column("max_projects", sa.Integer(), server_default="1"),
        sa.Column("run_budget_cents", sa.Integer(), server_default="200"),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("stripe_subscription_id", sa.String(255)),
        sa.Column("stripe_price_id", sa.String(255)),
        sa.Column("byo_llm_provider", sa.String(50)),
        sa.Column("byo_llm_key", sa.Text()),
        sa.Column("current_period_start", sa.DateTime(timezone=True)),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_subscriptions_owner", "subscriptions", ["user_id", "org_id"])

    op.create_table(
        "usage_records",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("run_id", UUID, sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", sa.String(50), server_default="run"),
        sa.Column("agent_role", sa.String(50)),
        sa.Column("model", sa.String(100)),
        sa.Column("provider", sa.String(50)),
        sa.Column("input_tokens", sa.Integer(), server_default="0"),
        sa.Column("output_tokens", sa.Integer(), server_default="0"),
        sa.Column("cost_millicents", sa.Integer(), server_default="0"),
        sa.Column("quantity", sa.Integer(), server_default="1"),
        sa.Column("billable", sa.Boolean(), server_default=sa.true()),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_usage_owner_created", "usage_records", ["org_id", "user_id", "created_at"])
    op.create_index("ix_usage_run", "usage_records", ["run_id"])

    # ── Notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("type", sa.String(80)),
        sa.Column("title", sa.String(255)),
        sa.Column("body", sa.Text()),
        sa.Column("link", sa.Text()),
        sa.Column("severity", sa.String(20), server_default="info"),
        sa.Column("payload", JSONB, server_default="{}"),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "read_at"])

    op.create_table(
        "notification_settings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("email_enabled", sa.Boolean(), server_default=sa.true()),
        sa.Column("slack_enabled", sa.Boolean(), server_default=sa.false()),
        sa.Column("slack_webhook_url", sa.Text()),
        sa.Column("digest_enabled", sa.Boolean(), server_default=sa.true()),
        sa.Column("events", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Governance ────────────────────────────────────────────────────────────
    op.create_table(
        "approval_policies",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(255)),
        sa.Column("environment", sa.String(50), server_default="*"),
        sa.Column("min_approvers", sa.Integer(), server_default="1"),
        sa.Column("approver_roles", JSONB, server_default='["owner","admin","member"]'),
        sa.Column("require_review_pass", sa.Boolean(), server_default=sa.false()),
        sa.Column("min_review_score", sa.Integer(), server_default="0"),
        sa.Column("block_on_severity", sa.String(20)),
        sa.Column("auto_approve_below_risk", sa.Integer(), server_default="0"),
        sa.Column("protected_paths", JSONB, server_default="[]"),
        sa.Column("protected_branches", JSONB, server_default="[]"),
        sa.Column("max_files_changed", sa.Integer(), server_default="0"),
        sa.Column("max_run_cost_cents", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_policies_scope", "approval_policies", ["org_id", "project_id", "environment"])

    op.create_table(
        "api_keys",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(255)),
        sa.Column("prefix", sa.String(16)),
        sa.Column("hashed_key", sa.Text()),
        sa.Column("scopes", JSONB, server_default='["runs:read"]'),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"])
    op.create_index("ix_api_keys_hash", "api_keys", ["hashed_key"])

    op.create_table(
        "webhooks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("url", sa.Text()),
        sa.Column("secret", sa.String(64)),
        sa.Column("events", JSONB, server_default='["run.completed","run.failed","run.awaiting_approval"]'),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("failure_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("webhook_id", UUID, sa.ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event", sa.String(80)),
        sa.Column("payload", JSONB, server_default="{}"),
        sa.Column("status_code", sa.Integer()),
        sa.Column("ok", sa.Boolean(), server_default=sa.false()),
        sa.Column("error", sa.Text()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_webhook_deliveries_hook", "webhook_deliveries", ["webhook_id", "created_at"])

    # ── Catalog / marketplace ─────────────────────────────────────────────────
    op.create_table(
        "templates",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", sa.String(20)),
        sa.Column("slug", sa.String(160)),
        sa.Column("name", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(100)),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("version", sa.String(20), server_default="1.0.0"),
        sa.Column("payload", JSONB, server_default="{}"),
        sa.Column("is_builtin", sa.Boolean(), server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_templates_slug", "templates", ["slug"])
    op.create_index("ix_templates_kind_builtin", "templates", ["kind", "is_builtin"])

    op.create_table(
        "marketplace_listings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("template_id", UUID, sa.ForeignKey("templates.id", ondelete="CASCADE"),
                  unique=True, nullable=False),
        sa.Column("publisher_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("publisher_name", sa.String(255)),
        sa.Column("visibility", sa.String(20), server_default="public"),
        sa.Column("price_cents", sa.Integer(), server_default="0"),
        sa.Column("revenue_share_pct", sa.Integer(), server_default="70"),
        sa.Column("install_count", sa.Integer(), server_default="0"),
        sa.Column("rating_sum", sa.Integer(), server_default="0"),
        sa.Column("rating_count", sa.Integer(), server_default="0"),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.false()),
        sa.Column("readme_md", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "marketplace_installs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("listing_id", UUID, sa.ForeignKey("marketplace_listings.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("installed_resource_id", UUID),
        sa.Column("rating", sa.Integer()),
        sa.Column("review_comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("listing_id", "user_id", "org_id", name="uq_install_owner"),
    )

    # ── Memory ────────────────────────────────────────────────────────────────
    op.create_table(
        "memory_chunks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(30), server_default="file"),
        sa.Column("path", sa.Text()),
        sa.Column("title", sa.String(255)),
        sa.Column("content", sa.Text()),
        sa.Column("embedding", JSONB, server_default="[]"),
        sa.Column("tokens", sa.Integer(), server_default="0"),
        sa.Column("sha", sa.String(64)),
        sa.Column("source_run_id", UUID, sa.ForeignKey("runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_memory_project_kind", "memory_chunks", ["project_id", "kind"])

    op.create_table(
        "memory_indexes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"),
                  unique=True, nullable=False),
        sa.Column("status", sa.String(30), server_default="pending"),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("file_count", sa.Integer(), server_default="0"),
        sa.Column("embedding_model", sa.String(100)),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
        sa.Column("auto_update", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Insight ───────────────────────────────────────────────────────────────
    op.create_table(
        "review_findings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("run_id", UUID, sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", UUID, sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("severity", sa.String(20), server_default="info"),
        sa.Column("category", sa.String(50), server_default="quality"),
        sa.Column("file_path", sa.Text()),
        sa.Column("line", sa.Integer()),
        sa.Column("message", sa.Text()),
        sa.Column("suggestion", sa.Text()),
        sa.Column("posted_to_vcs", sa.Boolean(), server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_findings_run", "review_findings", ["run_id", "severity"])

    op.create_table(
        "run_feedback",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("run_id", UUID, sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_role", sa.String(50)),
        sa.Column("rating", sa.Integer(), server_default="0"),
        sa.Column("category", sa.String(50)),
        sa.Column("comment", sa.Text()),
        sa.Column("human_edits_loc", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_feedback_run", "run_feedback", ["run_id"])

    op.create_table(
        "deployments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("run_id", UUID, sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("environment", sa.String(50)),
        sa.Column("branch", sa.String(255)),
        sa.Column("sha", sa.String(64)),
        sa.Column("status", sa.String(30), server_default="succeeded"),
        sa.Column("approved_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approver_count", sa.Integer(), server_default="0"),
        sa.Column("policy_id", UUID, sa.ForeignKey("approval_policies.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("message", sa.Text()),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_deployments_project_env", "deployments",
                    ["project_id", "environment", "created_at"])


def downgrade() -> None:
    for table in [
        "deployments", "run_feedback", "review_findings",
        "memory_indexes", "memory_chunks",
        "marketplace_installs", "marketplace_listings", "templates",
        "webhook_deliveries", "webhooks", "api_keys", "approval_policies",
        "notification_settings", "notifications",
        "usage_records", "subscriptions",
    ]:
        op.drop_table(table)
