"""
app.core — cross-cutting utilities.

Re-exported for convenient single-import access:
  from app.core import get_logger, AppError, NotFoundError, with_retry, CLAUDE_RETRY
"""
from app.core.errors import (
    AppError,
    NotFoundError,
    ForbiddenError,
    ConflictError,
    ValidationError,
    ExternalServiceError,
    RateLimitError,
    register_error_handlers,
)
from app.core.logging import (
    get_logger,
    configure_logging,
    bind_context,
    new_request_id,
    request_id_var,
    user_id_var,
    run_id_var,
)
from app.core.retry import (
    RetryConfig,
    with_retry,
    CLAUDE_RETRY,
    GITHUB_RETRY,
    JIRA_RETRY,
    _init_retry_configs,
)
from app.core.security import (
    get_fernet,
    load_fernet_key,
    limiter,
    AUTH_LOGIN_LIMIT,
    AUTH_REGISTER_LIMIT,
)

__all__ = [
    # errors
    "AppError", "NotFoundError", "ForbiddenError", "ConflictError",
    "ValidationError", "ExternalServiceError", "RateLimitError",
    "register_error_handlers",
    # logging
    "get_logger", "configure_logging", "bind_context", "new_request_id",
    "request_id_var", "user_id_var", "run_id_var",
    # retry
    "RetryConfig", "with_retry", "CLAUDE_RETRY", "GITHUB_RETRY", "JIRA_RETRY",
    "_init_retry_configs",
    # security
    "get_fernet", "load_fernet_key", "limiter", "AUTH_LOGIN_LIMIT", "AUTH_REGISTER_LIMIT",
]
