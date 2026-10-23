#!/usr/bin/env bash
# tests/runner.sh - Aegis test runner (Phase 0)
# Run from the repo root: bash tests/runner.sh
# Exit code 0 = all pass; non-zero = failure.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
FAIL=0
ERRORS=()

echo "=== Aegis test runner ==="
echo "Repo: $REPO_ROOT"
echo "Date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""

# -- 1. Prototype unit tests -------------------------------------------------
echo "--- [1] Prototype unit tests (prototypes/) ---"
PY_COUNT=$(find "$REPO_ROOT/prototypes" -maxdepth 1 -name "*.py" 2>/dev/null | wc -l)
if [ -f "$REPO_ROOT/prototypes/test_aegis.py" ]; then
    cd "$REPO_ROOT/prototypes"
    if python3 -m unittest test_aegis -v 2>&1; then
        echo "PASS: prototype unit tests (all tests passed)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: prototype unit tests failed"
        ERRORS+=("prototype unit tests failed")
        FAIL=$((FAIL + 1))
    fi
    cd "$REPO_ROOT"
elif [ "$PY_COUNT" -gt 0 ]; then
    echo "FAIL: prototypes/ contains Python files but test_aegis.py is missing"
    ERRORS+=("prototypes/test_aegis.py missing")
    FAIL=$((FAIL + 1))
else
    echo "SKIP: prototypes/test_aegis.py not found (prototypes directory not yet populated)"
fi

echo ""

# -- 2. VERIFY.md presence and format check ----------------------------------
echo "--- [2] docs/VERIFY.md presence and format check ---"
VERIFY_FILE="$REPO_ROOT/docs/VERIFY.md"
if [ -f "$VERIFY_FILE" ]; then
    # Verify it has standard table headers and sections
    if grep -q "## Axis S:" "$VERIFY_FILE" && grep -q "## Axis I:" "$VERIFY_FILE" && grep -q "## Axis N:" "$VERIFY_FILE"; then
        echo "PASS: docs/VERIFY.md exists with required axis sections"
        PASS=$((PASS + 1))
    else
        echo "FAIL: docs/VERIFY.md missing required axis sections"
        ERRORS+=("docs/VERIFY.md missing required axis sections")
        FAIL=$((FAIL + 1))
    fi
else
    echo "FAIL: docs/VERIFY.md missing"
    ERRORS+=("docs/VERIFY.md missing")
    FAIL=$((FAIL + 1))
fi

echo ""

# -- 3. DECISIONS.md exists ---------------------------------------------------
echo "--- [3] docs/DECISIONS.md exists ---"
if [ -f "$REPO_ROOT/docs/DECISIONS.md" ]; then
    echo "PASS: docs/DECISIONS.md exists"
    PASS=$((PASS + 1))
else
    echo "FAIL: docs/DECISIONS.md missing"
    ERRORS+=("docs/DECISIONS.md missing")
    FAIL=$((FAIL + 1))
fi

echo ""

# -- 4. upstream/VERSION is set and non-empty ---------------------------------
echo "--- [4] upstream/VERSION is set ---"
VERSION_FILE="$REPO_ROOT/upstream/VERSION"
if [ -f "$VERSION_FILE" ] && [ -s "$VERSION_FILE" ]; then
    VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')
    echo "PASS: upstream/VERSION = $VERSION"
    PASS=$((PASS + 1))
else
    echo "FAIL: upstream/VERSION missing or empty"
    ERRORS+=("upstream/VERSION missing or empty")
    FAIL=$((FAIL + 1))
fi

echo ""

# -- 5. policies.json syntax and schema validation ---------------------------
echo "--- [5] config/policy/policies.json validation ---"
POLICY_FILE="$REPO_ROOT/config/policy/policies.json"
if [ -f "$POLICY_FILE" ]; then
    if python3 -c "
import json, sys
try:
    with open('$POLICY_FILE') as f:
        data = json.load(f)
except Exception as e:
    sys.exit(f'Invalid JSON: {e}')

if 'policies' not in data:
    sys.exit('Missing root policies key')

def check_no_underscore_keys(obj, path=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith('_'):
                sys.exit(f'Disallowed key starting with underscore: {path}{k}')
            check_no_underscore_keys(v, f'{path}{k}.')
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            check_no_underscore_keys(item, f'{path}[{i}].')

check_no_underscore_keys(data['policies'], 'policies.')
"; then
        echo "PASS: config/policy/policies.json is valid JSON with no underscore keys in policies"
        PASS=$((PASS + 1))
    else
        echo "FAIL: config/policy/policies.json validation failed"
        ERRORS+=("policies.json validation failed")
        FAIL=$((FAIL + 1))
    fi
else
    echo "FAIL: config/policy/policies.json missing"
    ERRORS+=("config/policy/policies.json missing")
    FAIL=$((FAIL + 1))
fi

echo ""

# -- 6. Autoconfig ASCII check -----------------------------------------------
echo "--- [6] Autoconfig ASCII check ---"
AUTOCONFIG_JS="$REPO_ROOT/config/autoconfig/autoconfig.js"
AEGIS_CFG="$REPO_ROOT/config/autoconfig/aegis.cfg"
ASCII_OK=1

for f in "$AUTOCONFIG_JS" "$AEGIS_CFG"; do
    if [ -f "$f" ]; then
        if ! python3 -c "open('$f', 'rb').read().decode('ascii')" 2>/dev/null; then
            echo "FAIL: $f contains non-ASCII characters"
            ERRORS+=("$f contains non-ASCII characters")
            ASCII_OK=0
        fi
    else
        echo "FAIL: $f missing"
        ERRORS+=("$f missing")
        ASCII_OK=0
    fi
done

if [ "$ASCII_OK" -eq 1 ]; then
    echo "PASS: autoconfig.js and aegis.cfg are strictly ASCII"
    PASS=$((PASS + 1))
else
    FAIL=$((FAIL + 1))
fi

echo ""

# -- 7. Placeholder: axis enforcement tests (Phase 2+) -----------------------
echo "--- [7] Axis enforcement tests (Phase 2+, skipped in Phase 0) ---"
echo "SKIP: axis enforcement tests are not yet implemented"

echo ""

# -- Summary ------------------------------------------------------------------
echo "=== Summary ==="
echo "PASS: $PASS"
echo "FAIL: $FAIL"
if [ ${#ERRORS[@]} -gt 0 ]; then
    echo "Issues:"
    for e in "${ERRORS[@]}"; do
        echo "  - $e"
    done
fi
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "RESULT: FAILED"
    exit 1
else
    echo "RESULT: OK"
    exit 0
fi
