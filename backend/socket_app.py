import socketio
from app.config import settings

_ALLOWED_ORIGINS = [settings.frontend_url, "http://localhost:3000", "http://localhost:5173"]

# Try Redis manager so Celery workers can emit events too.
# Falls back to in-process manager if Redis/aioredis is unavailable.
try:
    mgr = socketio.AsyncRedisManager(settings.redis_url)
    sio = socketio.AsyncServer(
        async_mode="asgi",
        client_manager=mgr,
        cors_allowed_origins=_ALLOWED_ORIGINS,
    )
except Exception:
    sio = socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=_ALLOWED_ORIGINS,
    )


@sio.event
async def connect(sid, environ):
    pass


@sio.event
async def disconnect(sid):
    pass


@sio.event
async def join_run(sid, data):
    run_id = data.get("run_id")
    if run_id:
        await sio.enter_room(sid, f"run:{run_id}")


@sio.event
async def leave_run(sid, data):
    run_id = data.get("run_id")
    if run_id:
        await sio.leave_room(sid, f"run:{run_id}")


# ── Workspace rooms ───────────────────────────────────────────────────────────
#
# Two room shapes, and the distinction matters.
#
#   channel:{id}  — the open channel. Carries the message firehose: new
#                   messages, edits, reactions, typing. A client joins the one
#                   it is looking at and leaves when it navigates away.
#   user:{id}     — the person, wherever they are in the app. Carries only
#                   sidebar-level facts (an unread bumped, a channel read on
#                   another device). Without it, a DM that arrives while you
#                   are on the Runs page shows up on the next refresh instead
#                   of immediately.
#
# Room membership is not an authorisation check. Every message a client
# receives here was already scoped by the router that emitted it; these
# handlers only decide where events are delivered, never what a client is
# allowed to read.


@sio.event
async def join_channel(sid, data):
    channel_id = data.get("channel_id")
    if channel_id:
        await sio.enter_room(sid, f"channel:{channel_id}")


@sio.event
async def leave_channel(sid, data):
    channel_id = data.get("channel_id")
    if channel_id:
        await sio.leave_room(sid, f"channel:{channel_id}")


@sio.event
async def join_user(sid, data):
    user_id = data.get("user_id")
    if user_id:
        await sio.enter_room(sid, f"user:{user_id}")
