#!/usr/bin/env bash
# tools/setup_fastpath_profile.sh — Aegis fast-path profile setup
#
# Usage: bash tools/setup_fastpath_profile.sh [--launch]
#
# This script:
#   1. Checks that firefox-esr/ exists (the extracted ESR tarball).
#   2. Copies policies.json to firefox-esr/distribution/
#   3. Copies autoconfig.js to firefox-esr/defaults/pref/
#   4. Copies aegis.cfg to firefox-esr/
#   5. Creates profiles/aegis-fastpath if it does not exist.
#   6. Optionally launches Firefox ESR with --no-remote and the Aegis profile.
#
# Does NOT download the tarball — run that manually after reading docs/BUILD.md.
# Does NOT modify the system Firefox installation.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ESR_DIR="$REPO_ROOT/firefox-esr"
PROFILE_DIR="$REPO_ROOT/profiles/aegis-fastpath"
LAUNCH=0

for arg in "$@"; do
    [ "$arg" = "--launch" ] && LAUNCH=1
done

echo "=== Aegis fast-path setup ==="
echo "Repo root: $REPO_ROOT"
echo "ESR dir:   $ESR_DIR"
echo "Profile:   $PROFILE_DIR"
echo ""

# ── 1. Check ESR directory ────────────────────────────────────────────────────
if [ ! -d "$ESR_DIR" ]; then
    echo "ERROR: firefox-esr/ directory not found."
    echo "Download and extract the Firefox ESR 153.5.1 tarball first."
    echo "See docs/BUILD.md Part A steps A1-A2."
    exit 1
fi

FIREFOX_BIN="$ESR_DIR/firefox"
if [ ! -f "$FIREFOX_BIN" ]; then
    echo "ERROR: $FIREFOX_BIN not found. Check that the tarball unpacked correctly."
    echo "The tarball may have unpacked as 'firefox/' — rename to 'firefox-esr/'."
    exit 1
fi

ACTUAL_VERSION=$("$FIREFOX_BIN" --version 2>/dev/null || echo "unknown")
PINNED_VERSION=$(cat "$REPO_ROOT/upstream/VERSION" | tr -d '[:space:]')
echo "ESR binary version: $ACTUAL_VERSION"
echo "Pinned version:     $PINNED_VERSION"
echo ""

# ── 2. Install policies.json ──────────────────────────────────────────────────
POLICY_SRC="$REPO_ROOT/config/policy/policies.json"
POLICY_DST_DIR="$ESR_DIR/distribution"
mkdir -p "$POLICY_DST_DIR"
cp "$POLICY_SRC" "$POLICY_DST_DIR/policies.json"
echo "Installed: $POLICY_DST_DIR/policies.json"

# ── 3. Install autoconfig.js ──────────────────────────────────────────────────
AUTOCONFIG_SRC="$REPO_ROOT/config/autoconfig/autoconfig.js"
AUTOCONFIG_DST_DIR="$ESR_DIR/defaults/pref"
mkdir -p "$AUTOCONFIG_DST_DIR"
cp "$AUTOCONFIG_SRC" "$AUTOCONFIG_DST_DIR/autoconfig.js"
echo "Installed: $AUTOCONFIG_DST_DIR/autoconfig.js"

# ── 4. Install aegis.cfg ──────────────────────────────────────────────────────
CFG_SRC="$REPO_ROOT/config/autoconfig/aegis.cfg"
cp "$CFG_SRC" "$ESR_DIR/aegis.cfg"
echo "Installed: $ESR_DIR/aegis.cfg"

# ── 5. Create profile directory ───────────────────────────────────────────────
mkdir -p "$PROFILE_DIR"
echo "Profile dir: $PROFILE_DIR"

echo ""
echo "=== Setup complete ==="
echo ""
echo "To verify policies are applied, launch with:"
echo "  $FIREFOX_BIN -profile $PROFILE_DIR --no-remote"
echo "Then navigate to about:policies and about:config."
echo ""

# ── 6. Optional launch ────────────────────────────────────────────────────────
if [ "$LAUNCH" -eq 1 ]; then
    echo "Launching Firefox ESR with Aegis fast-path profile..."
    "$FIREFOX_BIN" -profile "$PROFILE_DIR" --no-remote &
    echo "Firefox ESR launched (PID $!). Check about:policies to verify."
fi
