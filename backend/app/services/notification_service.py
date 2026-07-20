"""
Emit socket.io events from anywhere (FastAPI or Celery workers).

Uses KombuManager (write-only) which publishes to Redis.
The server-side AsyncRedisManager picks up events and forwards them
to connected WebSocket clients in the right room.

Falls back silently if Redis is unavailable.
"""
import socketio
from app.config import settings

_mgr = None


def _get_mgr():
    global _mgr
    if _mgr is None:
        try:
            _mgr = socketio.KombuManager(settings.redis_url, write_only=True)
        except Exception:
            pass
    return _mgr


def emit_run_event(run_id: str, event: str, data: dict) -> None:
    """Emit a socket.io event to the run:{run_id} room."""
    mgr = _get_mgr()
    if mgr is None:
        return
    try:
        mgr.emit(event, data, room=f"run:{run_id}")
    except Exception:
        pass  # Never let socket emit errors break the run
