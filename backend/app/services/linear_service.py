"""
Linear connector — the ticket source fast-growing startups actually use.

Jira is the enterprise incumbent; Linear is where the Series A/B teams in the
design-partner profile live, and they cannot use a Jira-only platform at all.
Linear's API is GraphQL; this wraps the four operations the pipeline needs:
authenticate, list teams, sync issues, and write status back.
"""
from __future__ import annotations

import logging

import httpx

log = logging.getLogger(__name__)

API_URL = "https://api.linear.app/graphql"


class LinearError(RuntimeError):
    pass


class LinearClient:
    def __init__(self, token: str, timeout: float = 30.0):
        self.token = token
        self.timeout = timeout

    def _query(self, query: str, variables: dict | None = None) -> dict:
        # Linear accepts a personal API key raw, and an OAuth token as Bearer.
        auth = self.token if self.token.startswith("lin_api") else f"Bearer {self.token}"
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(API_URL, headers={"Authorization": auth,
                                              "Content-Type": "application/json"},
                            json={"query": query, "variables": variables or {}})
        if r.status_code >= 400:
            raise LinearError(f"Linear API {r.status_code}: {r.text[:300]}")
        data = r.json()
        if data.get("errors"):
            raise LinearError(f"Linear GraphQL error: {data['errors'][0].get('message')}")
        return data.get("data", {})

    # ── read ──────────────────────────────────────────────────────────────────

    def test(self) -> dict:
        data = self._query("{ viewer { id name email } }")
        return data.get("viewer", {})

    def list_teams(self) -> list[dict]:
        data = self._query("{ teams(first: 100) { nodes { id key name } } }")
        return [
            {"key": t["key"], "id": t["id"], "name": t["name"]}
            for t in data.get("teams", {}).get("nodes", [])
        ]

    def list_issues(self, team_key: str, limit: int = 50) -> list[dict]:
        """Returns dicts shaped like the platform's Ticket model (jira_id etc.)."""
        query = """
        query Issues($key: String!, $first: Int!) {
          issues(first: $first, filter: { team: { key: { eq: $key } } },
                 orderBy: updatedAt) {
            nodes {
              id identifier title description url priorityLabel
              state { name type }
              assignee { name email }
              labels(first: 10) { nodes { name } }
            }
          }
        }"""
        data = self._query(query, {"key": team_key, "first": min(limit, 100)})
        out = []
        for n in data.get("issues", {}).get("nodes", []):
            labels = [l["name"] for l in (n.get("labels") or {}).get("nodes", [])]
            out.append({
                "jira_id": n["identifier"],           # shared "external ticket id" column
                "external_id": n["id"],
                "title": n["title"],
                "description": n.get("description") or "",
                "type": _infer_type(labels),
                "priority": n.get("priorityLabel") or "None",
                "status": (n.get("state") or {}).get("name"),
                "assignee": ((n.get("assignee") or {}) or {}).get("name"),
                "url": n.get("url"),
                "raw": n,
            })
        return out

    # ── write ─────────────────────────────────────────────────────────────────

    def state_id(self, team_key: str, state_name: str) -> str | None:
        query = """
        query States($key: String!) {
          workflowStates(first: 50, filter: { team: { key: { eq: $key } } }) {
            nodes { id name type }
          }
        }"""
        for s in self._query(query, {"key": team_key}).get("workflowStates", {}).get("nodes", []):
            if s["name"].lower() == state_name.lower():
                return s["id"]
        return None

    def move_issue(self, issue_id: str, state_id: str) -> bool:
        mutation = """
        mutation Move($id: String!, $stateId: String!) {
          issueUpdate(id: $id, input: { stateId: $stateId }) { success }
        }"""
        data = self._query(mutation, {"id": issue_id, "stateId": state_id})
        return bool(data.get("issueUpdate", {}).get("success"))

    def comment(self, issue_id: str, body: str) -> bool:
        mutation = """
        mutation Comment($id: String!, $body: String!) {
          commentCreate(input: { issueId: $id, body: $body }) { success }
        }"""
        data = self._query(mutation, {"id": issue_id, "body": body})
        return bool(data.get("commentCreate", {}).get("success"))


def _infer_type(labels: list[str]) -> str:
    lowered = {l.lower() for l in labels}
    if lowered & {"bug", "defect"}:
        return "Bug"
    if lowered & {"feature", "enhancement"}:
        return "Story"
    if "chore" in lowered:
        return "Task"
    return "Task"
