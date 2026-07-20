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
