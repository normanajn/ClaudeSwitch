#!/usr/bin/env bash
# install.sh — install claudeswitch with pip
#
# Single-file alternative (no pip required):
#   python3 build.py          # produces dist/claudeswitch.pyz
#   ./dist/claudeswitch.pyz   # run directly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_BASE="$(python3 -m site --user-base)"
USER_BIN="$USER_BASE/bin"

python3 -m pip install --user "$SCRIPT_DIR[gui]"
python3 -m claudeswitch init

echo "Installed ClaudeSwitch with python3 -m pip install --user .[gui]"
echo "Console scripts are typically available in: $USER_BIN"
