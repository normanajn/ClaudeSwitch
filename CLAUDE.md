# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

ClaudeSwitch is a packaged Python CLI/TUI/GUI tool for managing multiple Claude Code API configuration profiles. It lets users switch between different backends (standard Anthropic, Azure, LiteLLM, AskSage) by copying profile-specific `settings.json` files into `~/.claude/`.

## Running the Tool

```bash
python3 -m claudeswitch            # Launch interactive TUI
python3 -m claudeswitch init       # Create ~/.claude state and login profile
python3 -m claudeswitch --gui      # Launch Qt GUI
python3 -m claudeswitch --list     # List profiles
python3 -m claudeswitch --switch <name>  # Switch to a named profile
./install.sh                       # User-local install via pip with GUI extras
```

After installation, the console script `claudeswitch` is also available through the package entry point defined in `pyproject.toml`.

## Packaging And Tests

- Packaging is defined in `pyproject.toml`
- The importable package is `claudeswitch/`
- The executable entry point is `claudeswitch.cli:run`
- The automated tests live in `tests/test_cli.py`

Typical development setup:

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -e '.[test]'
pytest
coverage run --source=claudeswitch -m pytest tests/test_cli.py -q
coverage report -m
```

## Architecture

The main application logic lives in `claudeswitch/cli.py`. It is still structured in horizontal layers:

**Data layer:** Profile discovery, file I/O, env var serialization, backup logic, and field specifications per profile type.

**TUI layer:** Curses-based terminal UI — profile browser, inline field editor, pop-up dialogs.

**Qt GUI layer:** PySide6/PyQt5 application with split-panel layout (profile list + JSON preview + form editor), menu bar, and import/export.

**CLI entry point:** Argument parsing and dispatch; launches the TUI when no arguments are given, supports `init`, `--list`, `--switch`, `--gui`, and returns CLI errors for unknown arguments.

## Profile Storage Convention

All data lives under `~/.claude/`:

| Path | Purpose |
|---|---|
| `settings.json` | Active profile (Claude Code reads this) |
| `.claudeswitch` | Name of the currently active profile |
| `settings-<name>.json` | Stored profile files |
| `backups/` | Timestamped backups created before each switch |

Each profile file contains an `env` object with backend-specific keys (e.g. `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, `AZURE_API_VERSION`). The function `fields_for(name, env)` maps a profile name/env to the appropriate field schema (label, default, secret flag, optional flag).

## Profile Types

`login` (no API config), `azure`, `litellm`, `asksage`, and a generic fallback (API key + base URL). Profile type is inferred from the profile name and its existing env keys.

## Key Functions

- `activate_profile(name)` — backs up current settings, copies profile to `settings.json`, writes `.claudeswitch`
- `discover_profiles()` — scans `settings-*.json` and returns sorted profile names
- `current_profile()` — reads `.claudeswitch`
- `do_init()` — creates `~/.claude/`, `backups/`, and `settings-login.json`
- `read_env(name)` / `write_env(name, env)` — profile JSON serialization
- `main(argv=None)` — CLI dispatch for package/module/script entry points

## Dependencies

Standard library only for CLI/TUI. `PySide6` is the packaged GUI extra, and `PyQt5` is also supported at runtime if installed separately. PyTest and Coverage are used for automated testing.
