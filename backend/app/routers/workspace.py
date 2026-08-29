"""
Workspace router — channels, messages, threads, reactions, presence, search.

Access rules, stated once here because they are enforced on every route:

  * Read  — public and broadcast channels are open to the workspace; private,
            dm and group_dm need a membership row (`workspace_service.can_read`).
  * Write — additionally, broadcast channels accept posts only from their own
            admins (`workspace_service.can_post`).
  * Admin — renaming, archiving and removing members needs `owner`/`admin` on
            the channel, or `admin` on the org.

The list endpoints return the caller's per-member state (unread, muted,
starred) inline with each channel, because a sidebar that needs a second
request per row to know whether it is bold is a sidebar that flickers.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent import Agent
from app.models.organization import OrgMember
from app.models.user import User
from app.models.workspace import (
    CHANNEL_KINDS, Channel, ChannelMember, Message, MessageReaction,
)
from app.routers._helpers import OrgContext, can_write, get_optional_org, is_domain_admin
from app.routers.auth import get_current_user
from app.services import workspace_bridge as bridge
from app.services import workspace_service as ws
from app.services.notification_service import emit_to_room

router = APIRouter()


# ── Bodies ────────────────────────────────────────────────────────────────────

class ChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = "channel"
    topic: str | None = None
    description: str | None = None
    project_id: uuid.UUID | None = None
    member_ids: list[uuid.UUID] = Field(default_factory=list)
    agent_ids: list[uuid.UUID] = Field(default_factory=list)


class ChannelUpdate(BaseModel):
    name: str | None = None
    topic: str | None = None
    description: str | None = None
    is_archived: bool | None = None


class ChannelPrefs(BaseModel):
    notify_level: str | None = None       # all | mentions | none
    is_muted: bool | None = None
    is_starred: bool | None = None


class MessageCreate(BaseModel):
    body: str = ""
    parent_id: uuid.UUID | None = None
    attachments: list[dict] = Field(default_factory=list)


class MessageUpdate(BaseModel):
    body: str = Field(min_length=1)


class ReactionBody(BaseModel):
    emoji: str = Field(min_length=1, max_length=32)


class MemberAdd(BaseModel):
    user_ids: list[uuid.UUID] = Field(default_factory=list)
    agent_ids: list[uuid.UUID] = Field(default_factory=list)


class PresenceBody(BaseModel):
    status: str | None = None             # active | away | dnd | offline
    status_text: str | None = None
    status_emoji: str | None = None
    dnd_minutes: int | None = None        # a DND window that expires by itself


# ── Lookups ───────────────────────────────────────────────────────────────────

def _get_channel(channel_id: uuid.UUID, db: Session, current_user: User,
                 org_ctx: Optional[OrgContext]) -> Channel:
    ch = (
        db.query(Channel)
        .filter(Channel.id == channel_id, ws.visible_channels_filter(current_user, org_ctx))
        .first()
    )
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    if not ws.can_read(db, ch, current_user.id):
        # 404 rather than 403: confirming that a private channel exists to
        # someone who cannot read it leaks the channel list by probing.
        raise HTTPException(status_code=404, detail="Channel not found")
    return ch


def _require_channel_admin(db: Session, ch: Channel, current_user: User,
                           org_ctx: Optional[OrgContext]) -> None:
    member = ws.is_member(db, ch.id, current_user.id)
    if member and member.role in ("owner", "admin"):
        return
    # An org-wide admin — owner, admin, or an engineering lead — can moderate
    # any channel even without a channel-level role, the same fallback every
    # other engineering surface gives that role.
    if org_ctx and is_domain_admin(org_ctx, "engineering"):
        return
    raise HTTPException(status_code=403, detail="Only channel admins can do that")


# ── Channels ──────────────────────────────────────────────────────────────────

@router.get("/workspace/channels")
def list_channels(
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    The sidebar. Returns every channel the caller can see, with their unread
    state resolved, newest activity first.
    """
    ws.ensure_default_channels(db, current_user, org_ctx)

    # `.scalar_subquery()`, not `.subquery()` — IN() wants a SELECT of one
    # column, and passing a Subquery makes SQLAlchemy coerce it with a warning.
    joined = db.query(ChannelMember.channel_id).filter(
        ChannelMember.user_id == current_user.id
    ).scalar_subquery()

    q = db.query(Channel).filter(ws.visible_channels_filter(current_user, org_ctx))
    if not include_archived:
        q = q.filter(Channel.is_archived.is_(False))
    # Public and broadcast channels are browsable even before joining; private
    # ones and DMs appear only once you are a member.
    q = q.filter(or_(Channel.kind.in_(("channel", "broadcast")), Channel.id.in_(joined)))

    # DESC first, then NULLS LAST — the other composition order emits
    # `NULLS LAST DESC`, which Postgres rejects outright. A channel nobody has
    # spoken in yet sorts below every channel that has traffic.
    rows = q.order_by(Channel.last_message_at.desc().nullslast(), Channel.created_at).all()
    unread = ws.unread_counts(db, current_user.id, [c.id for c in rows])

    channels = [ws.serialize_channel(db, c, user_id=current_user.id,
                                     unread=unread.get(str(c.id), 0)) for c in rows]
    return {
        "channels": channels,
        "total_unread": sum(c["unread"] for c in channels if c["is_member"]),
        "total_mentions": sum(c["unread_mentions"] for c in channels),
    }


