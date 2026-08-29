"""
Functional retry decorator with exponential backoff + full jitter.

Works on both async and sync functions.

Usage:
  from app.core.retry import with_retry, CLAUDE_RETRY, GITHUB_RETRY, JIRA_RETRY

  @with_retry(CLAUDE_RETRY)
  async def call_claude(...):
      ...

  @with_retry(GITHUB_RETRY)
  def fetch_repos(token: str):
      ...
"""
from __future__ import annotations

import asyncio
import functools
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Type

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0       # seconds
    max_delay: float = 60.0       # seconds
    jitter: bool = True
    # Only retry on these exception types (narrow — auth errors are NOT included)
    retryable: tuple[Type[Exception], ...] = field(default_factory=tuple)


def _backoff_delay(attempt: int, cfg: RetryConfig) -> float:
    """Exponential backoff with optional full jitter."""
    delay = min(cfg.base_delay * (2 ** attempt), cfg.max_delay)
    if cfg.jitter:
        delay = random.uniform(0, delay)
    return delay


def with_retry(cfg: RetryConfig):
    """
    Decorator factory. Works on both async and sync functions.
    On each failure, logs the attempt and waits before retrying.
    Raises the last exception if all attempts are exhausted.
    """
    def decorator(fn: Callable) -> Callable:
        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                last_exc: Exception | None = None
                for attempt in range(cfg.max_attempts):
                    try:
                        return await fn(*args, **kwargs)
                    except cfg.retryable as exc:
                        last_exc = exc
                        if attempt < cfg.max_attempts - 1:
                            delay = _backoff_delay(attempt, cfg)
                            log.warning(
                                "retry_attempt",
                                fn=fn.__qualname__,
                                attempt=attempt + 1,
                                max_attempts=cfg.max_attempts,
                                delay_s=round(delay, 2),
                                error=str(exc),
                            )
                            await asyncio.sleep(delay)
                    except Exception:
                        raise  # non-retryable — propagate immediately
                raise last_exc  # type: ignore[misc]
            return async_wrapper

        else:
            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                last_exc: Exception | None = None
                for attempt in range(cfg.max_attempts):
                    try:
                        return fn(*args, **kwargs)
                    except cfg.retryable as exc:
                        last_exc = exc
                        if attempt < cfg.max_attempts - 1:
                            delay = _backoff_delay(attempt, cfg)
                            log.warning(
                                "retry_attempt",
                                fn=fn.__qualname__,
                                attempt=attempt + 1,
                                max_attempts=cfg.max_attempts,
                                delay_s=round(delay, 2),
                                error=str(exc),
                            )
                            time.sleep(delay)
                    except Exception:
                        raise
                raise last_exc  # type: ignore[misc]
            return sync_wrapper

    return decorator


# ─── Pre-built configs ────────────────────────────────────────────────────────

# Import lazily to avoid circular imports
def _transient_errors():
    """Return a tuple of transient exception types suitable for retry."""
    import httpx
    return (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.RemoteProtocolError,
        ConnectionError,
        TimeoutError,
    )


def _anthropic_errors():
    """Anthropic API transient errors."""
    try:
        import anthropic
        return (
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
            anthropic.InternalServerError,
            anthropic.RateLimitError,
        )
    except ImportError:
        return ()


CLAUDE_RETRY = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    jitter=True,
    # Populated at first use via property-like pattern below
)

GITHUB_RETRY = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=15.0,
    jitter=True,
)

JIRA_RETRY = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=15.0,
    jitter=True,
)


def _init_retry_configs() -> None:
    """
    Populate retryable tuples after all dependencies are importable.
    Call once from app startup (main.py) or lazily on first use.
    """
    global CLAUDE_RETRY, GITHUB_RETRY, JIRA_RETRY

    transient = _transient_errors()
    anthropic_errs = _anthropic_errors()

    CLAUDE_RETRY = RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=30.0,
        jitter=True,
        retryable=anthropic_errs + transient,
    )
    GITHUB_RETRY = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=15.0,
        jitter=True,
        retryable=transient,
    )
    JIRA_RETRY = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=15.0,
        jitter=True,
        retryable=transient,
    )
