#!/usr/bin/env bash
# UNOFFICIAL PATCH - USE AT YOUR OWN RISK. Not endorsed or supported by the Supersymmetry, GregTech CEu or
# Industrial Renewal authors. No warranty. Back up the world before running this.
# install_patches.sh - installs (or rolls back) the susy-patches jars on a Supersymmetry 0.2.0.1-patch2 server.
#
# Usage:
#   install_patches.sh <server_dir>             install patched jars (server must be STOPPED)
#   install_patches.sh <server_dir> --rollback  restore the original jars from the latest backup
#   install_patches.sh <server_dir> --check     only report what is installed, change nothing
#
# What it does (install):
#   1. refuses to run if the server looks like it is running (world session lock held / java process in dir)
#   2. downloads every patched jar listed in patches.json and verifies its SHA-256
#   3. verifies the jar it replaces is the ORIGINAL pack jar (SHA-1), so it never replaces an unknown version
#   4. moves the originals to <server_dir>/mods-backup-<timestamp>/ (outside mods/, Forge must not load them)
#   5. copies the patched jars into mods/
# Safe to re-run: already patched mods are skipped.
#
# Requires: bash, curl, sha1sum, sha256sum, python3 OR jq (to read patches.json)
set -euo pipefail

MANIFEST_URL="${SUSY_PATCHES_MANIFEST:-https://raw.githubusercontent.com/ondrej1808/susy-patches/main/server/patches.json}"

#######################################
# Prints an error and exits.
# Arguments: $* - message
# Returns: never (exit 1)
#######################################
die() { echo "ERROR: $*" >&2; exit 1; }

#######################################
# Extracts "name|original_file|original_sha1|patched_file|url|sha256" lines from patches.json.
# Arguments: $1 - path to patches.json
# Outputs: one line per mod on stdout
#######################################
read_manifest() {
  if command -v jq >/dev/null 2>&1; then
    jq -r '.mods[] | [.name,.original_file,.original_sha1,.patched_file,.url,.sha256] | join("|")' "$1"
  elif command -v python3 >/dev/null 2>&1; then
    python3 -I -c 'import json,sys
for m in json.load(open(sys.argv[1]))["mods"]:
    print("|".join([m["name"],m["original_file"],m["original_sha1"],m["patched_file"],m["url"],m["sha256"]]))' "$1"
  else
    die "need jq or python3 to read patches.json"
  fi
}

#######################################
# Fails if the Minecraft server in the directory seems to be running.
# Arguments: $1 - server dir
# Returns: 0 if stopped, exits otherwise
#######################################
assert_stopped() {
  if command -v pgrep >/dev/null 2>&1 && pgrep -f "java.*$(basename "$1")" >/dev/null 2>&1; then
    # best effort; verify the working directory of matching processes
    for pid in $(pgrep -f java || true); do
      if [ "$(readlink -f "/proc/$pid/cwd" 2>/dev/null)" = "$(readlink -f "$1")" ]; then
        die "a java process (pid $pid) is running in $1 - stop the server first"
      fi
    done
  fi
}

SERVER_DIR="${1:-}"; MODE="${2:-install}"
[ -n "$SERVER_DIR" ] || die "usage: $0 <server_dir> [--rollback|--check]"
MODS="$SERVER_DIR/mods"
[ -d "$MODS" ] || die "$MODS not found"

if [ "$MODE" = "--rollback" ]; then
  assert_stopped "$SERVER_DIR"
  BACKUP=$(ls -d "$SERVER_DIR"/mods-backup-* 2>/dev/null | sort | tail -1)
  [ -n "$BACKUP" ] || die "no mods-backup-* directory found"
  rm -f "$MODS"/*-susypatch.jar
  cp -v "$BACKUP"/*.jar "$MODS"/
  echo "Rolled back from $BACKUP"
  exit 0
fi

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
curl -fsSL "$MANIFEST_URL" -o "$TMP/patches.json" || die "cannot download $MANIFEST_URL"

if [ "$MODE" = "--check" ]; then
  while IFS='|' read -r name orig osha patched url sha; do
    if [ -f "$MODS/$patched" ] && [ "$(sha256sum "$MODS/$patched" | cut -d' ' -f1)" = "$sha" ]; then
      echo "PATCHED   $name ($patched)"
    elif [ -f "$MODS/$patched" ]; then
      echo "OUTDATED  $name ($patched has a different hash)"
    elif [ -f "$MODS/$orig" ]; then
      echo "ORIGINAL  $name ($orig)"
    else
      echo "MISSING   $name"
    fi
  done < <(read_manifest "$TMP/patches.json")
  exit 0
fi

echo "UNOFFICIAL PATCH - USE AT YOUR OWN RISK. Make sure the world is backed up."
assert_stopped "$SERVER_DIR"
BACKUP="$SERVER_DIR/mods-backup-$(date +%Y%m%d-%H%M%S)"
CHANGED=0
while IFS='|' read -r name orig osha patched url sha; do
  echo "== $name"
  if [ -f "$MODS/$patched" ] && [ "$(sha256sum "$MODS/$patched" | cut -d' ' -f1)" = "$sha" ]; then
    echo "   already patched, skipping"; continue
  fi
  curl -fsSL "$url" -o "$TMP/$patched" || die "download failed: $url"
  [ "$(sha256sum "$TMP/$patched" | cut -d' ' -f1)" = "$sha" ] || die "SHA-256 mismatch for $patched"
  mkdir -p "$BACKUP"
  if [ -f "$MODS/$orig" ]; then
    [ "$(sha1sum "$MODS/$orig" | cut -d' ' -f1)" = "$osha" ] \
      || die "$orig is not the original pack jar (unexpected SHA-1) - refusing to replace"
    mv -v "$MODS/$orig" "$BACKUP/"
  fi
  # an older patched build is replaced too (kept in backup)
  [ -f "$MODS/$patched" ] && mv -v "$MODS/$patched" "$BACKUP/"
  cp -v "$TMP/$patched" "$MODS/$patched"
  CHANGED=1
done < <(read_manifest "$TMP/patches.json")

[ "$CHANGED" = 1 ] && echo "Done. Originals backed up in $BACKUP" || echo "Nothing to do."
