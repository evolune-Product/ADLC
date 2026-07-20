import base64
import httpx


def _headers(email: str, api_token: str) -> dict:
    creds = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    return {"Authorization": f"Basic {creds}", "Accept": "application/json"}


def test_connection(workspace_url: str, email: str, api_token: str) -> dict:
    try:
        resp = httpx.get(
            f"{workspace_url.rstrip('/')}/rest/api/3/myself",
            headers=_headers(email, api_token),
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {"success": True, "display_name": data.get("displayName", "")}
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_projects(workspace_url: str, email: str, api_token: str) -> list[dict]:
    resp = httpx.get(
        f"{workspace_url.rstrip('/')}/rest/api/3/project?maxResults=100",
        headers=_headers(email, api_token),
        timeout=15,
    )
    data = resp.json()
    if not isinstance(data, list):
        return []
    return [{"key": p["key"], "name": p["name"], "id": p["id"]} for p in data]


def sync_tickets(workspace_url: str, email: str, api_token: str, project_key: str) -> list[dict]:
    """Fetch up to 100 tickets from Jira for a given project key."""
    jql = f"project={project_key} ORDER BY updated DESC"
    resp = httpx.get(
        f"{workspace_url.rstrip('/')}/rest/api/3/search",
        params={
            "jql": jql,
            "maxResults": 100,
            "fields": "summary,description,issuetype,priority,status,assignee",
        },
        headers=_headers(email, api_token),
        timeout=20,
    )
    data = resp.json()
    issues = data.get("issues", [])
    results = []
    for issue in issues:
        fields = issue.get("fields", {})
        desc = _extract_text(fields.get("description"))
        results.append({
            "jira_id": issue["key"],
            "title": fields.get("summary", ""),
            "description": desc,
            "type": ((fields.get("issuetype") or {}).get("name", "") or "").lower(),
            "priority": ((fields.get("priority") or {}).get("name", "") or "").lower(),
            "status": (fields.get("status") or {}).get("name", ""),
            "assignee": ((fields.get("assignee") or {}) or {}).get("displayName", "") or "",
            "jira_url": f"{workspace_url.rstrip('/')}/browse/{issue['key']}",
            "raw_payload": issue,
        })
    return results


def _extract_text(node) -> str:
    """Recursively extract plain text from Atlassian Document Format (ADF)."""
    if not node:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        text = node.get("text", "")
        children = node.get("content", [])
        parts = [text] + [_extract_text(c) for c in children]
        return " ".join(p for p in parts if p).strip()
    return ""
