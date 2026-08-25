"""
Workspace service — the write path for channels and messages.

Every message in the product goes through `post_message`, whether a human
typed it, an agent produced it, or a run step narrated itself. That is
deliberate: the denormalised counters on Channel, the unread bookkeeping on
ChannelMember, the socket fan-out, the notification fan-out and the mention
parse all have to happen together or the sidebar starts lying about unread
counts. One entry point is the only way to keep them consistent.

The ordering inside `post_message` matters and is not arbitrary:

    persist → counters → socket → notifications

Socket delivery comes *before* notifications so an online reader sees the
message and clears the unread before the notifier decides whether to email
them about it. That ordering is why a user with the channel open does not get
an email thirty seconds later about a message they already read.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.organization import OrgMember
from app.models.user import User
from app.models.workspace import (
    Channel, ChannelMember, Message, MessageReaction, UserPresence,
)
from app.services import llm_service, notifier
from app.services.notification_service import emit_to_room

log = logging.getLogger(__name__)

# @name, @channel, @here. Names may contain letters, digits, dot, dash and
# underscore — the set a slug can hold — but must both start and end
# alphanumeric. That last requirement is what makes "ping @dev." resolve to
# `dev` rather than `dev.`, which would match nobody and silently drop the
# mention. A trailing separator is punctuation in a sentence far more often
# than it is part of a handle.
_MENTION_RE = re.compile(r"@([A-Za-z0-9](?:[A-Za-z0-9._-]{0,62}[A-Za-z0-9])?)")

# Channels every workspace starts with. An empty chat surface on first login is
# the single most reliable way to send a team back to WhatsApp, so the workspace
# is never empty: #general for the team, #deploys for the machine.
DEFAULT_CHANNELS = [
    ("general", "General", "Everything that doesn't have a channel yet."),
    ("deploys", "Deploys", "Every run, approval and deploy lands here automatically."),
]

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Channel slugs are lowercase, dash-separated, and never empty."""
    s = _SLUG_RE.sub("-", (name or "").strip().lower()).strip("-")
    return s[:120] or f"channel-{uuid.uuid4().hex[:8]}"


# ── Membership and lookup ─────────────────────────────────────────────────────

def visible_channels_filter(current_user: User, org_ctx):
    """
    Scope a Channel query to one workspace.

    Mirrors `routers/_helpers.owner_filter` rather than importing it, because
    Channel's personal-workspace case is keyed on the *creating* user while
    visibility is keyed on membership; the two only coincide for public
    channels. `list_channels` applies the membership join on top of this.
    """
    if org_ctx:
        return Channel.org_id == org_ctx.org_id
    return and_(Channel.user_id == current_user.id, Channel.org_id.is_(None))


def is_member(db: Session, channel_id, user_id) -> ChannelMember | None:
    return (
        db.query(ChannelMember)
        .filter(ChannelMember.channel_id == channel_id, ChannelMember.user_id == user_id)
        .first()
    )


def can_read(db: Session, channel: Channel, user_id) -> bool:
    """
    Public and broadcast channels are readable by anyone in the workspace;
    private channels, DMs and group DMs require a membership row.

    Read access is checked on every message fetch and not cached — a member
    removed from a private channel mid-session must stop seeing it on their
    next request, not on their next login.
    """
    if channel.kind in ("channel", "broadcast"):
        return True
    return is_member(db, channel.id, user_id) is not None


def can_post(db: Session, channel: Channel, user_id) -> tuple[bool, str | None]:
    """
    Returns (allowed, reason). Broadcast channels are the WhatsApp-Channel
    shape — admins publish, everyone else reads — and that asymmetry is the
    entire reason the kind exists, so it is enforced here rather than hidden
    in the UI.
    """
    if channel.is_archived:
        return False, "This channel is archived"

    member = is_member(db, channel.id, user_id)
    if channel.kind in ("private", "dm", "group_dm") and member is None:
        return False, "You are not a member of this channel"

    if channel.kind == "broadcast":
        if member is None or member.role not in ("owner", "admin"):
            return False, "Only channel admins can post to a broadcast channel"

    return True, None


