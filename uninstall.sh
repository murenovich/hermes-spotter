#!/usr/bin/env bash
# Remove Spotter from ${HERMES_HOME:-$HOME/.hermes}: undoes the config edits install.sh made (main config and
# any profiles) and deletes the plugin files. Notes and turn counts in $HERMES_HOME/spotter/ are kept.
set -euo pipefail
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ID="hermes-spotter"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
case "$HERMES_HOME" in ""|"/"|*/profiles/*) echo "Refusing HERMES_HOME='$HERMES_HOME'" >&2; exit 1 ;; esac
PLUGIN_DEST="$HERMES_HOME/plugins/$PLUGIN_ID"
find_python() {
  local p
  for p in "${HERMES_PYTHON:-}" "$HERMES_HOME/hermes-agent/venv/bin/python3" "$(command -v python3 || true)"; do
    if [ -n "$p" ] && [ -x "$p" ] && "$p" -I -c 'import yaml' >/dev/null 2>&1; then echo "$p"; return 0; fi
  done; return 1
}
py="$(find_python)" || { echo "✗ no python with PyYAML; remove $PLUGIN_ID from plugins.enabled by hand" >&2; exit 2; }
echo "→ Uninstalling Spotter from $HERMES_HOME"
[ -f "$HERMES_HOME/config.yaml" ] && "$py" -I "$SRC_DIR/scripts/config_edit.py" disable "$PLUGIN_ID" "$HERMES_HOME/config.yaml" "$PLUGIN_DEST/.config-owned.json"
for owner in "$PLUGIN_DEST"/.config-owned-profiles/*.json; do
  [ -f "$owner" ] || continue
  name="$(basename "$owner" .json)"; cfg="$HERMES_HOME/profiles/$name/config.yaml"
  [ -f "$cfg" ] && { printf "  [%s] " "$name"; "$py" -I "$SRC_DIR/scripts/config_edit.py" disable "$PLUGIN_ID" "$cfg" "$owner"; }
done
rm -rf "$PLUGIN_DEST" "$HERMES_HOME/desktop-plugins/$PLUGIN_ID"
echo "  ✓ removed plugins/$PLUGIN_ID and desktop-plugins/$PLUGIN_ID"
echo "Done. Restart Hermes Desktop. Your notes in $HERMES_HOME/spotter/ were kept; delete that folder to forget them."
