import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, connections, skills, agents, pods, projects, tickets, runs, audit
from app.routers import dashboard, settings as settings_router
from app.routers import billing, notifications, insights, governance, catalog, memory, public_api, mcp, sprint
from app.routers import workspace, integrations
from app.routers import departments, teams, work, desk, workflows
from app.routers.organizations import router as orgs_router, inv_router
from app.middleware.audit_middleware import AuditMiddleware

fastapi_app = FastAPI(title="Agentic SDLC API", version="1.1.0")

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
fastapi_app.add_middleware(AuditMiddleware)

fastapi_app.include_router(auth.router,             prefix="/auth",       tags=["auth"])
fastapi_app.include_router(connections.router,      prefix="/connections", tags=["connections"])
fastapi_app.include_router(skills.router,           prefix="/skills",     tags=["skills"])
fastapi_app.include_router(agents.router,           prefix="/agents",     tags=["agents"])
fastapi_app.include_router(pods.router,             prefix="/pods",       tags=["pods"])
fastapi_app.include_router(projects.router,         prefix="/projects",   tags=["projects"])
fastapi_app.include_router(tickets.router,          prefix="",            tags=["tickets"])
fastapi_app.include_router(runs.router,             prefix="",            tags=["runs"])
fastapi_app.include_router(audit.router,            prefix="/audit",      tags=["audit"])
fastapi_app.include_router(dashboard.router,        prefix="",            tags=["dashboard"])
fastapi_app.include_router(settings_router.router,  prefix="/settings",   tags=["settings"])
fastapi_app.include_router(orgs_router,             prefix="/orgs",        tags=["organizations"])
fastapi_app.include_router(inv_router,              prefix="/invitations",  tags=["invitations"])

# ── Phase 11: commercial, governance and intelligence layer ───────────────────
fastapi_app.include_router(billing.router,        prefix="/billing",       tags=["billing"])
fastapi_app.include_router(notifications.router,  prefix="/notifications", tags=["notifications"])
fastapi_app.include_router(insights.router,       prefix="",               tags=["insights"])
fastapi_app.include_router(governance.router,     prefix="",               tags=["governance"])
fastapi_app.include_router(catalog.router,        prefix="",               tags=["catalog"])
fastapi_app.include_router(memory.router,         prefix="",               tags=["memory"])
fastapi_app.include_router(sprint.router,         prefix="",               tags=["sprint"])

# ── Phase 12: the collaboration layer ────────────────────────────────────────
# Mounted at the root because its paths are already namespaced under
# /workspace, and a /workspace prefix here would make them /workspace/workspace.
fastapi_app.include_router(workspace.router,      prefix="",               tags=["workspace"])
# Model providers and plugins. Root-mounted: the paths are already namespaced
# under /providers and /plugins, and the catalogue endpoints are read by the
# settings UI on every load.
fastapi_app.include_router(integrations.router,   prefix="",               tags=["integrations"])
# Public, API-key authenticated surface for CI and customer automation
fastapi_app.include_router(public_api.router,     prefix="/v1",            tags=["public-api"])
# MCP lives at the root, not under /v1: an MCP client config takes a URL and
# the spec's convention is a bare /mcp. It is versioned by protocolVersion in
# the handshake, not by a path segment.
fastapi_app.include_router(mcp.router,            prefix="",               tags=["mcp"])

# ── Phase 13: Company OS foundation ────────────────────────────────────────
# Departments, teams and generic Work requests — the org-chart and non-
# engineering work layer laid on top of the existing org/RBAC foundation.
# Engineering keeps running through projects/tickets/runs entirely
# unchanged; these are additive, org-scoped resources alongside it.
fastapi_app.include_router(departments.router,    prefix="/departments",   tags=["departments"])
# teams.py declares its own routes as "/{department_id}/teams/..." so a team's
# URL nests under its department (/departments/{id}/teams/...) — same prefix
# as departments.router, a second APIRouter rather than one file for two
# related-but-distinct resources.
fastapi_app.include_router(teams.router,          prefix="/departments",   tags=["teams"])
fastapi_app.include_router(work.router,           prefix="/work",          tags=["work"])
fastapi_app.include_router(desk.router,           prefix="/desk",          tags=["desk"])
fastapi_app.include_router(workflows.router,      prefix="/workflows",     tags=["workflows"])


@fastapi_app.get("/health")
def health():
    return {"status": "ok", "version": "1.1.0", "mode": settings.deployment_mode}


# Wrap FastAPI with socket.io so both share the same process.
# socket.io handles /socket.io/ paths; everything else goes to FastAPI.
from socket_app import sio  # noqa: E402 — import after sio is configured

app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
