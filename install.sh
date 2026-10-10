#!/usr/bin/env bash
# Install Spotter into ${HERMES_HOME:-$HOME/.hermes}. Copies only changed files, enables the plugin in
# config.yaml (and, if asked, in every profile), backing up each config first. Every change is printed.
#   SPOTTER_ALL_PROFILES=1|0   enable in every profile without asking / skip profiles
set -euo pipefail
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ID="hermes-spotter"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
case "$HERMES_HOME" in ""|"/") echo "Refusing HERMES_HOME='$HERMES_HOME'" >&2; exit 1 ;; esac
case "$HERMES_HOME" in */profiles/*) echo "  ! HERMES_HOME is a profile folder ($HERMES_HOME). Set HERMES_HOME to your main Hermes." >&2; exit 1 ;; esac
PLUGIN_DEST="$HERMES_HOME/plugins/$PLUGIN_ID"
DESKTOP_DEST="$HERMES_HOME/desktop-plugins/$PLUGIN_ID"
STAMP="$(date +%Y%m%d-%H%M%S)"

copy() { # src dst
  if [ -f "$2" ] && cmp -s "$1" "$2"; then echo "  = ${2#$HERMES_HOME/} (unchanged)"; return; fi
  mkdir -p "$(dirname "$2")"; cp "$1" "$2"; echo "  ✓ ${2#$HERMES_HOME/}"
}
find_python() {
  local p
  for p in "${HERMES_PYTHON:-}" "$HERMES_HOME/hermes-agent/venv/bin/python3" "$(command -v python3 || true)"; do
    if [ -n "$p" ] && [ -x "$p" ] && "$p" -I -c 'import yaml' >/dev/null 2>&1; then echo "$p"; return 0; fi
  done; return 1
}
enable_in() { # config owner-file
  [ -f "$1" ] || { echo "  - no $1; start Hermes once, then re-run" >&2; return 0; }
  local py; py="$(find_python)" || { echo "  ✗ no python with PyYAML; enable $PLUGIN_ID in $1 by hand" >&2; return 2; }
  cp "$1" "$1.bak-$STAMP-spotter"
  "$py" -I "$SRC_DIR/scripts/config_edit.py" enable "$PLUGIN_ID" "$1" "$2"
}

echo "→ Installing Spotter into $HERMES_HOME"
copy "$SRC_DIR/desktop/plugin.js" "$DESKTOP_DEST/plugin.js"
for f in plugin.yaml __init__.py spotter_store.py LICENSE dashboard/manifest.json dashboard/plugin_api.py; do
  copy "$SRC_DIR/$f" "$PLUGIN_DEST/$f"
done
mkdir -p "$PLUGIN_DEST/.config-owned-profiles"
enable_in "$HERMES_HOME/config.yaml" "$PLUGIN_DEST/.config-owned.json"

answer="${SPOTTER_ALL_PROFILES:-}"
cfgs=("$HERMES_HOME"/profiles/*/config.yaml)
if [ -f "${cfgs[0]}" ]; then
  if [ -z "$answer" ] && [ -t 0 ]; then
    printf "Spotter only watches turns in profiles where it is enabled. Enable in all %s profiles? [Y/n] " "${#cfgs[@]}"
    read -r r || r=n; case "$r" in [nN]*) answer=0 ;; *) answer=1 ;; esac
  fi
  if [ "$answer" = "1" ]; then
    for cfg in "${cfgs[@]}"; do
      name="$(basename "$(dirname "$cfg")")"; printf "  [%s] " "$name"
      enable_in "$cfg" "$PLUGIN_DEST/.config-owned-profiles/$name.json" || echo "  ! $name left unchanged" >&2
    done
  else
    echo "  - other profiles left unchanged"
  fi
fi
echo ""
echo "Done. Quit Hermes Desktop (⌘Q) and reopen it once. Spotter makes no model calls in this version."
echo "Notes and turn counts live in $HERMES_HOME/spotter/."