def ensure_member(db: Session, channel: Channel, *, user_id=None, agent_id=None,
                  role: str = "member") -> ChannelMember:
    """Idempotent join. Returns the existing row if there is one."""
    q = db.query(ChannelMember).filter(ChannelMember.channel_id == channel.id)
    q = q.filter(ChannelMember.user_id == user_id) if user_id else q.filter(ChannelMember.agent_id == agent_id)
    existing = q.first()
    if existing:
        return existing

    member = ChannelMember(channel_id=channel.id, user_id=user_id, agent_id=agent_id, role=role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def ensure_default_channels(db: Session, current_user: User, org_ctx) -> list[Channel]:
    """
    Create #general and #deploys for a workspace that has none, and join the
    caller to every default channel.

    Called on the channel-list read path rather than at org creation, because
    orgs created before this feature existed would otherwise never get them —
    and a backfill migration that inserts rows for every existing org is a
    worse trade than a cheap `is_default` lookup per sidebar load.
    """
    scope = visible_channels_filter(current_user, org_ctx)
    existing = db.query(Channel).filter(scope, Channel.is_default.is_(True)).all()

    if not existing:
        for slug, name, topic in DEFAULT_CHANNELS:
            db.add(Channel(
                user_id=current_user.id,
                org_id=org_ctx.org_id if org_ctx else None,
                kind="channel",
                name=name,
                slug=slug,
                topic=topic,
                is_default=True,
                created_by=current_user.id,
            ))
        db.commit()
        existing = db.query(Channel).filter(scope, Channel.is_default.is_(True)).all()

    for ch in existing:
        ensure_member(db, ch, user_id=current_user.id, role="member")
    return existing


def dm_channel(db: Session, current_user: User, org_ctx, other_user_id: uuid.UUID) -> Channel:
    """
    Find or create the 1:1 DM between two users.

    A DM is identified by its member set, not by a name, so the lookup is
    "channels of kind dm that both of these users belong to". Cheap enough at
    DM scale, and it means there is no synthetic composite key to keep sorted.
    """
    mine = db.query(ChannelMember.channel_id).filter(ChannelMember.user_id == current_user.id).subquery()
    theirs = db.query(ChannelMember.channel_id).filter(ChannelMember.user_id == other_user_id).subquery()

    existing = (
        db.query(Channel)
        .filter(
            visible_channels_filter(current_user, org_ctx),
            Channel.kind == "dm",
            Channel.id.in_(mine),
            Channel.id.in_(theirs),
        )
        .first()
    )
    if existing:
        return existing

    ch = Channel(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        kind="dm",
        created_by=current_user.id,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)

    ensure_member(db, ch, user_id=current_user.id, role="owner")
    ensure_member(db, ch, user_id=other_user_id, role="owner")
    return ch


# ── Mentions ──────────────────────────────────────────────────────────────────

def parse_mentions(db: Session, body: str, channel: Channel, org_ctx) -> dict:
    """
    Resolve @tokens to user ids, agent ids and the broadcast flags.

    Parsed once at write time and stored on the row. Doing it at render time
    would mean re-resolving every name in every message on every scroll, and
    would also mean a renamed agent silently rewrote history.

    Humans are matched on the local part of their email and on their display
    name slug; agents on their name slug. Agents are checked first because an
    agent named "qa" and a user qa@company.com is a real collision, and the
    agent is the one the sentence "@qa please look at this" means in a channel
    that has an agent member.
    """
    tokens = {m.group(1).lower() for m in _MENTION_RE.finditer(body or "")}
    out: dict = {"users": [], "agents": [], "channel": False, "here": False}
    if not tokens:
        return out

    if "channel" in tokens or "all" in tokens:
        out["channel"] = True
    if "here" in tokens:
        out["here"] = True
    tokens -= {"channel", "all", "here"}
    if not tokens:
        return out

    agent_scope = (
        Agent.org_id == org_ctx.org_id if org_ctx
        else and_(Agent.user_id == channel.user_id, Agent.org_id.is_(None))
    )
    for agent in db.query(Agent).filter(agent_scope, Agent.is_active.is_(True)).all():
        if slugify(agent.name) in tokens or agent.role.lower() in tokens:
            out["agents"].append(str(agent.id))
            tokens.discard(slugify(agent.name))
            tokens.discard(agent.role.lower())

    if tokens:
        for user in _workspace_users(db, channel, org_ctx):
            local = (user.email or "").split("@")[0].lower()
            if local in tokens or slugify(user.name or "") in tokens:
                out["users"].append(str(user.id))

    return out


def _workspace_users(db: Session, channel: Channel, org_ctx) -> list[User]:
    """Everyone who could possibly be mentioned in this channel."""
    if org_ctx:
        return (
            db.query(User)
            .join(OrgMember, OrgMember.user_id == User.id)
            .filter(OrgMember.org_id == org_ctx.org_id)
            .all()
        )
    owner = db.query(User).filter(User.id == channel.user_id).first()
    return [owner] if owner else []


def _recipients(db: Session, channel: Channel, mentions: dict, exclude_user_id) -> list[ChannelMember]:
    """
    Which memberships should be told about this message.

    `notify_level` and `is_muted` are honoured here rather than in the notifier
    because they are per-channel settings and the notifier only knows about
    users. A muted channel still increments the unread count — mute means "do
    not interrupt me", not "hide this from me".
    """
    members = (
        db.query(ChannelMember)
        .filter(ChannelMember.channel_id == channel.id, ChannelMember.user_id.isnot(None))
        .all()
    )
    mentioned = set(mentions.get("users") or [])
    broadcast = bool(mentions.get("channel") or mentions.get("here"))

    out = []
    for m in members:
        if m.user_id == exclude_user_id:
            continue
        was_mentioned = str(m.user_id) in mentioned or broadcast
        if m.notify_level == "none":
            continue
        if m.notify_level == "mentions" and not was_mentioned:
            continue
        if m.is_muted and not was_mentioned:
            continue
        out.append(m)
    return out


def _is_dnd(db: Session, user_id, org_id) -> bool:
    """A DND window suppresses email/Slack, never the in-app record."""
    row = (
        db.query(UserPresence)
        .filter(UserPresence.user_id == user_id, UserPresence.org_id == org_id)
        .first()
    )
    if not row:
        return False
    if row.dnd_until and row.dnd_until > datetime.now(timezone.utc):
        return True
    return row.status == "dnd"


# ── The write path ────────────────────────────────────────────────────────────

def post_message(
    db: Session,
    *,
    channel: Channel,
    body: str,
    author: User | None = None,
    agent_id: uuid.UUID | None = None,
    kind: str = "user",
    parent_id: uuid.UUID | None = None,
    attachments: list | None = None,
    payload: dict | None = None,
    org_ctx=None,
    notify: bool = True,
) -> Message:
    """
    The single entry point for every message. See the module docstring for why.

    `notify=False` exists for the run-narration path: a run posting forty step
    events into #deploys must not send forty emails. Those messages still
    persist, still emit on the socket, and still bump the unread count — they
    just do not page anyone. The one exception is an approval request, which is
    the whole point of the notifier and always notifies.
    """
    mentions = parse_mentions(db, body, channel, org_ctx) if kind in ("user", "agent") else {}

    msg = Message(
        channel_id=channel.id,
        parent_id=parent_id,
        kind=kind,
        author_id=author.id if author else None,
        agent_id=agent_id,
        body=body or "",
        mentions=mentions,
        attachments=attachments or [],
        payload=payload or {},
    )
    db.add(msg)

    # Counters. A reply bumps the thread's parent, not the channel preview —
    # a channel whose preview flips to a deep thread reply is how Slack's
    # sidebar became unreadable.
    now = datetime.now(timezone.utc)
    if parent_id:
        parent = db.query(Message).filter(Message.id == parent_id).first()
        if parent:
            parent.reply_count = (parent.reply_count or 0) + 1
            parent.last_reply_at = now
    else:
        channel.last_message_at = now
        channel.last_message_preview = _preview(body, kind)
    channel.message_count = (channel.message_count or 0) + 1

    # Mention counters, so the sidebar can show "3 unread, 1 for you".
    if mentions.get("users") or mentions.get("channel") or mentions.get("here"):
        _bump_mention_counts(db, channel, mentions, exclude_user_id=author.id if author else None)

    db.commit()
    db.refresh(msg)

    # Exactly one publish per message, to the channel's room.
    #
    # The obvious alternative — also emitting a badge event to each recipient's
    # `user:{id}` room — is O(members) publishes for every message posted, which
    # in a 200-person #general is 200 round trips to the message broker to
    # deliver one line of text. Instead the client subscribes to every channel
    # it belongs to, not only the one on screen, and decides locally whether an
    # inbound message is a badge or a rendered line. Rooms are cheap on the
    # server; broker publishes are not.
    payload_out = serialize_message(db, msg)
    emit_to_room(f"channel:{channel.id}", "message:new", payload_out)

    if notify or kind == "approval_request":
        _fan_out_notifications(db, channel, msg, mentions, author)

    return msg


def _preview(body: str, kind: str) -> str:
    text = (body or "").replace("\n", " ").strip()
    if kind == "system" and not text:
        text = "Run update"
    return text[:280]


def _bump_mention_counts(db: Session, channel: Channel, mentions: dict, exclude_user_id) -> None:
    q = db.query(ChannelMember).filter(
        ChannelMember.channel_id == channel.id,
        ChannelMember.user_id.isnot(None),
    )
    if not (mentions.get("channel") or mentions.get("here")):
        ids = [uuid.UUID(u) for u in mentions.get("users") or []]
        if not ids:
            return
        q = q.filter(ChannelMember.user_id.in_(ids))

    for member in q.all():
        if member.user_id == exclude_user_id:
            continue
        member.unread_mentions = (member.unread_mentions or 0) + 1


def _fan_out_notifications(db: Session, channel: Channel, msg: Message,
                           mentions: dict, author: User | None) -> None:
    """
    Reach people who are not looking at the screen.

    Every failure here is swallowed for the same reason the notifier swallows
    its own: a broken SMTP host must never lose a message that is already
    committed.
    """
    try:
        label = channel.name or "Direct message"
        who = (author.name or author.email) if author else "ADLC"
        mentioned = set(mentions.get("users") or [])
        broadcast = bool(mentions.get("channel") or mentions.get("here"))

        for member in _recipients(db, channel, mentions, exclude_user_id=author.id if author else None):
            direct = str(member.user_id) in mentioned or broadcast or channel.kind in ("dm", "group_dm")
            # Only a mention or a DM is allowed to page someone. Ordinary
            # channel traffic stays in the app; that restraint is the
            # difference between a tool people keep and one they mute.
            if not direct:
                continue
            if _is_dnd(db, member.user_id, channel.org_id):
                continue

            notifier.notify_user(
                db,
                user_id=member.user_id,
                org_id=channel.org_id,
                type="workspace.mention" if not channel.kind.endswith("dm") else "workspace.dm",
                title=f"{who} in #{label}" if channel.name else f"{who} sent you a message",
                body=(msg.body or "")[:400],
                link=f"/workspace/{channel.id}",
                payload={"channel_id": str(channel.id), "message_id": str(msg.id)},
            )
    except Exception:
        log.exception("Workspace notification fan-out failed for channel %s", channel.id)


# ── Read state ────────────────────────────────────────────────────────────────

def mark_read(db: Session, channel_id, user_id) -> ChannelMember | None:
    member = is_member(db, channel_id, user_id)
    if not member:
        return None
    member.last_read_at = datetime.now(timezone.utc)
    member.unread_mentions = 0
    db.commit()
    db.refresh(member)
    emit_to_room(f"user:{user_id}", "workspace:read", {"channelId": str(channel_id)})
    return member


def unread_counts(db: Session, user_id, channel_ids: list[uuid.UUID]) -> dict[str, int]:
    """
    Unread message count per channel, in one query for the whole sidebar.

    A per-channel COUNT(*) in a loop is N queries to paint one list; this is a
    single grouped count joined against each member's high-water mark. The
    `last_read_at IS NULL` arm covers a channel joined but never opened.
    """
    if not channel_ids:
        return {}

    rows = (
        db.query(Message.channel_id, func.count(Message.id))
        .join(
            ChannelMember,
            and_(
                ChannelMember.channel_id == Message.channel_id,
                ChannelMember.user_id == user_id,
            ),
        )
        .filter(
            Message.channel_id.in_(channel_ids),
            Message.parent_id.is_(None),
            Message.is_deleted.is_(False),
            or_(
                ChannelMember.last_read_at.is_(None),
                Message.created_at > ChannelMember.last_read_at,
            ),
            or_(Message.author_id.is_(None), Message.author_id != user_id),
        )
        .group_by(Message.channel_id)
        .all()
    )
    return {str(cid): count for cid, count in rows}


# ── Serialisation ─────────────────────────────────────────────────────────────

def serialize_message(db: Session, msg: Message) -> dict:
    """
    One message, shaped for the client.

    Author identity is embedded rather than referenced so the client never has
    to hold a user cache to render a scroll — the cost is a few duplicated
    strings per page, the saving is an entire class of "unknown user" bugs.
    """
    author = None
    if msg.author_id:
        u = db.query(User).filter(User.id == msg.author_id).first()
        if u:
            author = {"id": str(u.id), "name": u.name or u.email.split("@")[0],
                      "email": u.email, "avatar_url": u.avatar_url, "is_agent": False}
    elif msg.agent_id:
        a = db.query(Agent).filter(Agent.id == msg.agent_id).first()
        if a:
            author = {"id": str(a.id), "name": a.name, "email": None,
                      "avatar_url": None, "is_agent": True, "role": a.role}

    reactions: dict[str, list[str]] = {}
    for r in db.query(MessageReaction).filter(MessageReaction.message_id == msg.id).all():
        reactions.setdefault(r.emoji, []).append(str(r.user_id))

    return {
        "id": str(msg.id),
        "channel_id": str(msg.channel_id),
        "parent_id": str(msg.parent_id) if msg.parent_id else None,
        "kind": msg.kind,
        "author": author,
        "body": "" if msg.is_deleted else (msg.body or ""),
        "mentions": msg.mentions or {},
        "attachments": msg.attachments or [],
        "payload": msg.payload or {},
        "reactions": [{"emoji": k, "users": v, "count": len(v)} for k, v in reactions.items()],
        "reply_count": msg.reply_count or 0,
        "last_reply_at": msg.last_reply_at.isoformat() if msg.last_reply_at else None,
        "is_pinned": msg.is_pinned,
        "is_deleted": msg.is_deleted,
        "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


def serialize_channel(db: Session, ch: Channel, *, user_id=None, unread: int = 0) -> dict:
    member = is_member(db, ch.id, user_id) if user_id else None

    # A DM has no name of its own; it is named after the person on the other
    # end, which is a per-viewer answer and so cannot be stored on the row.
    display_name = ch.name
    if ch.kind == "dm" and user_id:
        other = (
            db.query(User)
            .join(ChannelMember, ChannelMember.user_id == User.id)
            .filter(ChannelMember.channel_id == ch.id, ChannelMember.user_id != user_id)
            .first()
        )
        if other:
            display_name = other.name or other.email.split("@")[0]

    return {
        "id": str(ch.id),
        "kind": ch.kind,
        "name": display_name,
        "slug": ch.slug,
        "topic": ch.topic,
        "description": ch.description,
        "project_id": str(ch.project_id) if ch.project_id else None,
        "run_id": str(ch.run_id) if ch.run_id else None,
        "ticket_id": str(ch.ticket_id) if ch.ticket_id else None,
        "is_default": ch.is_default,
        "is_archived": ch.is_archived,
        "message_count": ch.message_count or 0,
        "last_message_at": ch.last_message_at.isoformat() if ch.last_message_at else None,
        "last_message_preview": ch.last_message_preview,
        "unread": unread,
        "unread_mentions": member.unread_mentions if member else 0,
        "is_member": member is not None,
        "is_muted": member.is_muted if member else False,
        "is_starred": member.is_starred if member else False,
        "notify_level": member.notify_level if member else "all",
        "member_role": member.role if member else None,
        "created_at": ch.created_at.isoformat() if ch.created_at else None,
    }


# ── Catch-up summary ──────────────────────────────────────────────────────────

CATCHUP_SYSTEM = """You are summarising a work chat channel for a teammate who has been away.

Write a tight catch-up. Rules:
- Lead with anything that needs a decision or is blocking someone.
- Name people and agents explicitly ("Priya asked...", "the QA agent found...").
- Note unanswered questions directed at the reader if any.
- Skip greetings, acknowledgements and chatter entirely.
- 120 words maximum. No preamble, no "here is a summary".
- If nothing of substance happened, say exactly: Nothing needing your attention."""


def summarize_channel(db: Session, channel: Channel, *, since: datetime | None = None,
                      limit: int = 200, byo_provider=None, byo_key=None) -> dict:
    """
    "Catch me up" — the feature that makes a 400-message overnight channel
    survivable, and the reason a team stops scrolling a WhatsApp group.

    Routed through `llm_service.complete` like every other model call in this
    codebase so the tokens are metered and attributable. A summary that
    bypassed metering would be the one un-capped cost path in the product.
    """
    q = db.query(Message).filter(
        Message.channel_id == channel.id,
        Message.is_deleted.is_(False),
    )
    if since:
        q = q.filter(Message.created_at > since)
    rows = q.order_by(Message.created_at.desc()).limit(limit).all()
    rows.reverse()

    if not rows:
        return {"summary": "Nothing new since you were last here.", "message_count": 0,
                "cost_millicents": 0}

    lines = []
    for m in rows:
        who = "system"
        if m.author_id:
            u = db.query(User).filter(User.id == m.author_id).first()
            who = (u.name or u.email.split("@")[0]) if u else "someone"
        elif m.agent_id:
            a = db.query(Agent).filter(Agent.id == m.agent_id).first()
            who = f"{a.name} (agent)" if a else "agent"
        lines.append(f"{who}: {(m.body or '')[:500]}")

    result = llm_service.complete(
        system=CATCHUP_SYSTEM,
        user=f"Channel #{channel.name or 'direct message'}\n\n" + "\n".join(lines),
        max_tokens=600,
        force_tool=False,
        byo_provider=byo_provider,
        byo_key=byo_key,
    )
    return {
        "summary": (result.text or "").strip(),
        "message_count": len(rows),
        "cost_millicents": result.cost_millicents,
    }


# ── Presence ──────────────────────────────────────────────────────────────────

# How long after the last heartbeat a user is still shown as online. Long
# enough to survive a laptop lid closing for a moment, short enough that a
# green dot means something.
PRESENCE_TTL = timedelta(minutes=5)


def touch_presence(db: Session, user_id, org_id, *, status: str | None = None,
                   status_text: str | None = None, status_emoji: str | None = None,
                   dnd_until: datetime | None = None) -> UserPresence:
    row = (
        db.query(UserPresence)
        .filter(UserPresence.user_id == user_id, UserPresence.org_id == org_id)
        .first()
    )
    if not row:
        row = UserPresence(user_id=user_id, org_id=org_id)
        db.add(row)

    row.last_seen_at = datetime.now(timezone.utc)
    if status:
        row.status = status
    if status_text is not None:
        row.status_text = status_text or None
    if status_emoji is not None:
        row.status_emoji = status_emoji or None
    if dnd_until is not None:
        row.dnd_until = dnd_until

    db.commit()
    db.refresh(row)
    return row


def presence_map(db: Session, org_id, user_ids: list[uuid.UUID]) -> dict[str, dict]:
    """
    Resolve stored status against the heartbeat clock.

    A row saying 'active' whose `last_seen_at` is an hour old means the tab was
    closed without a clean disconnect, which happens constantly on mobile. The
    TTL is what stops the member list from being a wall of stale green dots.
    """
    if not user_ids:
        return {}

    cutoff = datetime.now(timezone.utc) - PRESENCE_TTL
    rows = (
        db.query(UserPresence)
        .filter(UserPresence.user_id.in_(user_ids), UserPresence.org_id == org_id)
        .all()
    )
    out = {}
    for r in rows:
        live = r.last_seen_at is not None and r.last_seen_at > cutoff
        status = r.status if live else "offline"
        if r.dnd_until and r.dnd_until > datetime.now(timezone.utc):
            status = "dnd"
        out[str(r.user_id)] = {
            "status": status,
            "status_text": r.status_text,
            "status_emoji": r.status_emoji,
            "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
        }
    return out
