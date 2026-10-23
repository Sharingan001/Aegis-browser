#!/usr/bin/env bash
# tests/runner.sh - Aegis test runner (Phase 0)
# Run from the repo root: bash tests/runner.sh
# Exit code 0 = all pass; non-zero = failure.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
SKIPPED=0
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

# -- 6. Autoconfig ASCII and Drift check ---------------------------------------
echo "--- [6] Autoconfig ASCII and Drift check ---"
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
    if python3 "$REPO_ROOT/tools/generate_autoconfig.py" --check; then
        echo "PASS: config/autoconfig/aegis.cfg strictly matches config/axes/surface/*.json (no drift)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: config/autoconfig/aegis.cfg has drifted from config/axes/surface/*.json"
        ERRORS+=("Autoconfig drift detected")
        FAIL=$((FAIL + 1))
    fi
else
    FAIL=$((FAIL + 1))
fi

echo ""

# -- 7. LICENSES_AND_TRADEMARKS.md presence check ----------------------------
echo "--- [7] docs/LICENSES_AND_TRADEMARKS.md check ---"
LIC_FILE="$REPO_ROOT/docs/LICENSES_AND_TRADEMARKS.md"
if [ -f "$LIC_FILE" ] && grep -q "MPL 2.0" "$LIC_FILE" && grep -q "LEGAL ADVICE REQUIRED" "$LIC_FILE"; then
    echo "PASS: docs/LICENSES_AND_TRADEMARKS.md exists with required sections"
    PASS=$((PASS + 1))
else
    echo "FAIL: docs/LICENSES_AND_TRADEMARKS.md missing or incomplete"
    ERRORS+=("docs/LICENSES_AND_TRADEMARKS.md missing or incomplete")
    FAIL=$((FAIL + 1))
fi

echo ""

# -- 8. Phase 1a UI & Cell Indicator tests -----------------------------------
echo "--- [8] Phase 1a UI & Cell Indicator tests ---"
if [ -f "$REPO_ROOT/tests/ui/test_cell_indicator.py" ]; then
    if python3 -m unittest tests/ui/test_cell_indicator.py -v 2>&1; then
        echo "PASS: UI, theme, and Cell Indicator tests passed (including honest language lint)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: UI and Cell Indicator tests failed"
        ERRORS+=("UI and Cell Indicator tests failed")
        FAIL=$((FAIL + 1))
    fi
else
    echo "FAIL: tests/ui/test_cell_indicator.py missing"
    ERRORS+=("tests/ui/test_cell_indicator.py missing")
    FAIL=$((FAIL + 1))
fi

echo ""

# -- 9. Phase 2a Surface Levels & Fail-Closed Tier Runtime Tests -------------
echo "--- [9] Phase 2a Surface Levels & Fail-Closed Tier Runtime Tests ---"
SURF_OK=1

# Check level files schema
for tier in s1 s2 s3 s4; do
    if [ ! -f "$REPO_ROOT/config/axes/surface/${tier}.json" ]; then
        echo "FAIL: config/axes/surface/${tier}.json missing"
        ERRORS+=("surface/${tier}.json missing")
        SURF_OK=0
    fi
done

if [ "$SURF_OK" -eq 0 ]; then
    FAIL=$((FAIL + 1))
elif [ ! -f "$REPO_ROOT/firefox-esr/firefox" ]; then
    echo "SKIPPED (requires firefox-esr): Firefox ESR binary not found at firefox-esr/firefox"
    SKIPPED=$((SKIPPED + 1))
elif [ -f "$REPO_ROOT/tests/axes/test_surface_levels.py" ] && [ -f "$REPO_ROOT/tests/axes/test_tier_failclosed.py" ]; then
    if python3 -m unittest tests/axes/test_surface_levels.py tests/axes/test_tier_failclosed.py -v 2>&1; then
        echo "PASS: Phase 2a Surface levels (S1..S4) and fail-closed tier tests passed"
        PASS=$((PASS + 1))
    else
        echo "FAIL: Phase 2a Surface level tests failed"
        ERRORS+=("Phase 2a Surface level tests failed")
        FAIL=$((FAIL + 1))
    fi
else
    echo "FAIL: Surface level test files missing"
    ERRORS+=("Surface level test files missing")
    FAIL=$((FAIL + 1))
fi

echo ""

# -- 10. Phase 2c Multi-Axis Combination Matrix Tests ------------------------
echo "--- [10] Phase 2c Multi-Axis Combination Matrix Tests ---"
if [ -f "$REPO_ROOT/tests/axes/test_tier_matrix.py" ]; then
    if python3 -m unittest tests.axes.test_tier_matrix -v; then
        echo "PASS: Multi-axis 4x4x4 combination matrix tests passed (all rules verified)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: Multi-axis combination matrix tests failed"
        ERRORS+=("test_tier_matrix failed")
        FAIL=$((FAIL + 1))
    fi
else
    echo "FAIL: tests/axes/test_tier_matrix.py missing"
    ERRORS+=("tests/axes/test_tier_matrix.py missing")
    FAIL=$((FAIL + 1))
fi

echo ""

# -- 11. Phase 2c Identity Levels & FPP Override Runtime Tests ---------------
echo "--- [11] Phase 2c Identity Levels & FPP Override Runtime Tests ---"
ID_OK=1
for level in i1 i2 i3 i4; do
    if [ ! -f "$REPO_ROOT/config/axes/identity/${level}.json" ]; then
        echo "FAIL: config/axes/identity/${level}.json missing"
        ERRORS+=("identity/${level}.json missing")
        ID_OK=0
    fi
done

if [ "$ID_OK" -eq 0 ]; then
    FAIL=$((FAIL + 1))
elif [ ! -f "$REPO_ROOT/firefox-esr/firefox" ]; then
    echo "SKIPPED (requires firefox-esr): Firefox ESR binary not found at firefox-esr/firefox"
    SKIPPED=$((SKIPPED + 1))
elif [ -f "$REPO_ROOT/tests/axes/test_identity_levels.py" ]; then
    if python3 -m unittest tests/axes/test_identity_levels.py -v 2>&1; then
        echo "PASS: Phase 2c Identity levels (I1..I4) and FPP override tests passed"
        PASS=$((PASS + 1))
    else
        echo "FAIL: Phase 2c Identity level tests failed"
        ERRORS+=("Phase 2c Identity level tests failed")
        FAIL=$((FAIL + 1))
    fi
else
    echo "FAIL: tests/axes/test_identity_levels.py missing"
    ERRORS+=("tests/axes/test_identity_levels.py missing")
    FAIL=$((FAIL + 1))
fi

echo ""

# -- Summary ------------------------------------------------------------------
echo "=== Summary ==="
echo "PASS: $PASS"
echo "SKIPPED: $SKIPPED"
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
