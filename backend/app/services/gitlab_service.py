"""
GitLab connector — the second repo host.

GitLab shops (often larger, more regulated enterprises) could not use the
platform at all while it was GitHub-only, and "works with the SCM we already
have" is a procurement gate, not a nice-to-have. This client covers exactly what
the agent pipeline needs: list projects, read files, create a branch, commit,
open a merge request, comment on it, and merge.

Uses the REST v4 API over httpx — no python-gitlab dependency.
"""
from __future__ import annotations

import base64
import logging
from urllib.parse import quote

import httpx

log = logging.getLogger(__name__)

DEFAULT_HOST = "https://gitlab.com"


class GitLabError(RuntimeError):
    pass


class GitLabClient:
    def __init__(self, token: str, host: str | None = None, timeout: float = 30.0):
        self.token = token
        self.base = f"{(host or DEFAULT_HOST).rstrip('/')}/api/v4"
        self.timeout = timeout

    # ── plumbing ──────────────────────────────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs):
        headers = {"PRIVATE-TOKEN": self.token, "Content-Type": "application/json"}
        headers.update(kwargs.pop("headers", {}))
        with httpx.Client(timeout=self.timeout) as client:
            r = client.request(method, f"{self.base}{path}", headers=headers, **kwargs)
        if r.status_code >= 400:
            raise GitLabError(f"GitLab {method} {path} → {r.status_code}: {r.text[:300]}")
        return r.json() if r.content else None

    @staticmethod
    def _pid(project: str) -> str:
        """GitLab wants the namespaced path URL-encoded ('group/repo' → 'group%2Frepo')."""
        return quote(str(project), safe="")

    # ── read ──────────────────────────────────────────────────────────────────

    def test(self) -> dict:
        return self._request("GET", "/user")

    def list_projects(self, limit: int = 100) -> list[dict]:
        rows = self._request(
            "GET", "/projects",
            params={"membership": "true", "per_page": min(limit, 100),
                    "order_by": "last_activity_at", "simple": "true"},
        ) or []
        return [
            {
                "id": p["id"],
                "full_name": p["path_with_namespace"],
                "name": p["name"],
                "default_branch": p.get("default_branch") or "main",
                "private": p.get("visibility") != "public",
                "url": p.get("web_url"),
            }
            for p in rows
        ]

    def default_branch(self, project: str) -> str:
        return (self._request("GET", f"/projects/{self._pid(project)}") or {}).get("default_branch") or "main"

    def get_file(self, project: str, path: str, ref: str) -> str | None:
        try:
            data = self._request(
                "GET", f"/projects/{self._pid(project)}/repository/files/{quote(path, safe='')}",
                params={"ref": ref},
            )
        except GitLabError:
            return None
        if not data or "content" not in data:
            return None
        return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")

    def read_source_files(self, project: str, *, max_files: int, extensions: set[str],
                          skip_dirs: set[str], max_bytes: int) -> list[tuple[str, str]]:
        """Tree walk used by the codebase-memory indexer."""
        ref = self.default_branch(project)
        tree = self._request(
            "GET", f"/projects/{self._pid(project)}/repository/tree",
            params={"recursive": "true", "per_page": 100, "ref": ref},
        ) or []

        out: list[tuple[str, str]] = []
        for node in tree:
            if len(out) >= max_files:
                break
            if node.get("type") != "blob":
                continue
            path = node["path"]
            if any(part in skip_dirs for part in path.split("/")):
                continue
            if not any(path.endswith(ext) for ext in extensions):
                continue
            content = self.get_file(project, path, ref)
            if content and len(content) <= max_bytes and content.strip():
                out.append((path, content))
        return out

    # ── write ─────────────────────────────────────────────────────────────────

    def create_branch(self, project: str, branch: str, ref: str) -> dict:
        try:
            return self._request("POST", f"/projects/{self._pid(project)}/repository/branches",
                                 json={"branch": branch, "ref": ref})
        except GitLabError as exc:
            if "already exists" in str(exc):
                return {"name": branch, "existed": True}
            raise

    def commit_files(self, project: str, branch: str, message: str, files: list[dict]) -> dict:
        """`files` = [{path, content, action?}] — one atomic commit, like the GitHub path."""
        actions = []
        for f in files:
            if f.get("action") == "delete":
                actions.append({"action": "delete", "file_path": f["path"]})
                continue
            exists = self.get_file(project, f["path"], branch) is not None
            actions.append({
                "action": "update" if exists else "create",
                "file_path": f["path"],
                "content": f["content"],
            })

        return self._request(
            "POST", f"/projects/{self._pid(project)}/repository/commits",
            json={"branch": branch, "commit_message": message, "actions": actions},
        )

    def create_merge_request(self, project: str, *, source: str, target: str,
                             title: str, description: str) -> dict:
        mr = self._request(
            "POST", f"/projects/{self._pid(project)}/merge_requests",
            json={"source_branch": source, "target_branch": target,
                  "title": title, "description": description},
        )
        return {"url": mr["web_url"], "number": mr["iid"], "id": mr["id"]}

    def comment(self, project: str, mr_iid: int, body: str) -> dict:
        return self._request("POST", f"/projects/{self._pid(project)}/merge_requests/{mr_iid}/notes",
                             json={"body": body})

    def merge_request_changes(self, project: str, mr_iid: int) -> list[dict]:
        data = self._request("GET", f"/projects/{self._pid(project)}/merge_requests/{mr_iid}/changes") or {}
        return [
            {
                "filename": c.get("new_path") or c.get("old_path"),
                "status": "added" if c.get("new_file") else ("removed" if c.get("deleted_file") else "modified"),
                "additions": 0,
                "deletions": 0,
                "patch": c.get("diff", ""),
            }
            for c in data.get("changes", [])[:20]
        ]

    def merge(self, project: str, mr_iid: int) -> dict:
        try:
            mr = self._request("PUT", f"/projects/{self._pid(project)}/merge_requests/{mr_iid}/merge",
                               json={"squash": True})
            return {"merged": True, "message": "Merged successfully", "sha": (mr or {}).get("sha")}
        except GitLabError as exc:
            return {"merged": False, "message": str(exc)}

    def merge_branches(self, project: str, source: str, target: str, message: str) -> dict:
        """Environment promotion: open an MR source→target and merge it immediately."""
        try:
            mr = self.create_merge_request(project, source=source, target=target,
                                           title=message, description=message)
            result = self.merge(project, mr["number"])
            result.setdefault("message", message)
            return result
        except GitLabError as exc:
            text = str(exc).lower()
            if "already exists" in text or "no changes" in text:
                return {"merged": True, "message": f"{source} is already up-to-date with {target}"}
            return {"merged": False, "message": str(exc)}
