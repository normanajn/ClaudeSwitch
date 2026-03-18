# ClaudeSwitch

A CLI/TUI/GUI tool for managing multiple [Claude Code](https://claude.ai/code) API configuration profiles. Quickly switch between different backends — standard Anthropic, Azure OpenAI, LiteLLM, or AskSage — without manually editing `~/.claude/settings.json`.

## Features

- **Interactive TUI** — keyboard-driven profile browser, no dependencies beyond Python 3
- **Qt GUI** — split-panel interface with live JSON preview and import/export
- **CLI mode** — scriptable profile switching
- **Auto-backup** — saves a timestamped copy of `settings.json` before every switch
- **Secret masking** — API keys are hidden by default in all UIs

## Requirements

- Python 3.7+
- `PySide6` or `PyQt5` *(optional, for `--gui` mode only)*

## Installation

```bash
git clone https://github.com/youruser/ClaudeSwitch.git
cd ClaudeSwitch
./install.sh
```

`install.sh` makes the script executable, symlinks it to `/usr/local/bin/claudeswitch`, and runs `claudeswitch init` to create a default `login` profile.

## Usage

```bash
claudeswitch                    # Interactive TUI
claudeswitch --gui              # Qt graphical UI
claudeswitch --list             # List all profiles
claudeswitch --switch <name>    # Switch to a profile non-interactively
claudeswitch --help             # Show help
```

Short flags: `-l` for `--list`, `-s` for `--switch`.

## TUI Key Bindings

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate profiles |
| `Enter` | Switch to selected profile |
| `m` | Open More menu |
| `q` | Quit |
| **More menu** | |
| `c` | Configure selected profile |
| `n` | Create new profile |
| `d` | Delete selected profile |
| `i` | Init default profiles |
| `<` | Back to main menu |

## Profile Types

Profiles are stored as `~/.claude/settings-<name>.json`. ClaudeSwitch recognises the following types by name and pre-fills the appropriate fields:

| Profile name | Backend | Fields |
|---|---|---|
| `login` | Anthropic subscription | *(none required)* |
| `azure` | Azure OpenAI | API Key, Endpoint URL, API Version, Deployment Name |
| `litellm` | LiteLLM proxy | API Key, Proxy URL |
| `asksage` | AskSage | API Key, Base URL, AskSage Token *(optional)* |
| anything else | Standard Anthropic API | API Key, Base URL |

The active profile is mirrored to `~/.claude/settings.json`, which is what Claude Code reads. Previous settings are backed up to `~/.claude/backups/` before each switch.

## File Layout

```
~/.claude/
├── settings.json            ← active profile (managed by claudeswitch)
├── .claudeswitch            ← name of the currently active profile
├── settings-login.json
├── settings-azure.json
├── settings-<name>.json
└── backups/
    └── settings_20260318_120000.json
```

## License

MIT
