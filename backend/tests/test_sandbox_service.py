"""
Unit tests for the execution sandbox (app/services/sandbox_service.py).

Deliberately Docker-free for the required suite: the pure logic (which
command a project gets, how a clone failure is reported, how a host-path
translation resolves) is what would silently drift and produce wrong
behaviour without ever throwing an exception in CI. One additional test does
exercise a real Docker daemon end to end, but skips itself cleanly wherever
one isn't reachable — including this repo's own CI runner and most
contributors' machines — so it can never turn into a false failure.
"""
from __future__ import annotations

import subprocess

import pytest

from app.config import settings
from app.services import sandbox_service as sb


# ═══ Project-type detection ═══════════════════════════════════════════════════

class TestDetectConfig:
    def test_no_manifest_is_not_runnable(self, tmp_path):
        config = sb.detect_config(str(tmp_path))
        assert config.source == "none"
        assert not config.runnable

    def test_package_json_picks_npm(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        config = sb.detect_config(str(tmp_path))
        assert config.source == "heuristic:package.json"
        assert config.install_cmd == "npm ci"
        assert "npm test" in config.test_cmd
        assert config.runnable

    def test_requirements_txt_picks_pytest(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n")
        config = sb.detect_config(str(tmp_path))
        assert config.source == "heuristic:requirements.txt"
        assert config.test_cmd == "pytest -q"
        assert "requirements.txt" in config.install_cmd

    def test_pyproject_toml_picks_pytest(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        config = sb.detect_config(str(tmp_path))
        assert config.source == "heuristic:pyproject.toml"
        assert config.test_cmd == "pytest -q"

    def test_go_mod_has_no_install_step(self, tmp_path):
        (tmp_path / "go.mod").write_text("module x\n")
        config = sb.detect_config(str(tmp_path))
        assert config.test_cmd == "go test ./..."
        assert config.install_cmd is None
        assert config.runnable        # install being optional must not affect runnability

    def test_cargo_toml_picks_cargo_test(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'x'\n")
        config = sb.detect_config(str(tmp_path))
        assert config.test_cmd == "cargo test"

    def test_gemfile_picks_rspec(self, tmp_path):
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'\n")
        config = sb.detect_config(str(tmp_path))
        assert config.test_cmd == "bundle exec rspec"

    def test_explicit_config_overrides_heuristic(self, tmp_path):
        # Both a package.json AND an .evolune.yml — the explicit file must win,
        # not the manifest that would otherwise be detected first.
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / ".evolune.yml").write_text(
            "image: python:3.12-slim\ninstall: pip install -e .\ntest: pytest -q -k unit\n"
        )
        config = sb.detect_config(str(tmp_path))
        assert config.source == "explicit"
        assert config.image == "python:3.12-slim"
        assert config.test_cmd == "pytest -q -k unit"

    def test_evolune_yml_beats_older_adlc_yml_name(self, tmp_path):
        (tmp_path / ".evolune.yml").write_text("test: pytest -q\n")
        (tmp_path / ".adlc.yml").write_text("test: pytest -q -k should-not-be-picked\n")
        config = sb.detect_config(str(tmp_path))
        assert config.test_cmd == "pytest -q"

    def test_malformed_explicit_config_does_not_fall_back_to_heuristic(self, tmp_path):
        # A repo maintainer's broken YAML must not silently run against the
        # WRONG commands via the heuristic path — that would report on code
        # that was never actually exercised as configured.
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / ".evolune.yml").write_text("test: [unterminated\n")
        config = sb.detect_config(str(tmp_path))
        assert config.source == "explicit-invalid"
        assert not config.runnable

    def test_explicit_config_with_no_test_key_is_not_runnable(self, tmp_path):
        (tmp_path / ".evolune.yml").write_text("install: echo hi\n")
        config = sb.detect_config(str(tmp_path))
        assert config.source == "explicit"
        assert not config.runnable


# ═══ ExecutionResult ═══════════════════════════════════════════════════════════

class TestExecutionResult:
    def test_passed_property_matches_outcome(self):
        assert sb.ExecutionResult(outcome="passed").passed
        assert not sb.ExecutionResult(outcome="failed").passed
        assert not sb.ExecutionResult(outcome="skipped").passed

    def test_long_output_is_truncated_in_as_dict(self):
        huge = "x" * (sb.MAX_OUTPUT_CHARS + 500)
        result = sb.ExecutionResult(outcome="passed", test_output=huge)
        rendered = result.as_dict()["test_output"]
        assert len(rendered) < len(huge)
        assert "truncated" in rendered

    def test_short_output_is_not_modified(self):
        result = sb.ExecutionResult(outcome="passed", test_output="all good")
        assert result.as_dict()["test_output"] == "all good"


# ═══ Authenticated clone URLs ═══════════════════════════════════════════════════

class TestAuthenticatedUrl:
    def test_token_is_embedded_as_basic_auth(self):
        url = sb._authenticated_url("https://github.com/acme/repo.git",
                                     username="x-access-token", token="ghp_abc123")
        assert url == "https://x-access-token:ghp_abc123@github.com/acme/repo.git"

    def test_token_with_special_characters_does_not_corrupt_the_url(self):
        # A token containing '@' or '/' must not let the credential spill
        # into the host or path components of the URL.
        from urllib.parse import urlsplit
        url = sb._authenticated_url("https://gitlab.example.com/group/repo.git",
                                     username="oauth2", token="wei/rd@token")
        parts = urlsplit(url)
        assert parts.hostname == "gitlab.example.com"
        assert parts.path == "/group/repo.git"

    def test_self_hosted_gitlab_port_is_preserved(self):
        from urllib.parse import urlsplit
        url = sb._authenticated_url("https://git.internal:8443/team/repo.git",
                                     username="oauth2", token="tok")
        parts = urlsplit(url)
        assert parts.port == 8443
        assert parts.hostname == "git.internal"


class TestCloneRepo:
    def test_failure_never_leaks_the_token_into_the_raised_error(self, monkeypatch, tmp_path):
        secret = "super-secret-token-value"

        def fake_run(argv, **kwargs):
            assert any(secret in a for a in argv)   # confirms the token really was in the clone URL
            return subprocess.CompletedProcess(
                argv, returncode=128,
                stdout="", stderr=f"fatal: could not read Username for 'https://{secret}@github.com'",
            )

        monkeypatch.setattr(sb.subprocess, "run", fake_run)
        with pytest.raises(sb.SandboxError) as exc_info:
            sb.clone_repo(repo_name="acme/repo", branch="main", token=secret,
                          dest=str(tmp_path / "checkout"))
        assert secret not in str(exc_info.value)
        assert "***" in str(exc_info.value)

    def test_timeout_raises_sandbox_error(self, monkeypatch, tmp_path):
        def fake_run(argv, **kwargs):
            raise subprocess.TimeoutExpired(cmd=argv, timeout=1)

        monkeypatch.setattr(sb.subprocess, "run", fake_run)
        with pytest.raises(sb.SandboxError, match="timed out"):
            sb.clone_repo(repo_name="acme/repo", branch="main", token="t",
                          dest=str(tmp_path / "checkout"), timeout=1)


# ═══ Docker-outside-of-Docker path translation ═════════════════════════════════

class TestHostPathTranslation:
    def test_identity_when_no_host_path_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "sandbox_host_path", "")
        assert sb._host_path("/tmp/adlc-sandbox/run-123") == "/tmp/adlc-sandbox/run-123"

    def test_translates_into_the_configured_host_path(self, monkeypatch):
        monkeypatch.setattr(settings, "sandbox_workdir", "/tmp/adlc-sandbox")
        monkeypatch.setattr(settings, "sandbox_host_path", "/opt/agentic-sdlc/sandbox_data")
        result = sb._host_path("/tmp/adlc-sandbox/run-123")
        assert result == "/opt/agentic-sdlc/sandbox_data/run-123"

    def test_translates_nested_paths(self, monkeypatch):
        monkeypatch.setattr(settings, "sandbox_workdir", "/tmp/adlc-sandbox")
        monkeypatch.setattr(settings, "sandbox_host_path", "/srv/sandbox")
        result = sb._host_path("/tmp/adlc-sandbox/run-123/sub/dir")
        assert result == "/srv/sandbox/run-123/sub/dir"


# ═══ Top-level entry point ═════════════════════════════════════════════════════

class TestExecute:
    def test_disabled_by_settings_skips_before_touching_the_filesystem(self, monkeypatch):
        monkeypatch.setattr(settings, "sandbox_enabled", False)
        calls = []
        monkeypatch.setattr(sb, "clone_repo", lambda **kw: calls.append(kw))
        result = sb.execute(repo_name="acme/repo", branch="main", token="t")
        assert result.outcome == "skipped"
        assert "disabled" in result.reason.lower()
        assert calls == []

    def test_clone_failure_yields_skipped_not_an_exception(self, monkeypatch, tmp_path):
        monkeypatch.setattr(settings, "sandbox_enabled", True)
        monkeypatch.setattr(settings, "sandbox_workdir", str(tmp_path))

        def fake_clone(**kw):
            raise sb.SandboxError("git clone failed: repository not found")
        monkeypatch.setattr(sb, "clone_repo", fake_clone)

        result = sb.execute(repo_name="acme/repo", branch="main", token="t")
        assert result.outcome == "skipped"
        assert "not found" in result.reason


# ═══ Live Docker smoke test — self-skipping ════════════════════════════════════

def _docker_daemon_reachable() -> bool:
    client = sb._client()
    if client is None:
        return False
    try:
        client.ping()
        return True
    except Exception:
        return False
    finally:
        try:
            client.close()
        except Exception:
            pass


@pytest.mark.skipif(not _docker_daemon_reachable(), reason="no Docker daemon reachable")
def test_run_in_sandbox_against_a_real_container(tmp_path, monkeypatch):
    """The one test that actually proves a container runs, on any machine that
    happens to have Docker. Everything else in this file is intentionally
    daemon-free so the suite is meaningful in this repo's own CI, which does
    not run the backend tests inside a nested container."""
    monkeypatch.setattr(settings, "sandbox_cpu_limit", 1.0)
    monkeypatch.setattr(settings, "sandbox_memory_limit", "256m")

    config = sb.SandboxConfig(image="python:3.11-slim", test_cmd="python3 -c 'print(1+1)'",
                              source="explicit")
    result = sb.run_in_sandbox(repo_path_in_worker=str(tmp_path), config=config)
    assert result.outcome == "passed"
    assert "2" in result.test_output
