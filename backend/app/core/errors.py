"""
Canonical exception hierarchy and FastAPI error handler registration.

All errors produce a uniform JSON shape:
  { "error_code": str, "message": str, "detail": str | None, "request_id": str | None }

Usage:
  from app.core.errors import NotFoundError, register_error_handlers
  raise NotFoundError("run", run_id)
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


# ─── Exception hierarchy ──────────────────────────────────────────────────────

class AppError(Exception):
    """Base class for all application errors."""
    http_status: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class NotFoundError(AppError):
    http_status = 404
    error_code = "not_found"

    def __init__(self, entity: str, id: Any = None):
        msg = f"{entity} not found" if id is None else f"{entity} '{id}' not found"
        super().__init__(msg)


class ForbiddenError(AppError):
    http_status = 403
    error_code = "forbidden"

    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message)


class ConflictError(AppError):
    http_status = 409
    error_code = "conflict"


class ValidationError(AppError):
    http_status = 422
    error_code = "validation_error"


class ExternalServiceError(AppError):
    http_status = 502
    error_code = "external_service_error"

    def __init__(self, service: str, message: str, detail: str | None = None):
        super().__init__(f"{service}: {message}", detail)
        self.service = service


class RateLimitError(AppError):
    http_status = 429
    error_code = "rate_limit_exceeded"

    def __init__(self, message: str = "Too many requests. Please slow down."):
        super().__init__(message)


# ─── Response builder ─────────────────────────────────────────────────────────

def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    detail: str | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "detail": detail,
            "request_id": request_id,
        },
    )


def _get_request_id(request: Request) -> str | None:
    return request.headers.get("x-request-id") or getattr(request.state, "request_id", None)


# ─── Handler registration ─────────────────────────────────────────────────────

def register_error_handlers(app: FastAPI) -> None:
    """Register canonical error handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(
            status_code=exc.http_status,
            error_code=exc.error_code,
            message=exc.message,
            detail=exc.detail,
            request_id=_get_request_id(request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Map common HTTP status codes to meaningful error_codes
        code_map = {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            409: "conflict",
            422: "validation_error",
            429: "rate_limit_exceeded",
            500: "internal_error",
            502: "bad_gateway",
            503: "service_unavailable",
        }
        error_code = code_map.get(exc.status_code, f"http_{exc.status_code}")
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _error_response(
            status_code=exc.status_code,
            error_code=error_code,
            message=detail,
            request_id=_get_request_id(request),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Flatten Pydantic v2 error list to a readable string
        messages = "; ".join(
            f"{' > '.join(str(loc) for loc in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        )
        return _error_response(
            status_code=422,
            error_code="validation_error",
            message="Request validation failed",
            detail=messages,
            request_id=_get_request_id(request),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the unhandled exception (import here to avoid circular at module load)
        try:
            from app.core.logging import get_logger
            log = get_logger(__name__)
            log.error("unhandled_exception", exc_info=exc, path=str(request.url.path))
        except Exception:
            print(f"[error_handler] logging failed for: {exc!r}")

        # Forward to Sentry if configured. We must do this manually because our
        # custom handler returns a JSONResponse — Sentry's ASGI middleware never
        # sees the raw exception once we catch it here.
        # AppError subclasses (404s, 403s, etc.) are expected business errors and
        # are deliberately excluded — only genuine bugs reach this handler.
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(exc)
        except Exception:
            pass  # never let Sentry break the error response path

        return _error_response(
            status_code=500,
            error_code="internal_error",
            message="An unexpected error occurred",
            request_id=_get_request_id(request),
        )
