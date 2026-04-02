# ClaudeSwitch

If you are like me you have multiple sources of access to LLMs, and need to swap between them depending on what you are working on (i.e. a work account, private account, public free LLMs etc...) and you want them to all work with Claude Code.  Normally this would require copying files back and forth between the `.claude/settings.json` file, or setting a number of different environment variables.  This is a pain.

This is where claudeswitch comes in.

Claudeswitch, is a CLI/TUI/GUI tool for managing multiple [Claude Code](https://claude.ai/code) API configuration profiles. It lets you quickly switch between different backends — standard Anthropic account, Azure, OpenAI, LiteLLM, AskSage, etc... — without manually editing `~/.claude/settings.json`.

It also lets you *see* what configuration you are currently in, so that you can tailor which claude terminals are doing what against different token pools.

It doesn't expose your different auth tokens, it just handles the bookkeeping of juggling which one should be in place at any given time.  This should work on most platforms that use the json configuration system.

## Features

- **CLI mode** — commandline for scripting profile switching
- **Curses Terminal** — terminal-driven profile browser (slick as a mombo band)
- **Qt GUI** — split-panel interface with live JSON preview and import/export (point, click)
- **Auto-backup** — saves a timestamped copy of `settings.json` before every switch
- **Secret masking** — API keys are hidden by default in all UIs

## Requirements

- Python 3.7+
- `PySide6` or `PyQt5` *(optional, for `--gui` mode only)*

## Installation

To install claudeswitch you will need to do some basic boostrapping.  Either run the bootstrap script, or setup a Python virtual environment and populate it.

First clone the repo:
```bash
git clone https://github.com/youruser/ClaudeSwitch.git
cd ClaudeSwitch
```

```
./install.sh. # This does a basic install
```

`install.sh` makes the script executable, symlinks it to `/usr/local/bin/claudeswitch`, and runs `claudeswitch init` to create a default `login` profile.

```
python3 -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```
At this point you should be able to test it out.
```
python -m claudeswitch init
```

If it works then you can do a:
```
./install.sh
```

`install.sh` makes the script executable, symlinks it to `/usr/local/bin/claudeswitch`, and runs `claudeswitch init` to create a default `login` profile.

Notes: You'll want to create a set of settings-PROVIDER.json files which have the settings for each service you use.  If you also have an Anthropic Pro/Max account you should also make a settings-login.json which will be the settings when running in that mode.

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