@router.post("/workspace/channels", status_code=status.HTTP_201_CREATED)
def create_channel(
    body: ChannelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    if body.kind not in CHANNEL_KINDS or body.kind == "dm":
        raise HTTPException(status_code=422, detail="kind must be channel, private, broadcast or group_dm")
    if org_ctx and not can_write(org_ctx):
        raise HTTPException(status_code=403, detail="Read-only members cannot create channels")

    slug = ws.slugify(body.name)
    clash = (
        db.query(Channel)
        .filter(ws.visible_channels_filter(current_user, org_ctx), Channel.slug == slug)
        .first()
    )
    if clash:
        raise HTTPException(status_code=409, detail=f"#{slug} already exists")

    ch = Channel(
        user_id=current_user.id,
        org_id=org_ctx.org_id if org_ctx else None,
        kind=body.kind,
        name=body.name,
        slug=slug if body.kind != "group_dm" else None,
        topic=body.topic,
        description=body.description,
        project_id=body.project_id,
        created_by=current_user.id,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)

    ws.ensure_member(db, ch, user_id=current_user.id, role="owner")
    for uid in body.member_ids:
        ws.ensure_member(db, ch, user_id=uid)
    for aid in body.agent_ids:
        ws.ensure_member(db, ch, agent_id=aid)

    return ws.serialize_channel(db, ch, user_id=current_user.id)


@router.get("/workspace/channels/{channel_id}")
def get_channel(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    unread = ws.unread_counts(db, current_user.id, [ch.id])
    return ws.serialize_channel(db, ch, user_id=current_user.id, unread=unread.get(str(ch.id), 0))


@router.patch("/workspace/channels/{channel_id}")
def update_channel(
    channel_id: uuid.UUID,
    body: ChannelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    _require_channel_admin(db, ch, current_user, org_ctx)

    if body.name is not None:
        ch.name = body.name
        if ch.kind in ("channel", "private", "broadcast"):
            ch.slug = ws.slugify(body.name)
    if body.topic is not None:
        ch.topic = body.topic
    if body.description is not None:
        ch.description = body.description
    if body.is_archived is not None:
        ch.is_archived = body.is_archived

    db.commit()
    db.refresh(ch)
    return ws.serialize_channel(db, ch, user_id=current_user.id)


@router.delete("/workspace/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    _require_channel_admin(db, ch, current_user, org_ctx)
    if ch.is_default:
        raise HTTPException(status_code=400, detail="Default channels can be archived but not deleted")
    db.delete(ch)
    db.commit()


@router.post("/workspace/channels/{channel_id}/join")
def join_channel(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    if ch.kind in ("private", "dm", "group_dm"):
        raise HTTPException(status_code=403, detail="This channel is invite-only")
    ws.ensure_member(db, ch, user_id=current_user.id)
    return ws.serialize_channel(db, ch, user_id=current_user.id)


@router.delete("/workspace/channels/{channel_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_channel(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    member = ws.is_member(db, ch.id, current_user.id)
    if member:
        db.delete(member)
        db.commit()


@router.patch("/workspace/channels/{channel_id}/prefs")
def update_prefs(
    channel_id: uuid.UUID,
    body: ChannelPrefs,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Mute, star, and per-channel notification level."""
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    member = ws.ensure_member(db, ch, user_id=current_user.id)

    if body.notify_level is not None:
        if body.notify_level not in ("all", "mentions", "none"):
            raise HTTPException(status_code=422, detail="notify_level must be all, mentions or none")
        member.notify_level = body.notify_level
    if body.is_muted is not None:
        member.is_muted = body.is_muted
    if body.is_starred is not None:
        member.is_starred = body.is_starred

    db.commit()
    db.refresh(ch)
    return ws.serialize_channel(db, ch, user_id=current_user.id)


# ── Members ───────────────────────────────────────────────────────────────────

@router.get("/workspace/channels/{channel_id}/members")
def list_members(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    rows = db.query(ChannelMember).filter(ChannelMember.channel_id == ch.id).all()

    user_ids = [m.user_id for m in rows if m.user_id]
    presence = ws.presence_map(db, ch.org_id, user_ids)

    out = []
    for m in rows:
        if m.user_id:
            u = db.query(User).filter(User.id == m.user_id).first()
            if not u:
                continue
            p = presence.get(str(u.id), {})
            out.append({
                "id": str(m.id), "role": m.role, "is_agent": False,
                "user": {"id": str(u.id), "name": u.name or u.email.split("@")[0],
                         "email": u.email, "avatar_url": u.avatar_url},
                "presence": p.get("status", "offline"),
                "status_text": p.get("status_text"),
                "status_emoji": p.get("status_emoji"),
            })
        elif m.agent_id:
            a = db.query(Agent).filter(Agent.id == m.agent_id).first()
            if not a:
                continue
            out.append({
                "id": str(m.id), "role": m.role, "is_agent": True,
                "agent": {"id": str(a.id), "name": a.name, "role": a.role,
                          "model": a.llm_model, "is_active": a.is_active},
                "presence": "active" if a.is_active else "offline",
            })
    return {"members": out}


@router.post("/workspace/channels/{channel_id}/members")
def add_members(
    channel_id: uuid.UUID,
    body: MemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    if ch.kind in ("private", "broadcast"):
        _require_channel_admin(db, ch, current_user, org_ctx)

    added = []
    for uid in body.user_ids:
        ws.ensure_member(db, ch, user_id=uid)
        added.append(str(uid))
    for aid in body.agent_ids:
        ws.ensure_member(db, ch, agent_id=aid)
        added.append(str(aid))

    if added:
        ws.post_message(db, channel=ch, kind="system", notify=False,
                        body=f"{current_user.name or current_user.email} added {len(added)} member(s).")
    return {"added": added}


@router.delete("/workspace/channels/{channel_id}/members/{member_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    channel_id: uuid.UUID,
    member_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    _require_channel_admin(db, ch, current_user, org_ctx)
    member = (
        db.query(ChannelMember)
        .filter(ChannelMember.id == member_id, ChannelMember.channel_id == ch.id)
        .first()
    )
    if member:
        db.delete(member)
        db.commit()


# ── Messages ──────────────────────────────────────────────────────────────────

@router.get("/workspace/channels/{channel_id}/messages")
def list_messages(
    channel_id: uuid.UUID,
    before: Optional[datetime] = Query(None, description="Cursor: return messages older than this"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    The channel scroll, newest last.

    Keyset-paginated on `created_at` rather than OFFSET: a chat channel grows
    at the end constantly, and an offset page in a growing list either repeats
    or skips rows on every fetch.
    """
    ch = _get_channel(channel_id, db, current_user, org_ctx)

    q = db.query(Message).filter(Message.channel_id == ch.id, Message.parent_id.is_(None))
    if before:
        q = q.filter(Message.created_at < before)

    rows = q.order_by(desc(Message.created_at)).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    rows.reverse()

    return {
        "messages": [ws.serialize_message(db, m) for m in rows],
        "has_more": has_more,
        "next_cursor": rows[0].created_at.isoformat() if rows and has_more else None,
    }


@router.post("/workspace/channels/{channel_id}/messages", status_code=status.HTTP_201_CREATED)
def post_message(
    channel_id: uuid.UUID,
    body: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Post a message.

    Three things can happen here and the order matters. A slash command is
    handled and never becomes a normal message. Otherwise the message is
    persisted, and only then are any @agent mentions dispatched — so the agent's
    reply can be threaded under a message that already exists.
    """
    ch = _get_channel(channel_id, db, current_user, org_ctx)

    text = (body.body or "").strip()
    if not text and not body.attachments:
        raise HTTPException(status_code=422, detail="A message needs text or an attachment")

    allowed, reason = ws.can_post(db, ch, current_user.id)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    # Posting into a public channel you have only been reading joins you to it.
    # Requiring an explicit join before a first reply is friction with no
    # security value — the channel was already readable.
    ws.ensure_member(db, ch, user_id=current_user.id)

    if text.startswith("/"):
        result = bridge.handle_slash(db, channel=ch, body=text,
                                     current_user=current_user, org_ctx=org_ctx)
        if result is not None:
            return {"command": result}

    msg = ws.post_message(
        db, channel=ch, body=text, author=current_user, kind="user",
        parent_id=body.parent_id, attachments=body.attachments, org_ctx=org_ctx,
    )

    dispatched = []
    agent_ids = (msg.mentions or {}).get("agents") or []
    if agent_ids:
        dispatched = bridge.dispatch_agent_mention(
            db, channel=ch, message=msg, current_user=current_user,
            agent_ids=agent_ids, org_ctx=org_ctx,
        )

    # @department / @team — deterministic explicit mention, tried whenever no
    # agent mention already claimed this message (an @dev mention and an
    # @sales mention in the same line is ambiguous enough that "do both"
    # would be a platform guessing, not acting on an instruction).
    if not dispatched and org_ctx:
        dept_team_dispatched = bridge.dispatch_department_mention(
            db, channel=ch, message=msg, current_user=current_user, org_ctx=org_ctx,
        )
        if dept_team_dispatched:
            dispatched = dept_team_dispatched

    out = ws.serialize_message(db, msg)
    if dispatched:
        out["dispatched"] = dispatched
    return out


@router.get("/workspace/messages/{message_id}/thread")
def get_thread(
    message_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    parent = db.query(Message).filter(Message.id == message_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Message not found")
    _get_channel(parent.channel_id, db, current_user, org_ctx)

    replies = (
        db.query(Message)
        .filter(Message.parent_id == parent.id)
        .order_by(Message.created_at)
        .all()
    )
    return {
        "parent": ws.serialize_message(db, parent),
        "replies": [ws.serialize_message(db, r) for r in replies],
    }


@router.patch("/workspace/messages/{message_id}")
def edit_message(
    message_id: uuid.UUID,
    body: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own messages")
    if msg.is_deleted:
        raise HTTPException(status_code=400, detail="That message was deleted")

    ch = _get_channel(msg.channel_id, db, current_user, org_ctx)
    msg.body = body.body
    # Re-parse: an edit that adds an @mention has to actually mention someone.
    msg.mentions = ws.parse_mentions(db, body.body, ch, org_ctx)
    msg.edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)

    out = ws.serialize_message(db, msg)
    emit_to_room(f"channel:{ch.id}", "message:updated", out)
    return out


@router.delete("/workspace/messages/{message_id}")
def delete_message(
    message_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Soft delete. The row survives with a blanked body.

    A hard delete would let someone remove the message an approval was granted
    in, after the fact, from a system whose whole value is that the record is
    trustworthy.
    """
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    ch = _get_channel(msg.channel_id, db, current_user, org_ctx)
    is_author = msg.author_id == current_user.id
    is_admin = bool(org_ctx and is_domain_admin(org_ctx, "engineering"))
    if not (is_author or is_admin):
        raise HTTPException(status_code=403, detail="You can only delete your own messages")

    msg.is_deleted = True
    msg.body = ""
    msg.attachments = []
    db.commit()

    emit_to_room(f"channel:{ch.id}", "message:deleted", {"id": str(msg.id), "channelId": str(ch.id)})
    return {"deleted": True, "id": str(msg.id)}


# ── Reactions and pins ────────────────────────────────────────────────────────

@router.post("/workspace/messages/{message_id}/reactions")
def add_reaction(
    message_id: uuid.UUID,
    body: ReactionBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    ch = _get_channel(msg.channel_id, db, current_user, org_ctx)

    existing = (
        db.query(MessageReaction)
        .filter(MessageReaction.message_id == msg.id,
                MessageReaction.user_id == current_user.id,
                MessageReaction.emoji == body.emoji)
        .first()
    )
    # Same emoji twice is a toggle, which is what every chat client's UI
    # implies by highlighting the pill you already pressed.
    if existing:
        db.delete(existing)
    else:
        db.add(MessageReaction(message_id=msg.id, user_id=current_user.id, emoji=body.emoji))
    db.commit()

    out = ws.serialize_message(db, msg)
    emit_to_room(f"channel:{ch.id}", "message:updated", out)
    return out


@router.post("/workspace/messages/{message_id}/pin")
def toggle_pin(
    message_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    ch = _get_channel(msg.channel_id, db, current_user, org_ctx)

    msg.is_pinned = not msg.is_pinned
    db.commit()
    db.refresh(msg)

    out = ws.serialize_message(db, msg)
    emit_to_room(f"channel:{ch.id}", "message:updated", out)
    return out


@router.get("/workspace/channels/{channel_id}/pins")
def list_pins(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    rows = (
        db.query(Message)
        .filter(Message.channel_id == ch.id, Message.is_pinned.is_(True),
                Message.is_deleted.is_(False))
        .order_by(desc(Message.created_at))
        .all()
    )
    return {"pins": [ws.serialize_message(db, m) for m in rows]}


# ── Read state, typing, catch-up ──────────────────────────────────────────────

@router.post("/workspace/channels/{channel_id}/read")
def mark_channel_read(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    ws.ensure_member(db, ch, user_id=current_user.id)
    ws.mark_read(db, ch.id, current_user.id)
    return {"channel_id": str(ch.id), "unread": 0}


@router.post("/workspace/channels/{channel_id}/typing", status_code=status.HTTP_202_ACCEPTED)
def typing(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Typing indicator. Fire-and-forget — never persisted.

    A typing event that outlived the keystroke would be worse than none: the
    client re-sends every few seconds and the indicator expires on the reader's
    side, so there is nothing here for a stale row to be wrong about.
    """
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    emit_to_room(f"channel:{ch.id}", "typing", {
        "channelId": str(ch.id),
        "userId": str(current_user.id),
        "name": current_user.name or current_user.email.split("@")[0],
    })
    return {"ok": True}


@router.get("/workspace/channels/{channel_id}/catchup")
def catchup(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """"Catch me up" — an AI summary of everything since your last read."""
    ch = _get_channel(channel_id, db, current_user, org_ctx)
    member = ws.is_member(db, ch.id, current_user.id)
    return ws.summarize_channel(db, ch, since=member.last_read_at if member else None)


# ── Search, directory, DMs, presence ──────────────────────────────────────────

@router.get("/workspace/search")
def search(
    q: str = Query(min_length=2),
    channel_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Message search across the workspace.

    ILIKE with a trigram-friendly pattern rather than a tsvector column, for
    the same reason `memory_service` stores embeddings as JSONB: this has to
    run on stock Postgres 15 from a compose file with no extensions enabled.
    The swap point is here — a `search_vector tsvector` column plus a GIN index
    is a drop-in replacement once a deployment can guarantee the extension.
    """
    visible = (
        db.query(Channel.id)
        .filter(ws.visible_channels_filter(current_user, org_ctx))
        .scalar_subquery()
    )
    joined = (
        db.query(ChannelMember.channel_id)
        .filter(ChannelMember.user_id == current_user.id)
        .scalar_subquery()
    )

    rows = (
        db.query(Message)
        .join(Channel, Channel.id == Message.channel_id)
        .filter(
            Message.channel_id.in_(visible),
            Message.is_deleted.is_(False),
            Message.body.ilike(f"%{q}%"),
            # Never surface a private channel's contents through search.
            or_(Channel.kind.in_(("channel", "broadcast")), Channel.id.in_(joined)),
        )
    )
    if channel_id:
        rows = rows.filter(Message.channel_id == channel_id)

    found = rows.order_by(desc(Message.created_at)).limit(limit).all()

    out = []
    for m in found:
        item = ws.serialize_message(db, m)
        ch = db.query(Channel).filter(Channel.id == m.channel_id).first()
        item["channel"] = {"id": str(ch.id), "name": ch.name, "kind": ch.kind} if ch else None
        out.append(item)
    return {"results": out, "query": q, "count": len(out)}


@router.get("/workspace/directory")
def directory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Everyone and everything that can be @mentioned, for the composer's
    autocomplete. Humans and agents in one list, because that is how they are
    typed — the caller sorts by `is_agent` if it wants them grouped.
    """
    people = []
    if org_ctx:
        rows = (
            db.query(User, OrgMember.role)
            .join(OrgMember, OrgMember.user_id == User.id)
            .filter(OrgMember.org_id == org_ctx.org_id)
            .all()
        )
        presence = ws.presence_map(db, org_ctx.org_id, [u.id for u, _ in rows])
        for u, role in rows:
            p = presence.get(str(u.id), {})
            people.append({
                "id": str(u.id), "name": u.name or u.email.split("@")[0],
                "handle": u.email.split("@")[0], "email": u.email,
                "avatar_url": u.avatar_url, "org_role": role,
                "presence": p.get("status", "offline"),
                "status_text": p.get("status_text"), "is_agent": False,
            })
    else:
        people.append({
            "id": str(current_user.id), "name": current_user.name or current_user.email.split("@")[0],
            "handle": current_user.email.split("@")[0], "email": current_user.email,
            "avatar_url": current_user.avatar_url, "org_role": "owner",
            "presence": "active", "status_text": None, "is_agent": False,
        })

    agent_scope = (
        Agent.org_id == org_ctx.org_id if org_ctx
        else and_(Agent.user_id == current_user.id, Agent.org_id.is_(None))
    )
    agents = [
        {"id": str(a.id), "name": a.name, "handle": ws.slugify(a.name),
         "role": a.role, "model": a.llm_model, "presence": "active" if a.is_active else "offline",
         "is_agent": True}
        for a in db.query(Agent).filter(agent_scope, Agent.is_active.is_(True)).all()
    ]
    return {"people": people, "agents": agents}


@router.post("/workspace/dm/{user_id}")
def open_dm(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """Open (or create) the 1:1 DM with someone."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot DM yourself")

    if org_ctx:
        target = (
            db.query(OrgMember)
            .filter(OrgMember.org_id == org_ctx.org_id, OrgMember.user_id == user_id)
            .first()
        )
        if not target:
            raise HTTPException(status_code=404, detail="That person is not in this workspace")

    ch = ws.dm_channel(db, current_user, org_ctx, user_id)
    return ws.serialize_channel(db, ch, user_id=current_user.id)


@router.get("/workspace/presence")
def get_presence(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    org_id = org_ctx.org_id if org_ctx else None
    ids = [current_user.id]
    if org_ctx:
        ids = [m.user_id for m in db.query(OrgMember).filter(OrgMember.org_id == org_ctx.org_id).all()]
    return {"presence": ws.presence_map(db, org_id, ids)}


@router.put("/workspace/presence")
def set_presence(
    body: PresenceBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """
    Heartbeat and status. The client calls this on focus and on an interval;
    `PRESENCE_TTL` in the service is what turns a missed heartbeat into
    'offline' without needing a clean disconnect.
    """
    if body.status and body.status not in ("active", "away", "dnd", "offline"):
        raise HTTPException(status_code=422, detail="status must be active, away, dnd or offline")

    dnd_until = None
    if body.dnd_minutes is not None:
        dnd_until = (datetime.now(timezone.utc) + timedelta(minutes=body.dnd_minutes)
                     if body.dnd_minutes > 0 else datetime.now(timezone.utc))

    row = ws.touch_presence(
        db, current_user.id, org_ctx.org_id if org_ctx else None,
        status=body.status, status_text=body.status_text,
        status_emoji=body.status_emoji, dnd_until=dnd_until,
    )
    return {
        "status": row.status,
        "status_text": row.status_text,
        "status_emoji": row.status_emoji,
        "dnd_until": row.dnd_until.isoformat() if row.dnd_until else None,
    }


@router.get("/workspace/unread")
def total_unread(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx: Optional[OrgContext] = Depends(get_optional_org),
):
    """The sidebar badge. Deliberately cheap — polled by the shell on a timer."""
    joined = [
        m.channel_id for m in
        db.query(ChannelMember).filter(ChannelMember.user_id == current_user.id).all()
    ]
    counts = ws.unread_counts(db, current_user.id, joined)
    mentions = (
        db.query(ChannelMember)
        .filter(ChannelMember.user_id == current_user.id, ChannelMember.unread_mentions > 0)
        .all()
    )
    return {
        "total": sum(counts.values()),
        "mentions": sum(m.unread_mentions for m in mentions),
        "by_channel": counts,
    }
