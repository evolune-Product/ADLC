"""
Structured logging with structlog.

Features:
- JSON output in production, colored console in dev
- ContextVars for request_id, user_id, run_id — set once, appear in every log line
- get_logger(name) replaces logging.getLogger(__name__)
- bind_context(**kwargs) adds arbitrary k/v to the current context

Usage:
  from app.core.logging import get_logger, bind_context, new_request_id
  log = get_logger(__name__)
  bind_context(user_id="abc", run_id="xyz")
  log.info("doing_thing", key="value")
"""
from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from uuid import uuid4

import structlog

# ─── ContextVars ──────────────────────────────────────────────────────────────

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
run_id_var: ContextVar[str | None] = ContextVar("run_id", default=None)

# Extra context dict for bind_context()
_extra_context_var: ContextVar[dict] = ContextVar("_extra_context", default={})


def new_request_id() -> str:
    return str(uuid4())


def bind_context(**kwargs: object) -> None:
    """Merge kwargs into the current context so they appear in all subsequent log calls."""
    current = _extra_context_var.get()
    _extra_context_var.set({**current, **kwargs})


def _context_injector(logger, method_name, event_dict):  # noqa: ARG001
    """structlog processor: inject ContextVar values into every log event."""
    rid = request_id_var.get()
    uid = user_id_var.get()
    rnid = run_id_var.get()
    extra = _extra_context_var.get()

    if rid:
        event_dict["request_id"] = rid
    if uid:
        event_dict["user_id"] = uid
    if rnid:
        event_dict["run_id"] = rnid
    if extra:
        event_dict.update(extra)
    return event_dict


# ─── Configuration ────────────────────────────────────────────────────────────

_configured = False


def configure_logging(json_logs: bool = False) -> None:
    """
    Call once at application startup (in main.py).

    json_logs=True  → machine-readable JSON (production)
    json_logs=False → colored human-readable output (development)
    """
    global _configured
    if _configured:
        return
    _configured = True

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        _context_injector,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Drop-in replacement for logging.getLogger(__name__)."""
    return structlog.get_logger(name)
