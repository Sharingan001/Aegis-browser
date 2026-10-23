#!/usr/bin/env bash
# tools/setup_fastpath_profile.sh - Aegis fast-path profile setup
#
# Usage: bash tools/setup_fastpath_profile.sh [--launch]
#
# This script:
#   1. Checks that firefox-esr/ exists (the extracted ESR tarball).
#   2. Validates that the ESR binary version matches upstream/VERSION.
#   3. Validates policies.json schema before copying.
#   4. Copies policies.json to firefox-esr/distribution/
#   5. Copies autoconfig.js to firefox-esr/defaults/pref/
#   6. Copies aegis.cfg to firefox-esr/
#   7. Creates profiles/aegis-fastpath if it does not exist.
#   8. Optionally launches Firefox ESR with --no-remote and the Aegis profile.

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

# -- 1. Check ESR directory and binary version --------------------------------
if [ ! -d "$ESR_DIR" ]; then
    echo "ERROR: firefox-esr/ directory not found."
    echo "Download and extract the Firefox ESR tarball first into downloads/ and extract."
    echo "See docs/BUILD.md Part A."
    exit 1
fi

FIREFOX_BIN="$ESR_DIR/firefox"
if [ ! -f "$FIREFOX_BIN" ]; then
    echo "ERROR: $FIREFOX_BIN not found. Check that the tarball unpacked correctly."
    echo "The tarball may have unpacked as 'firefox/' - rename or move to 'firefox-esr/'."
    exit 1
fi

RAW_VERSION=$("$FIREFOX_BIN" --version 2>/dev/null || echo "unknown")
ACTUAL_VERSION=$(echo "$RAW_VERSION" | awk '{print $NF}')
PINNED_VERSION=$(cat "$REPO_ROOT/upstream/VERSION" | tr -d '[:space:]')

echo "ESR binary version: $ACTUAL_VERSION (from '$RAW_VERSION')"
echo "Pinned version:     $PINNED_VERSION"

# Version match check (strip trailing 'esr' for comparison if needed)
NORM_ACTUAL="${ACTUAL_VERSION%esr}"
NORM_PINNED="${PINNED_VERSION%esr}"

if [ "$NORM_ACTUAL" != "$NORM_PINNED" ]; then
    echo "ERROR: Binary version mismatch! Expected '$PINNED_VERSION' but binary reports '$ACTUAL_VERSION'."
    exit 1
fi
echo "Version check: OK"
echo ""

# -- 2. Validate and install policies.json ------------------------------------
POLICY_SRC="$REPO_ROOT/config/policy/policies.json"
POLICY_DST_DIR="$ESR_DIR/distribution"

if [ ! -f "$POLICY_SRC" ]; then
    echo "ERROR: Policy source file $POLICY_SRC not found."
    exit 1
fi

# Validate JSON and disallow underscore keys
if ! python3 -c "
import json, sys
try:
    with open('$POLICY_SRC') as f:
        data = json.load(f)
except Exception as e:
    sys.exit(f'Invalid JSON: {e}')

if 'policies' not in data:
    sys.exit('Missing root policies key')

def check_keys(obj, path=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith('_'):
                sys.exit(f'Disallowed key: {path}{k}')
            check_keys(v, f'{path}{k}.')
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            check_keys(item, f'{path}[{i}].')

check_keys(data['policies'], 'policies.')
"; then
    echo "ERROR: $POLICY_SRC failed validation. Aborting installation."
    exit 1
fi
echo "Policy JSON validation: OK"

mkdir -p "$POLICY_DST_DIR"
cp "$POLICY_SRC" "$POLICY_DST_DIR/policies.json"
echo "Installed: $POLICY_DST_DIR/policies.json"

# -- 3. Install autoconfig.js -------------------------------------------------
AUTOCONFIG_SRC="$REPO_ROOT/config/autoconfig/autoconfig.js"
AUTOCONFIG_DST_DIR="$ESR_DIR/defaults/pref"
mkdir -p "$AUTOCONFIG_DST_DIR"
cp "$AUTOCONFIG_SRC" "$AUTOCONFIG_DST_DIR/autoconfig.js"
echo "Installed: $AUTOCONFIG_DST_DIR/autoconfig.js"

# -- 4. Install aegis.cfg -----------------------------------------------------
CFG_SRC="$REPO_ROOT/config/autoconfig/aegis.cfg"
cp "$CFG_SRC" "$ESR_DIR/aegis.cfg"
echo "Installed: $ESR_DIR/aegis.cfg"

# -- 5. Create profile directory ----------------------------------------------
mkdir -p "$PROFILE_DIR"
echo "Profile dir: $PROFILE_DIR"

echo ""
echo "=== Setup complete ==="
echo ""
echo "To verify policies are applied, launch with:"
echo "  $FIREFOX_BIN -profile $PROFILE_DIR --no-remote"
echo "Then navigate to about:policies and about:config."
echo ""

# -- 6. Optional launch -------------------------------------------------------
if [ "$LAUNCH" -eq 1 ]; then
    echo "Launching Firefox ESR with Aegis fast-path profile..."
    "$FIREFOX_BIN" -profile "$PROFILE_DIR" --no-remote &
    echo "Firefox ESR launched (PID $!). Check about:policies to verify."
fi
