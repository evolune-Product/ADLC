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
            "name": r["full_name"],
            "private": r["private"],
            "default_branch": r["default_branch"],
            "description": r.get("description") or "",
        }
        for r in repos
    ]


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
