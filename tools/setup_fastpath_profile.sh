#!/usr/bin/env bash
# tools/setup_fastpath_profile.sh - Aegis fast-path profile setup
#
# Usage:
#   bash tools/setup_fastpath_profile.sh [--fixture=s3|default] [--launch]
#
# Profiles created:
#   - default: profiles/aegis-default (unlocked JIT/WASM, normal browsing)
#   - s3:      profiles/aegis-s3      (named fixture: locked JIT/WASM off)

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ESR_DIR="$REPO_ROOT/firefox-esr"
FIXTURE="default"
LAUNCH=0

for arg in "$@"; do
    case "$arg" in
        --fixture=s3|--s3)
            FIXTURE="s3"
            ;;
        --fixture=default)
            FIXTURE="default"
            ;;
        --launch)
            LAUNCH=1
            ;;
    esac
done

if [ "$FIXTURE" = "s3" ]; then
    PROFILE_DIR="$REPO_ROOT/profiles/aegis-s3"
    CFG_SRC="$REPO_ROOT/config/axes/surface/s3-fixture.cfg"
else
    PROFILE_DIR="$REPO_ROOT/profiles/aegis-default"
    CFG_SRC="$REPO_ROOT/config/autoconfig/aegis.cfg"
fi

echo "=== Aegis fast-path setup ==="
echo "Repo root: $REPO_ROOT"
echo "ESR dir:   $ESR_DIR"
echo "Fixture:   $FIXTURE"
echo "Config:    $CFG_SRC"
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

# -- 4. Install selected autoconfig .cfg --------------------------------------
if [ ! -f "$CFG_SRC" ]; then
    echo "ERROR: Configuration file $CFG_SRC not found."
    exit 1
fi
cp "$CFG_SRC" "$ESR_DIR/aegis.cfg"
echo "Installed: $CFG_SRC -> $ESR_DIR/aegis.cfg"

# -- 5. Create profile directory ----------------------------------------------
mkdir -p "$PROFILE_DIR"
echo "Profile dir: $PROFILE_DIR"

echo ""
echo "=== Setup complete ==="
echo ""
echo "To verify, launch with:"
echo "  $FIREFOX_BIN -profile $PROFILE_DIR --no-remote"
echo ""

# -- 6. Optional launch -------------------------------------------------------
if [ "$LAUNCH" -eq 1 ]; then
    echo "Launching Firefox ESR with profile $PROFILE_DIR..."
    "$FIREFOX_BIN" -profile "$PROFILE_DIR" --no-remote &
    echo "Firefox ESR launched (PID $!)."
fi
