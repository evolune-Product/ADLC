import httpx
from app.config import settings

GITHUB_API = "https://api.github.com"


def get_oauth_url(state: str) -> str:
    params = (
        f"client_id={settings.github_client_id}"
        f"&redirect_uri={settings.github_redirect_uri}"
        f"&scope=repo,user"
        f"&state={state}"
    )
    return f"https://github.com/login/oauth/authorize?{params}"


def exchange_code(code: str) -> str:
    resp = httpx.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": settings.github_redirect_uri,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    return resp.json().get("access_token", "")


def get_user_info(token: str) -> dict:
    resp = httpx.get(
        f"{GITHUB_API}/user",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
        timeout=10,
    )
    return resp.json()


def get_repos(token: str) -> list[dict]:
    resp = httpx.get(
        f"{GITHUB_API}/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
        timeout=15,
    )
    repos = resp.json()
    if not isinstance(repos, list):
        return []
    return [
        {
            "id": r["id"],
            # Both fields, matching GitHub's own API shape: `name` is the short
            # repo name, `full_name` is "owner/repo". The project wizard's repo
            # picker (useConnectionRepos) keys and displays by full_name — this
            # used to collapse both into `name` holding the full_name value and
            # never send full_name at all, which rendered every <option> blank.
            "name": r["name"],
            "full_name": r["full_name"],
            "private": r["private"],
            "default_branch": r["default_branch"],
            "description": r.get("description") or "",
        }
        for r in repos
    ]


def list_issues(token: str, full_name: str) -> list[dict]:
    """Issues on a repo, mapped to the same shape `jira_service.sync_tickets`
    returns — lets a project use a repo it already connected as its ticket
    source with no separate tracker account. GitHub's issues endpoint also
    returns pull requests; those carry a "pull_request" key issues never do,
    which is how they're filtered out here."""
    resp = httpx.get(
        f"{GITHUB_API}/repos/{full_name}/issues",
        params={"state": "all", "per_page": 100, "sort": "updated"},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
        timeout=20,
    )
    items = resp.json()
    if not isinstance(items, list):
        return []

    results = []
    for issue in items:
        if "pull_request" in issue:
            continue
        labels = {str(l.get("name", "")).lower() for l in (issue.get("labels") or []) if isinstance(l, dict)}
        if "bug" in labels:
            issue_type = "bug"
        elif labels & {"enhancement", "feature"}:
            issue_type = "feature"
        else:
            issue_type = "task"
        results.append({
            "jira_id": f"GH-{issue['number']}",
            "title": issue.get("title", ""),
            "description": issue.get("body") or "",
            "type": issue_type,
            # GitHub issues have no native priority field.
            "priority": "medium",
            "status": "Done" if issue.get("state") == "closed" else "To Do",
            "assignee": (issue.get("assignee") or {}).get("login") or "",
            "jira_url": issue.get("html_url", ""),
            "raw_payload": issue,
        })
    return results


def test_connection(token: str) -> bool:
    try:
        resp = httpx.get(
            f"{GITHUB_API}/user",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False
