import json
from pathlib import Path

import pytest

import ai_login_switcher as switcher


@pytest.fixture()
def isolated_switcher(tmp_path, monkeypatch):
    base = tmp_path / "switcher"
    claude_home = tmp_path / "homes" / "claude"
    codex_home = tmp_path / "homes" / "codex"
    monkeypatch.setattr(switcher, "BASE_DIR", base)
    monkeypatch.setattr(switcher, "PROFILES_DIR", base / "profiles")
    monkeypatch.setattr(switcher, "EMPTY_DIR", base / "empty")
    monkeypatch.setattr(switcher, "STATE_FILE", base / "state.json")
    monkeypatch.setattr(switcher, "CLAUDE_TARGET", claude_home)
    monkeypatch.setattr(switcher, "CODEX_TARGET", codex_home)
    monkeypatch.setattr(switcher, "TOOL_TARGETS", {"claude": claude_home, "codex": codex_home})
    return tmp_path


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_detects_valid_claude_credentials_file(isolated_switcher):
    root = isolated_switcher / "claude"
    write_json(root / ".credentials.json", {"claudeAiOauth": {"accessToken": "token"}})

    assert switcher.has_valid_credentials("claude", root)
    assert switcher.credential_status_for_root("claude", root) == "valid credentials (.credentials.json)"


def test_detects_valid_codex_auth_file(isolated_switcher):
    root = isolated_switcher / "codex"
    write_json(root / "auth.json", {"tokens": {"access_token": "token"}})

    assert switcher.has_valid_credentials("codex", root)
    assert switcher.credential_status_for_root("codex", root) == "valid auth.json"


def test_capture_and_switch_with_dummy_homes(isolated_switcher, monkeypatch):
    write_json(switcher.CLAUDE_TARGET / ".credentials.json", {"claudeAiOauth": {"accessToken": "claude-token"}})
    write_json(switcher.CODEX_TARGET / "auth.json", {"OPENAI_API_KEY": "codex-key"})
    monkeypatch.setattr(switcher, "refresh_profile_identity", lambda tool, profile_id: switcher.ToolIdentity(logged_in="true"))

    switcher.capture_tool("claude", "work")
    switcher.capture_tool("codex", "work")

    assert switcher.has_valid_credentials("claude", switcher.profile_tool_dir("work", "claude"))
    assert switcher.has_valid_credentials("codex", switcher.profile_tool_dir("work", "codex"))

    switcher.switch_tool("claude", "empty", refresh=False)
    switcher.switch_tool("codex", "empty", refresh=False)
    assert not switcher.has_valid_credentials("claude", switcher.CLAUDE_TARGET)
    assert not switcher.has_valid_credentials("codex", switcher.CODEX_TARGET)

    switcher.switch_tool("claude", "work", refresh=False)
    switcher.switch_tool("codex", "work", refresh=False)
    assert switcher.has_valid_credentials("claude", switcher.CLAUDE_TARGET)
    assert switcher.has_valid_credentials("codex", switcher.CODEX_TARGET)


def test_status_summary_extracts_token_usage_from_status_json():
    identity = switcher.ToolIdentity(
        raw_status=json.dumps(
            {
                "model": {"display_name": "Sonnet"},
                "context_window": {"used_percentage": 42, "total_input_tokens": 100, "total_output_tokens": 25},
                "cost": {"total_cost_usd": 0.12},
            }
        )
    )

    summary = switcher.status_summary(identity)

    assert "model: Sonnet" in summary
    assert "context: 42" in summary
    assert "input: 100" in summary
    assert "output: 25" in summary
    assert "cost: 0.12" in summary
