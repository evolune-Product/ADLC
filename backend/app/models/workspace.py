"""
Workspace — channels, messages, threads and presence.

Why a chat surface belongs in an SDLC platform at all
-----------------------------------------------------
Every team running this product already coordinates somewhere else: a WhatsApp
group in India, a Slack workspace elsewhere, a Teams channel in the enterprise.
That split is not a cosmetic annoyance. It is where the audit trail dies. A
deploy gets approved in a WhatsApp thread at 11pm, the approval is typed into
the platform an hour later by someone else, and the compliance export now says
something that did not happen. The whole pitch of this codebase is that the
governed path is the only path; a chat tool the platform cannot see is a
parallel ungoverned path.

So the conversation moves in, and it brings three things the general-purpose
tools structurally cannot have:

  1. **Agents are members, not webhooks.** A Slack bot posts *about* a run.
     Here an @mention of an agent in a channel starts one, because the agent
     row and the channel member row point at the same platform.
  2. **Every run and ticket has a thread by construction.** Not "someone
     remembered to paste the PR link" — the thread is created with the run and
     carries its step events as messages.
  3. **Approvals happen in the conversation and stay auditable.** An
     `approval_request` message is a real approval gate rendered as chat, not a
     link out to one. The AuditLog row is written either way.

Shape notes
-----------
*Channels* carry a `kind`. `channel` and `private` are the Slack shape;
`broadcast` is the WhatsApp-Channel shape (admins post, everyone reads) which
is what announcement groups are actually used for; `dm` and `group_dm` are
member-derived and never named by a human.

*Threads* are self-referential on Message (`parent_id`) rather than a separate
Thread table. A thread is a property of the message that started it, and
denormalising `reply_count`/`last_reply_at` onto the parent is what keeps the
channel list query from needing a correlated subquery per row.

*Read state* is a high-water mark per (channel, user), not a per-message
receipt table. A receipt table on a busy channel is members × messages rows to
answer one question — "how many unread" — that a single timestamp answers.

*Presence* is deliberately a DB row and not Redis-only. Redis holds the live
socket state; this row is what an offline client reads on first paint so the
member list is not blank for a second on every load.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Channel kinds. Kept as a module constant because the router, the service and
# the migration's CheckConstraint all need the same list and three copies drift.
CHANNEL_KINDS = ("channel", "private", "broadcast", "dm", "group_dm")

# Message kinds. `system` is platform narration (a run started, a member
# joined); `agent` is an agent speaking; `approval_request` renders as a gate
# with buttons rather than a bubble.
MESSAGE_KINDS = ("user", "agent", "system", "approval_request")


class Channel(Base):
    __tablename__ = "channels"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('channel','private','broadcast','dm','group_dm')",
            name="channels_kind_check",
        ),
        # Slugs are unique per workspace, but only for the kinds humans name.
        # Every DM has a NULL slug, and NULLs must not collide with each other —
        # which is what the partial predicate buys us. (In Postgres NULLs are
        # already distinct in a unique index; the predicate keeps the index
        # small and states the intent rather than relying on that.)
        Index(
            "uq_channels_org_slug",
            "org_id", "slug",
            unique=True,
            postgresql_where=text("slug IS NOT NULL"),
        ),
        Index("ix_channels_org_kind", "org_id", "kind"),
        Index("ix_channels_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Same dual-ownership shape as every other resource in this codebase:
    # org_id set = org workspace, org_id NULL + user_id = personal workspace.
    # `owner_filter` in routers/_helpers.py is what reads this pair.
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )

    kind: Mapped[str] = mapped_column(String(20), default="channel")
    name: Mapped[str | None] = mapped_column(String(120))          # NULL for dm / group_dm
    slug: Mapped[str | None] = mapped_column(String(120))          # url-safe, NULL for dm / group_dm
    topic: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)

    # What this channel is *about*, when it is about something. A project
    # channel gets run events for that project; a run thread channel is scoped
    # to one run. Both nullable — a plain #general is about nothing.
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=True
    )
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=True
    )

    # A default channel is auto-joined by every new member of the workspace.
    # #general and #deploys are created with the org for exactly this reason —
    # an empty chat surface on first login is why teams never leave WhatsApp.
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Denormalised so the channel sidebar renders in one query. Maintained by
    # workspace_service.post_message, never by hand.
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_message_preview: Mapped[str | None] = mapped_column(String(280))
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    members = relationship("ChannelMember", back_populates="channel", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="channel", cascade="all, delete-orphan")


class ChannelMember(Base):
    """
    Membership, and the per-member read/notification state that hangs off it.

    An agent member has `agent_id` set and `user_id` NULL. Keeping both on one
    table (rather than a separate ChannelAgent) is what lets the member list,
    the mention autocomplete and the @-resolution treat humans and agents
    identically — which is the entire point of agents being first-class here.
    """
    __tablename__ = "channel_members"
    __table_args__ = (
        UniqueConstraint("channel_id", "user_id", name="uq_channel_member_user"),
        UniqueConstraint("channel_id", "agent_id", name="uq_channel_member_agent"),
        CheckConstraint("role IN ('owner','admin','member')", name="channel_members_role_check"),
        # Exactly one of user_id / agent_id. A row that is neither is a ghost
        # member; a row that is both is ambiguous at mention-resolution time.
        CheckConstraint(
            "(user_id IS NOT NULL AND agent_id IS NULL) OR (user_id IS NULL AND agent_id IS NOT NULL)",
            name="channel_members_one_principal_check",
        ),
        CheckConstraint(
            "notify_level IN ('all','mentions','none')",
            name="channel_members_notify_check",
        ),
        Index("ix_channel_members_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=True
    )

    role: Mapped[str] = mapped_column(String(20), default="member")
    # 'all' | 'mentions' | 'none' — the setting that decides whether a message
    # here is allowed to reach someone's phone at 2am. WhatsApp's mute is the
    # single most-used feature of a work group; not having it is not an option.
    notify_level: Mapped[str] = mapped_column(String(20), default="all")
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)

    # Read high-water mark. `last_read_at` answers "how many unread"; the
    # separate mention counter exists because an unread count of 400 and an
    # unread count of 400-with-one-@you are different urgencies.
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unread_mentions: Mapped[int] = mapped_column(Integer, default=0)

    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    channel = relationship("Channel", back_populates="members")
    user = relationship("User")
    agent = relationship("Agent")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('user','agent','system','approval_request')",
            name="messages_kind_check",
        ),
        # The channel scroll: newest-first within a channel, top-level only.
        Index("ix_messages_channel_created", "channel_id", "created_at"),
        # The thread scroll.
        Index("ix_messages_parent_created", "parent_id", "created_at"),
        Index("ix_messages_author", "author_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"))

    # A reply. NULL means top-level. Self-referential rather than a Thread
    # table — see the module docstring.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True
    )

    kind: Mapped[str] = mapped_column(String(20), default="user")
    # Author is NULL for `system`. For `agent` the agent_id is set instead —
    # same two-principal shape as ChannelMember, for the same reason.
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )

    body: Mapped[str] = mapped_column(Text, default="")
    # Parsed at write time, not read time: user ids, agent ids, and whether
    # this was an @channel. Resolving mentions on every render would mean
    # re-parsing every message body on every scroll.
    mentions: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Files, images, PR links, run cards. A list of {type, url, name, size, meta}.
    attachments: Mapped[list] = mapped_column(JSONB, default=list)
    # Kind-specific payload: run_id + step for `system`, the approval decision
    # state for `approval_request`, the slash command result for `agent`.
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Denormalised thread state, maintained on the parent when a reply lands.
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reply_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    # Soft delete. A hard DELETE on a message that a compliance export already
    # referenced turns that export into a lie; the body is blanked, the row stays.
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    channel = relationship("Channel", back_populates="messages")
    author = relationship("User", foreign_keys=[author_id])
    agent = relationship("Agent", foreign_keys=[agent_id])
    parent = relationship("Message", remote_side=[id], backref="replies")
    reactions = relationship("MessageReaction", back_populates="message", cascade="all, delete-orphan")


class MessageReaction(Base):
    """One row per (message, user, emoji). Aggregated at read time."""
    __tablename__ = "message_reactions"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", "emoji", name="uq_reaction_once"),
        Index("ix_message_reactions_message", "message_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    emoji: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    message = relationship("Message", back_populates="reactions")
    user = relationship("User")


class UserPresence(Base):
    """
    Last-seen and status, one row per user per workspace.

    `status` is the user's declared state ('active' | 'away' | 'dnd' |
    'offline'); `last_seen_at` is the observed one. Both matter: DND is a
    promise the notifier must keep even while the socket is connected, which
    is why the notifier reads this table and not just socket liveness.
    """
    __tablename__ = "user_presence"
    __table_args__ = (
        UniqueConstraint("user_id", "org_id", name="uq_presence_user_org"),
        CheckConstraint("status IN ('active','away','dnd','offline')", name="user_presence_status_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(20), default="active")
    status_emoji: Mapped[str | None] = mapped_column(String(32))
    status_text: Mapped[str | None] = mapped_column(String(120))
    # A DND window that expires on its own. "Do not disturb until 9am" is the
    # setting people actually want; an indefinite DND just gets left on.
    dnd_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
