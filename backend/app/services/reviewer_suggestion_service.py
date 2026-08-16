"""
Reviewer suggestion — "suggest the right peer reviewer based on past commit
history" is a named Rovo Dev capability this platform didn't have: every PR
the agent opened went out with zero reviewers requested, leaving a human to
notice it existed and pick someone. That's an extra manual step competitors
don't make the human take.

Pure ranking logic lives here so it's unit-testable without a GitHub token or
network call. The GitHub-specific fetch (`suggest_github_reviewers`) is a thin
wrapper that gathers commit authors per touched file and hands them to `rank`.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

MAX_REVIEWERS = 2
COMMITS_PER_FILE = 15


def rank(authors_by_file: dict[str, list[str]], *, exclude: set[str], max_reviewers: int = MAX_REVIEWERS) -> list[str]:
    """
    Pure: authors_by_file maps changed file path -> list of past commit author
    logins for that file (most recent first, duplicates included so frequency
    counts). Returns up to max_reviewers logins, most-touched-files-first,
    excluding the given set (the PR's own author, bots, etc).
    """
    tally: dict[str, int] = {}
    for authors in authors_by_file.values():
        seen_in_file: set[str] = set()
        for login in authors:
            if not login or login in exclude or login in seen_in_file:
                continue
            seen_in_file.add(login)
            tally[login] = tally.get(login, 0) + 1

    ranked = sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))
    return [login for login, _ in ranked[:max_reviewers]]


def suggest_github_reviewers(repo, files: list[dict], *, exclude_login: str | None = None) -> list[str]:
    """
    repo: a PyGithub Repository. files: the same [{"path": ...}, ...] shape
    used elsewhere in the dev-agent pipeline. Best-effort — GitHub rate limits
    or a brand-new repo with no history must never block PR creation, so any
    failure here is caught by the caller and simply means no reviewer request.
    """
    exclude = {exclude_login} if exclude_login else set()
    authors_by_file: dict[str, list[str]] = {}
    for f in files:
        path = f.get("path") if isinstance(f, dict) else f
        if not path:
            continue
        try:
            commits = repo.get_commits(path=path)
            logins = [c.author.login for c in list(commits)[:COMMITS_PER_FILE] if c.author]
        except Exception:
            logins = []
        authors_by_file[path] = logins

    return rank(authors_by_file, exclude=exclude)
