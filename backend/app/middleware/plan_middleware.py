"""
Plan enforcement middleware - checks resource limits before creation.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User
from app.services.plan_service import plan_service
from app.middleware.auth_middleware import get_user_from_token


class PlanEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce plan limits on resource creation.

    Checks if user has reached their plan limits before allowing
    POST requests to create resources.
    """

    # Map route paths to resource types
    RESOURCE_MAP = {
        "/projects": "projects",
        "/agents": "agents",
        "/pods": "pods",
        "/skills": "skills",
        "/connections": ("github_connections", "jira_connections"),  # Depends on connection type
    }

    async def dispatch(self, request: Request, call_next):
        """Check plan limits for POST requests to resource endpoints."""

        # Only check POST requests (creation)
        if request.method != "POST":
            return await call_next(request)

        # Check if this is a resource creation endpoint.
        # scope["path"], not request.url.path — see rate_limit_middleware.py's
        # comment on the same line shape: it's the raw, routing-authoritative
        # path, immune to the Host-header/path reconstruction bugs fixed in
        # Starlette 1.3.1 that could desync request.url.path from real routing.
        path = request.scope["path"]
        resource_type = None

        for route_prefix, res_type in self.RESOURCE_MAP.items():
            if path.startswith(route_prefix) and path == route_prefix:
                resource_type = res_type
                break

        # Not a resource creation endpoint
        if not resource_type:
            return await call_next(request)

        # Get user from token
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return await call_next(request)

        db = SessionLocal()
        try:
            user = get_user_from_token(token, db)
            if not user:
                return await call_next(request)

            # For connections, we need to check the connection type from request body
            if isinstance(resource_type, tuple):
                # This is the connections endpoint
                # We'll let it pass here and check in the router instead
                # (need to read request body to determine github vs jira)
                return await call_next(request)

            # Check limit
            plan_service.check_resource_limit(user, resource_type, db)

        except Exception as e:
            # Let FastAPI exception handlers handle it
            raise
        finally:
            db.close()

        return await call_next(request)
