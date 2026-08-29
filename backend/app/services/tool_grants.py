"""
Tool-grant authorization — the single place `ToolGrant` rows are interpreted.

Both the plugin registry (step 11) and the BYO API registry (step 12) call
`can_use_tool()` rather than each re-implementing the allow-list check, so
there is exactly one place this default-open-until-scoped rule lives.

DEFAULT-OPEN-UNTIL-SCOPED (repeated here because it is the load-bearing
decision): a plugin_key/company_api_id with ZERO ToolGrant rows is available
to any caller in the org — this is what keeps every existing org that has
never heard of ToolGrant working exactly as before. The moment ANY ToolGrant
row exists for that target, it becomes an allow-list: only the specific
agent/department/team/workflow ids granted may use it from then on, and an
unlisted caller is refused even though the tool is "connected".
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.integration import ToolGrant


def can_use_tool(
    db: Session,
    org_id,
    *,
    plugin_key: str | None = None,
    company_api_id=None,
    agent_id=None,
    department_id=None,
    team_id=None,
    workflow_id=None,
) -> bool:
    """
    True if the given caller identity (agent/department/team/workflow — any
    subset may be supplied, e.g. an agent_task node also knows its
    department) may use the plugin or CompanyApi identified by plugin_key /
    company_api_id in this org.

    Exactly one of plugin_key / company_api_id should be given, matching the
    ToolGrant row shape.
    """
    if not plugin_key and not company_api_id:
        raise ValueError("can_use_tool requires plugin_key or company_api_id")

    q = db.query(ToolGrant).filter(ToolGrant.organization_id == org_id)
    if plugin_key:
        q = q.filter(ToolGrant.plugin_key == plugin_key)
    else:
        q = q.filter(ToolGrant.company_api_id == company_api_id)

    grants = q.all()
    if not grants:
        # No grants exist for this target at all — default-open.
        return True

    candidates: list[tuple[str, uuid.UUID]] = []
    if agent_id:
        candidates.append(("agent", agent_id))
    if department_id:
        candidates.append(("department", department_id))
    if team_id:
        candidates.append(("team", team_id))
    if workflow_id:
        candidates.append(("workflow", workflow_id))

    for grant in grants:
        for gtype, gid in candidates:
            if grant.grantee_type == gtype and str(grant.grantee_id) == str(gid):
                return True
    return False
