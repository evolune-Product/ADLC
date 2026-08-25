"""Workspace — channels, messages, threads, reactions, presence

Adds: channels, channel_members, messages, message_reactions, user_presence.

The collaboration layer. See app/models/workspace.py for why a chat surface
lives inside an SDLC platform at all.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "channels",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False, server_default="channel"),
        sa.Column("name", sa.String(120), nullable=True),
        sa.Column("slug", sa.String(120), nullable=True),
        sa.Column("topic", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("run_id", UUID, sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("ticket_id", UUID, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=True),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_preview", sa.String(280), nullable=True),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "kind IN ('channel','private','broadcast','dm','group_dm')",
            name="channels_kind_check",
        ),
    )
    # Partial: every DM carries a NULL slug and those must not collide.
    op.create_index("uq_channels_org_slug", "channels", ["org_id", "slug"],
                    unique=True, postgresql_where=sa.text("slug IS NOT NULL"))
    op.create_index("ix_channels_org_kind", "channels", ["org_id", "kind"])
    op.create_index("ix_channels_user", "channels", ["user_id"])

    op.create_table(
        "channel_members",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("channel_id", UUID, sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("agent_id", UUID, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("notify_level", sa.String(20), nullable=False, server_default="all"),
        sa.Column("is_muted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_starred", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unread_mentions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("channel_id", "user_id", name="uq_channel_member_user"),
        sa.UniqueConstraint("channel_id", "agent_id", name="uq_channel_member_agent"),
        sa.CheckConstraint("role IN ('owner','admin','member')", name="channel_members_role_check"),
        sa.CheckConstraint("notify_level IN ('all','mentions','none')", name="channel_members_notify_check"),
        # Exactly one principal per row — a human or an agent, never both.
        sa.CheckConstraint(
            "(user_id IS NOT NULL AND agent_id IS NULL) OR (user_id IS NULL AND agent_id IS NOT NULL)",
            name="channel_members_one_principal_check",
        ),
    )
    op.create_index("ix_channel_members_user", "channel_members", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("channel_id", UUID, sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", UUID, sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False, server_default="user"),
        sa.Column("author_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_id", UUID, sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("mentions", JSONB, nullable=False, server_default="{}"),
        sa.Column("attachments", JSONB, nullable=False, server_default="[]"),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("reply_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_reply_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "kind IN ('user','agent','system','approval_request')",
            name="messages_kind_check",
        ),
    )
    op.create_index("ix_messages_channel_created", "messages", ["channel_id", "created_at"])
    op.create_index("ix_messages_parent_created", "messages", ["parent_id", "created_at"])
    op.create_index("ix_messages_author", "messages", ["author_id"])

    op.create_table(
        "message_reactions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("message_id", UUID, sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("emoji", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("message_id", "user_id", "emoji", name="uq_reaction_once"),
    )
    op.create_index("ix_message_reactions_message", "message_reactions", ["message_id"])

    op.create_table(
        "user_presence",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("status_emoji", sa.String(32), nullable=True),
        sa.Column("status_text", sa.String(120), nullable=True),
        sa.Column("dnd_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "org_id", name="uq_presence_user_org"),
        sa.CheckConstraint("status IN ('active','away','dnd','offline')", name="user_presence_status_check"),
    )


def downgrade() -> None:
    op.drop_table("user_presence")
    op.drop_index("ix_message_reactions_message", table_name="message_reactions")
    op.drop_table("message_reactions")
    op.drop_index("ix_messages_author", table_name="messages")
    op.drop_index("ix_messages_parent_created", table_name="messages")
    op.drop_index("ix_messages_channel_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_channel_members_user", table_name="channel_members")
    op.drop_table("channel_members")
    op.drop_index("ix_channels_user", table_name="channels")
    op.drop_index("ix_channels_org_kind", table_name="channels")
    op.drop_index("uq_channels_org_slug", table_name="channels")
    op.drop_table("channels")
