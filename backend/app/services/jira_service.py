import base64
import re
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


# ─── Write-back ───────────────────────────────────────────────────────────────
#
# Everything above reads. These write, and they are what closes the loop: a
# ticket that goes into a run and never changes leaves the humans watching Jira
# with no idea the work happened. Every function here returns a bool and
# swallows nothing — the caller decides whether a failed write-back is worth
# surfacing, because it must never be worth failing a deploy over.


def _adf(text: str) -> dict:
    """
    Jira Cloud's comment body is Atlassian Document Format, not a string.

    Only the two node types we actually need: paragraphs, and links inside
    them. Anything richer would mean shipping an ADF builder for a feature
    whose entire output is "here is a PR link and a status".
    """
    content = []
    for line in (text or "").split("\n"):
        if not line.strip():
            continue
        # Split on the first bare URL so it renders as a link rather than as
        # text a human has to select and copy.
        parts = re.split(r"(https?://\S+)", line)
        nodes = []
        for part in parts:
            if not part:
                continue
            if part.startswith("http"):
                nodes.append({"type": "text", "text": part,
                              "marks": [{"type": "link", "attrs": {"href": part}}]})
            else:
                nodes.append({"type": "text", "text": part})
        content.append({"type": "paragraph", "content": nodes})

    if not content:
        content = [{"type": "paragraph", "content": [{"type": "text", "text": " "}]}]
    return {"type": "doc", "version": 1, "content": content}


def add_comment(workspace_url: str, email: str, api_token: str,
                issue_key: str, body: str) -> bool:
    resp = httpx.post(
        f"{workspace_url.rstrip('/')}/rest/api/3/issue/{issue_key}/comment",
        headers={**_headers(email, api_token), "Content-Type": "application/json"},
        json={"body": _adf(body)},
        timeout=15,
    )
    return resp.status_code < 300


def get_transitions(workspace_url: str, email: str, api_token: str,
                    issue_key: str) -> list[dict]:
    """
    The transitions available *from the issue's current state*.

    Jira does not let you set a status directly — you have to find the
    transition that leads to it, and which transitions exist depends on where
    the issue is right now and on the project's workflow. This is why
    write-back has to look them up per issue rather than caching an id.
    """
    resp = httpx.get(
        f"{workspace_url.rstrip('/')}/rest/api/3/issue/{issue_key}/transitions",
        headers=_headers(email, api_token),
        timeout=15,
    )
    if resp.status_code >= 300:
        return []
    return [
        {"id": t["id"], "name": t.get("name", ""),
         "to": (t.get("to") or {}).get("name", "")}
        for t in resp.json().get("transitions", [])
    ]


def transition_issue(workspace_url: str, email: str, api_token: str,
                     issue_key: str, target_status: str) -> bool:
    """
    Move an issue to a named status, if a transition to it exists right now.

    Matches on the destination status name and falls back to the transition's
    own name, because teams rename both. Returns False rather than raising when
    no route exists: a customer whose workflow has no "In Review" column has a
    configuration mismatch, not an outage.
    """
    wanted = (target_status or "").strip().lower()
    if not wanted:
        return False

    for t in get_transitions(workspace_url, email, api_token, issue_key):
        if t["to"].lower() == wanted or t["name"].lower() == wanted:
            resp = httpx.post(
                f"{workspace_url.rstrip('/')}/rest/api/3/issue/{issue_key}/transitions",
                headers={**_headers(email, api_token), "Content-Type": "application/json"},
                json={"transition": {"id": t["id"]}},
                timeout=15,
            )
            return resp.status_code < 300
    return False
