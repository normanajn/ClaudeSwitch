import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from claudeswitch import cli


@pytest.fixture
def isolated_claude_home(monkeypatch, tmp_path):
    claude_dir = tmp_path / ".claude"
    monkeypatch.setattr(cli, "CLAUDE_DIR", claude_dir)
    monkeypatch.setattr(cli, "SETTINGS_FILE", claude_dir / "settings.json")
    monkeypatch.setattr(cli, "STATE_FILE", claude_dir / ".claudeswitch")
    return claude_dir


def test_init_creates_default_profile_storage(isolated_claude_home, capsys):
    assert cli.main(["init"]) == 0

    captured = capsys.readouterr()
    assert "Initialised default profiles" in captured.out
    assert (isolated_claude_home / "backups").is_dir()
    assert (isolated_claude_home / "settings-login.json").read_text() == "{}\n"


def test_help_prints_usage(capsys):
    assert cli.main(["--help"]) == 0

    captured = capsys.readouterr()
    assert "claudeswitch --switch <name>" in captured.out


def test_list_marks_the_active_profile(isolated_claude_home, capsys):
    isolated_claude_home.mkdir()
    (isolated_claude_home / "settings-login.json").write_text("{}\n")
    (isolated_claude_home / "settings-azure.json").write_text("{}\n")
    (isolated_claude_home / ".claudeswitch").write_text("azure")

    assert cli.main(["--list"]) == 0

    captured = capsys.readouterr()
    assert "* azure" in captured.out
    assert "  login" in captured.out


def test_list_without_profiles_prints_init_hint(isolated_claude_home, capsys):
    isolated_claude_home.mkdir()

    assert cli.main(["--list"]) == 0

    captured = capsys.readouterr()
    assert "No profiles found. Run: claudeswitch init" in captured.out


def test_switch_copies_profile_and_updates_state(isolated_claude_home, capsys):
    isolated_claude_home.mkdir()
    (isolated_claude_home / "settings-login.json").write_text('{"env":{"ANTHROPIC_API_KEY":"abc"}}\n')

    assert cli.main(["--switch", "login"]) == 0

    captured = capsys.readouterr()
    assert "Switched to profile: login" in captured.out
    assert json.loads((isolated_claude_home / "settings.json").read_text()) == {
        "env": {"ANTHROPIC_API_KEY": "abc"}
    }
    assert (isolated_claude_home / ".claudeswitch").read_text() == "login"


def test_switch_unknown_profile_returns_error(isolated_claude_home, capsys):
    isolated_claude_home.mkdir()
    (isolated_claude_home / "settings-login.json").write_text("{}\n")

    assert cli.main(["--switch", "missing"]) == 1

    captured = capsys.readouterr()
    assert "unknown profile 'missing'" in captured.err
    assert "Available profiles: login" in captured.err


def test_write_env_preserves_non_env_content(isolated_claude_home):
    isolated_claude_home.mkdir()
    profile = isolated_claude_home / "settings-azure.json"
    profile.write_text('{"foo":"bar","env":{"OLD":"gone"}}\n')

    cli.write_env("azure", {"ANTHROPIC_API_KEY": "secret", "EMPTY": ""})

    assert json.loads(profile.read_text()) == {
        "foo": "bar",
        "env": {"ANTHROPIC_API_KEY": "secret"},
    }
    assert cli.read_env("azure") == {"ANTHROPIC_API_KEY": "secret"}


def test_discover_profiles_keeps_login_first(isolated_claude_home):
    isolated_claude_home.mkdir()
    (isolated_claude_home / "settings-azure.json").write_text("{}\n")
    (isolated_claude_home / "settings-login.json").write_text("{}\n")
    (isolated_claude_home / "settings-zed.json").write_text("{}\n")

    assert cli.discover_profiles() == ["login", "azure", "zed"]


def test_fields_for_login_and_azure_defaults():
    assert cli.fields_for("login", {}) is None

    azure_fields = cli.fields_for("azure", {})
    assert azure_fields[0]["key"] == "ANTHROPIC_API_KEY"
    assert azure_fields[1]["default"] == "https://<resource>.openai.azure.com"
    assert azure_fields[3]["default"] == "claude-3-5-sonnet"


def test_gui_branch_delegates_to_run_gui(monkeypatch):
    monkeypatch.setattr(cli, "run_gui", lambda: 7)

    assert cli.main(["--gui"]) == 7


def test_unknown_arguments_return_cli_error(monkeypatch, capsys):
    called = False

    def fake_run_tui():
        nonlocal called
        called = True

    monkeypatch.setattr(cli, "run_tui", fake_run_tui)

    assert cli.main(["bogus"]) == 1

    captured = capsys.readouterr()
    assert "unknown arguments: bogus" in captured.err
    assert called is False


def test_python_module_entry_point_supports_help():
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "claudeswitch", "--help"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "claudeswitch --switch <name>" in result.stdout
    assert result.stderr == ""


def test_python_module_entry_point_supports_init(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "claudeswitch", "init"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    assert "Initialised default profiles" in result.stdout
    assert (tmp_path / ".claude" / "settings-login.json").exists()


def test_package_main_module_calls_run(monkeypatch):
    called = False

    def fake_run():
        nonlocal called
        called = True

    monkeypatch.setattr(cli, "run", fake_run)
    runpy.run_module("claudeswitch", run_name="__main__")

    assert called is True
