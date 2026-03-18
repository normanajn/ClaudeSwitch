#!/usr/bin/env bash
# install.sh — install claudeswitch to /usr/local/bin

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="/usr/local/bin/claudeswitch"

chmod +x "$SCRIPT_DIR/claudeswitch"

if [[ -L "$TARGET" || -f "$TARGET" ]]; then
  echo "Removing existing $TARGET"
  sudo rm "$TARGET"
fi

sudo ln -s "$SCRIPT_DIR/claudeswitch" "$TARGET"
echo "Installed: $TARGET -> $SCRIPT_DIR/claudeswitch"

# Run init to set up profile files
"$SCRIPT_DIR/claudeswitch" init
