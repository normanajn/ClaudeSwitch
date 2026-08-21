#!/usr/bin/env bash
# uninstall.sh — remove claudeswitch installed via install.sh or pip

set -euo pipefail

TARGET="/usr/local/bin/claudeswitch"
PURGE=0

for arg in "$@"; do
  case "$arg" in
    --purge)
      PURGE=1
      ;;
    -h|--help)
      echo "Usage: $0 [--purge]"
      echo "  --purge   Also remove ~/.claude profile data (settings-*.json, backups/, .claudeswitch)"
      exit 0
      ;;
  esac
done

# Remove the symlink created by install.sh
if [[ -L "$TARGET" || -f "$TARGET" ]]; then
  echo "Removing $TARGET"
  sudo rm "$TARGET"
fi

# Remove pip-installed package (console script + man page), if present
if python3 -m pip show claudeswitch >/dev/null 2>&1; then
  echo "Removing pip package claudeswitch"
  python3 -m pip uninstall -y claudeswitch
fi

if [[ "$PURGE" -eq 1 ]]; then
  echo "Removing ~/.claude profile data"
  rm -f ~/.claude/settings-*.json ~/.claude/.claudeswitch
  rm -rf ~/.claude/backups
else
  echo "Profile data in ~/.claude left in place (use --purge to remove it)"
fi

echo "Uninstall complete."
