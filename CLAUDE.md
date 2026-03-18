# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

ClaudeSwitch is a single-file Python 3 CLI/TUI/GUI tool (`claudeswitch`) for managing multiple Claude Code API configuration profiles. It lets users switch between different backends (standard Anthropic, Azure, LiteLLM, AskSage) by copying profile-specific `settings.json` files into `~/.claude/`.

## Running the Tool

```bash
./claudeswitch              # Launch interactive TUI
./claudeswitch --gui        # Launch Qt GUI (requires PySide6 or PyQt5)
./claudeswitch --list       # List profiles
./claudeswitch --switch <name>  # Switch to a named profile
./install.sh                # Install: creates symlink at /usr/local/bin/claudeswitch
```

There is no build step, test suite, or linter configured.

## Architecture

The entire application lives in the single file `claudeswitch`. It is structured in horizontal layers (separated by visual comment banners):

**Data layer (lines ~32–140):** Profile discovery, file I/O, env var serialization, backup logic, and field specifications per profile type.

**TUI layer (lines ~146–604):** Curses-based terminal UI — profile browser, inline field editor, pop-up dialogs.

**Qt GUI layer (lines ~607–1106):** PySide6/PyQt5 application with split-panel layout (profile list + JSON preview + form editor), menu bar, and import/export.

**CLI entry point (lines ~1112–1169):** Argument parsing and dispatch; falls back to TUI when no flags given.

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
- `read_env(name)` / `write_env(name, env)` — profile JSON serialization

## Dependencies

Standard library only for CLI/TUI. `PySide6` (preferred) or `PyQt5` required for `--gui`; script falls back to TUI gracefully if neither is installed.
