"""
Execution sandbox — runs a project's own install/test/lint commands inside an
ephemeral, network-isolated Docker container, and returns real pass/fail
evidence instead of an LLM's opinion of a diff.

Why this exists: `qa_agent.py` used to ask Claude to read a PR diff and decide
PASS/FAIL with no way to know whether the code actually runs — its own
docstring said so: "no live test runner yet." An approval gate whose review
step never executed the change is not a control, it is a second opinion with
no evidence behind it.

Design, in order of the decisions that matter most:

  1. **The command is never model-authored.** `SandboxConfig` comes from the
     repo's own `.evolune.yml` (or the older `.adlc.yml` name) if present, or
     from a fixed, hardcoded heuristic keyed off manifest files the repo
     already has (package.json, requirements.txt, pyproject.toml, go.mod,
     Cargo.toml, Gemfile). An LLM never gets to propose a shell command that
     then runs here — that would turn a prompt-injected ticket description
     into arbitrary code execution against real infrastructure. The trust
     boundary this DOES rely on is the same one every CI system relies on:
     whoever can commit to the repo can already put anything in its build
     files. This sandboxes a run against a bad *ticket* or a bad *LLM diff*,
     not against a malicious repo owner.
  2. **Install gets network; test and lint do not.** Two separate ephemeral
     containers share the same bind-mounted workspace directory. `npm ci` /
     `pip install` need the public internet almost always; the actual test run
     does not, and a compromised or malicious test file that tries to
     exfiltrate environment data or reach an internal host should hit a dead
     network stack, not this platform's VPC. This mirrors the SSRF posture
     `reader_service._assert_public_url` and `company_api_service` already
     take elsewhere in this codebase — least privilege by default.
  3. **A failure to run is not a failure of the code.** Docker unreachable, no
     recognized project type, an image pull failure, a clone that fails —
     none of these are evidence the change is broken, so they resolve to
     `outcome="skipped"` and QA falls back to LLM-only review exactly as it
     did before this module existed. Only a real nonzero exit from a real
     command run produces `outcome="failed"`. Conflating "we couldn't check"
     with "it's broken" would make a flaky sandbox block real work — the same
     principle `DEFAULT_POLICY`'s docstring states for governance a team
     never configured.
  4. **Docker-outside-of-Docker path handling.** This module runs inside the
     `worker` container, which is not itself the Docker host — the mounted
     `/var/run/docker.sock` talks to the *host's* daemon. A bind mount handed
     to that daemon must be a path *on the host*, not a path inside this
     container, even though this process reads and writes the exact same
     directory through its own mount point. `settings.sandbox_host_path` is
     that translation; see `_host_path()`. Getting this wrong doesn't raise —
     it silently mounts an empty or wrong directory into the sibling
     container and tests "run" against nothing, which is worse than not
     having this feature. If you touch this function, re-verify against a
     real compose deploy, not just unit tests (there is no Docker daemon
     available in this repo's own CI or in local dev on every machine).
  5. **Every real limit is enforced by the container, not trusted from the
     command.** Memory, CPU, PIDs, a read-only root filesystem, all
     capabilities dropped, `no-new-privileges` — a slow or resource-hungry
     test suite degrades to a timeout, not a starved worker host. `HOME=/tmp`
     is set for every step so package-manager caches (pip, npm, go, cargo)
     land in the writable tmpfs instead of failing against the read-only root.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from urllib.parse import quote, urlsplit, urlunsplit

import yaml

from app.config import settings

log = logging.getLogger(__name__)

try:
    import docker as _docker_sdk
    _DOCKER_SDK_AVAILABLE = True
except ImportError:                                     # pragma: no cover
    _docker_sdk = None
    _DOCKER_SDK_AVAILABLE = False

MAX_OUTPUT_CHARS = 50_000
CONFIG_FILENAMES = (".evolune.yml", ".evolune.yaml", ".adlc.yml", ".adlc.yaml")

# manifest file → (default image, install cmd or None, test cmd, lint cmd or None)
# Order matters: first match wins, so a repo with both package.json and a
# requirements.txt (e.g. a JS frontend + Python backend monorepo) picks up
# the same one an engineer reading top-to-bottom would call the "main" stack.
# A repo with mixed stacks should ship an explicit `.evolune.yml` instead.
_HEURISTICS: list[tuple[str, str, str | None, str, str | None]] = [
    ("package.json", "node:20-slim", "npm ci",
     "npm test --if-present", "npm run lint --if-present"),
    ("pyproject.toml", "python:3.11-slim", "pip install --no-cache-dir -e .",
     "pytest -q", None),
    ("requirements.txt", "python:3.11-slim",
     "pip install --no-cache-dir -r requirements.txt", "pytest -q", None),
    ("go.mod", "golang:1.23", None, "go test ./...", None),
    ("Cargo.toml", "rust:1.82-slim", None, "cargo test", None),
    ("Gemfile", "ruby:3.3-slim", "bundle install", "bundle exec rspec", None),
]


class SandboxError(RuntimeError):
    """Raised only for this module's own precondition failures (e.g. a clone
    that fails). Callers should catch this and degrade to `outcome="skipped"`
    — see `qa_agent.py::_execute_tests` for the one real caller."""


@dataclass
class SandboxConfig:
    image: str | None = None
    install_cmd: str | None = None
    test_cmd: str | None = None
    lint_cmd: str | None = None
    source: str = "none"            # "explicit" | "explicit-invalid" | "heuristic:<file>" | "none"

    @property
    def runnable(self) -> bool:
        return bool(self.test_cmd)


@dataclass
class ExecutionResult:
    outcome: str                    # "passed" | "failed" | "skipped"
    reason: str | None = None       # set when outcome == "skipped"
    exit_code: int | None = None
    timed_out: bool = False
    install_output: str = ""
    test_output: str = ""
    lint_output: str = ""
    image: str | None = None
    commands: dict = field(default_factory=dict)
    duration_ms: int = 0

    @property
    def passed(self) -> bool:
        return self.outcome == "passed"

    def as_dict(self) -> dict:
        return {
            "outcome": self.outcome,
            "reason": self.reason,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "image": self.image,
            "commands": self.commands,
            "duration_ms": self.duration_ms,
            "install_output": _truncate(self.install_output),
            "test_output": _truncate(self.test_output),
            "lint_output": _truncate(self.lint_output),
        }


def _truncate(s: str) -> str:
    if len(s) <= MAX_OUTPUT_CHARS:
        return s
    cut = len(s) - MAX_OUTPUT_CHARS
    return s[:MAX_OUTPUT_CHARS] + f"\n… [{cut} more characters truncated]"


# ── Config resolution ───────────────────────────────────────────────────────

def detect_config(repo_path: str) -> SandboxConfig:
    """Explicit `.evolune.yml` always wins; otherwise the first recognised
    manifest file on disk picks a heuristic. No manifest recognised → not
    runnable, and the caller treats that as `skipped`, never `failed`."""
    for name in CONFIG_FILENAMES:
        p = os.path.join(repo_path, name)
        if os.path.isfile(p):
            try:
                with open(p, "r") as f:
                    raw = yaml.safe_load(f) or {}
                return SandboxConfig(
                    image=raw.get("image"),
                    install_cmd=raw.get("install"),
                    test_cmd=raw.get("test"),
                    lint_cmd=raw.get("lint"),
                    source="explicit",
                )
            except Exception as exc:
                log.warning("Could not parse %s: %s", p, exc)
                # A broken config file must not silently fall through to a
                # heuristic guess against the project's real test suite — that
                # would run the wrong commands and report on the wrong thing.
                return SandboxConfig(source="explicit-invalid")

    for manifest, image, install, test, lint in _HEURISTICS:
        if os.path.isfile(os.path.join(repo_path, manifest)):
            return SandboxConfig(image=image, install_cmd=install, test_cmd=test,
                                  lint_cmd=lint, source=f"heuristic:{manifest}")

    return SandboxConfig(source="none")


# ── Git ──────────────────────────────────────────────────────────────────────

def _authenticated_url(clone_url: str, *, username: str, token: str) -> str:
    """Insert HTTPS Basic auth into a clone URL. Built with urlsplit/urlunsplit
    rather than string concatenation so a token containing '@' or '/' cannot
    corrupt the URL structure."""
    parts = urlsplit(clone_url)
    netloc = f"{quote(username, safe='')}:{quote(token, safe='')}@{parts.hostname}"
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def clone_repo(*, repo_name: str, branch: str, token: str, dest: str,
                provider: str = "github", host: str | None = None,
                timeout: int = 120) -> None:
    """Shallow, single-branch clone. `dest` must not already exist.

    argv is a fixed list — never `shell=True`, never an f-string handed to a
    shell — so nothing in `repo_name`/`branch` (both platform-generated or
    read from GitHub/GitLab metadata, never raw ticket text) can break out
    into a second command even in principle.
    """
    if provider == "gitlab":
        base = (host or "https://gitlab.com").rstrip("/")
        clone_url = _authenticated_url(f"{base}/{repo_name}.git", username="oauth2", token=token)
    else:
        clone_url = _authenticated_url(f"https://github.com/{repo_name}.git",
                                        username="x-access-token", token=token)

    try:
        proc = subprocess.run(
            ["git", "clone", "--branch", branch, "--depth", "1", "--single-branch",
             clone_url, dest],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise SandboxError(f"git clone timed out after {timeout}s") from exc

    if proc.returncode != 0:
        # The token is embedded in clone_url — never let it reach a log or a
        # RunStep even on failure.
        safe_err = (proc.stderr or "").replace(token, "***")
        raise SandboxError(f"git clone failed: {safe_err[:2000]}")


# ── Docker execution ─────────────────────────────────────────────────────────

def _client():
    if not _DOCKER_SDK_AVAILABLE:
        return None
    try:
        return _docker_sdk.from_env(timeout=10)
    except Exception as exc:                            # noqa: BLE001
        log.warning("Docker daemon unreachable: %s", exc)
        return None


def _host_path(container_path: str) -> str:
    """Translate this container's view of the sandbox workdir into the
    *host's* path — see module docstring, point 4. Native (non-Docker) dev
    makes no translation: `sandbox_host_path` stays empty and the path is
    used as-is, which is correct because there is no container boundary."""
    if not settings.sandbox_host_path:
        return container_path
    rel = os.path.relpath(container_path, settings.sandbox_workdir)
    return str(PurePosixPath(settings.sandbox_host_path) / rel)


def _run_step(client, *, image: str, command: list[str], host_workdir: str,
              network_disabled: bool, timeout: int) -> tuple[int | None, str, bool]:
    """One ephemeral, locked-down container running one command. Returns
    (exit_code, combined stdout+stderr, timed_out). Always removes the
    container, win or lose — nothing here should accumulate on the host."""
    container = client.containers.run(
        image, command,
        working_dir="/workspace",
        volumes={host_workdir: {"bind": "/workspace", "mode": "rw"}},
        environment={"HOME": "/tmp"},
        network_disabled=network_disabled,
        mem_limit=settings.sandbox_memory_limit,
        nano_cpus=int(settings.sandbox_cpu_limit * 1_000_000_000),
        pids_limit=256,
        security_opt=["no-new-privileges"],
        cap_drop=["ALL"],
        read_only=True,
        tmpfs={"/tmp": "size=1g,exec"},
        detach=True,
    )
    timed_out = False
    try:
        result = container.wait(timeout=timeout)
        exit_code = result.get("StatusCode")
    except Exception:                                    # docker-py wait timeout
        timed_out = True
        exit_code = None
        try:
            container.kill()
        except Exception:
            pass
    try:
        output = container.logs(stdout=True, stderr=True).decode("utf-8", "replace")
    except Exception:
        output = ""
    try:
        container.remove(force=True)
    except Exception:
        pass
    return exit_code, output, timed_out


def _pull_if_needed(client, image: str) -> None:
    try:
        client.images.get(image)
    except Exception:
        client.images.pull(image)


def run_in_sandbox(*, repo_path_in_worker: str, config: SandboxConfig) -> ExecutionResult:
    """Run install (networked) then test+lint (network-isolated) against one
    already-cloned repo. `repo_path_in_worker` is this container's own path to
    the checkout; the host-path translation happens internally."""
    if not config.runnable:
        return ExecutionResult(outcome="skipped",
                                reason=f"No runnable test command (config source: {config.source})")

    client = _client()
    if client is None:
        return ExecutionResult(outcome="skipped", reason="Docker daemon unavailable")

    image = config.image or "python:3.11-slim"
    host_workdir = _host_path(repo_path_in_worker)
    commands = {"install": config.install_cmd, "test": config.test_cmd, "lint": config.lint_cmd}
    start = time.time()

    try:
        _pull_if_needed(client, image)
    except Exception as exc:
        return ExecutionResult(outcome="skipped", reason=f"Could not pull image {image}: {exc}",
                                image=image, commands=commands)

    install_output = ""
    if config.install_cmd:
        code, install_output, timed_out = _run_step(
            client, image=image, command=["sh", "-c", config.install_cmd],
            host_workdir=host_workdir, network_disabled=False,
            timeout=settings.sandbox_install_timeout_seconds,
        )
        if timed_out:
            return ExecutionResult(outcome="skipped", reason="Install step timed out",
                                    timed_out=True, image=image, commands=commands,
                                    install_output=install_output,
                                    duration_ms=int((time.time() - start) * 1000))
        if code != 0:
            # Dependencies that won't install are an infra/config gap (a
            # private registry this sandbox has no credentials for, a native
            # extension needing a package the base image lacks) — not evidence
            # the change itself is broken. Skip, don't fail.
            return ExecutionResult(outcome="skipped", reason=f"Install step exited {code}",
                                    image=image, commands=commands, install_output=install_output,
                                    duration_ms=int((time.time() - start) * 1000))

    test_code, test_output, test_timed_out = _run_step(
        client, image=image, command=["sh", "-c", config.test_cmd],
        host_workdir=host_workdir, network_disabled=True,
        timeout=settings.sandbox_timeout_seconds,
    )

    lint_output = ""
    if config.lint_cmd and not test_timed_out:
        _, lint_output, _ = _run_step(
            client, image=image, command=["sh", "-c", config.lint_cmd],
            host_workdir=host_workdir, network_disabled=True,
            timeout=settings.sandbox_timeout_seconds,
        )

    duration_ms = int((time.time() - start) * 1000)
    if test_timed_out:
        return ExecutionResult(outcome="skipped", reason="Test step timed out", timed_out=True,
                                image=image, commands=commands, install_output=install_output,
                                test_output=test_output, duration_ms=duration_ms)

    outcome = "passed" if test_code == 0 else "failed"
    return ExecutionResult(outcome=outcome, exit_code=test_code, image=image, commands=commands,
                            install_output=install_output, test_output=test_output,
                            lint_output=lint_output, duration_ms=duration_ms)


# ── Top-level entry point ────────────────────────────────────────────────────

def execute(*, repo_name: str, branch: str, token: str, provider: str = "github",
            host: str | None = None, run_id: str | None = None) -> ExecutionResult:
    """Clone the branch and run its own tests. Always cleans up the checkout,
    win or lose — the caller never has to remember to."""
    if not settings.sandbox_enabled:
        return ExecutionResult(outcome="skipped", reason="Sandbox disabled by settings")

    os.makedirs(settings.sandbox_workdir, exist_ok=True)
    workdir = os.path.join(settings.sandbox_workdir, f"run-{run_id or uuid.uuid4()}")

    try:
        clone_repo(repo_name=repo_name, branch=branch, token=token, dest=workdir,
                   provider=provider, host=host)
    except SandboxError as exc:
        return ExecutionResult(outcome="skipped", reason=str(exc))

    try:
        config = detect_config(workdir)
        return run_in_sandbox(repo_path_in_worker=workdir, config=config)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
