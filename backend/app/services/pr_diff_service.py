"""
PR diff fetching — shared by the internal runs router and the public API, so
the VS Code extension's diff view and the web UI's PrDiffViewer read the exact
same files, capped and shaped the exact same way.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.connection import Connection
from app.models.project import Project
from app.models.run import Run
from app.services.encryption import decrypt_token

MAX_FILES = 20


class DiffError(Exception):
    """Carries an HTTP status code so each router can raise its own exception type."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def get_pr_files(db: Session, run: Run) -> list[dict]:
    if not run.pr_number:
        raise DiffError(404, "No PR associated with this run")

    project = db.query(Project).filter(Project.id == run.project_id).first()
    if not project or not project.repo_connection_id or not project.repo_name:
        raise DiffError(422, "Project has no repository configured")

    conn = db.query(Connection).filter(Connection.id == project.repo_connection_id).first()
    if not conn or not conn.access_token:
        raise DiffError(422, "Repository connection not found")

    from github import Github

    try:
        token = decrypt_token(conn.access_token)
        repo = Github(token).get_repo(project.repo_name)
        pr = repo.get_pull(run.pr_number)
        return [
            {"filename": f.filename, "status": f.status,
             "additions": f.additions, "deletions": f.deletions, "patch": f.patch or ""}
            for f in list(pr.get_files())[:MAX_FILES]
        ]
    except DiffError:
        raise
    except Exception as e:
        raise DiffError(502, f"Failed to fetch PR diff: {e}")
