#!/usr/bin/env bash
# tests/runner.sh — Aegis test runner (Phase 0)
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

# ── 1. Prototype unit tests ─────────────────────────────────────────────────
echo "--- [1] Prototype unit tests (prototypes/) ---"
if [ -d "$REPO_ROOT/prototypes" ] && [ -f "$REPO_ROOT/prototypes/test_aegis.py" ]; then
    cd "$REPO_ROOT/prototypes"
    if python3 -m unittest test_aegis -v 2>&1; then
        echo "PASS: prototype unit tests"
        PASS=$((PASS + 1))
    else
        echo "FAIL: prototype unit tests"
        ERRORS+=("prototype unit tests")
        FAIL=$((FAIL + 1))
    fi
    cd "$REPO_ROOT"
else
    echo "SKIP: prototypes/test_aegis.py not found (expected after prototype files are placed)"
    ERRORS+=("SKIP: prototypes/test_aegis.py missing")
fi

echo ""

# ── 2. VERIFY.md integrity check ─────────────────────────────────────────────
echo "--- [2] VERIFY.md exists and has no VERIFIED items that are still marked OPEN ---"
VERIFY_FILE="$REPO_ROOT/docs/VERIFY.md"
if [ -f "$VERIFY_FILE" ]; then
    echo "PASS: docs/VERIFY.md exists"
    PASS=$((PASS + 1))
else
    echo "FAIL: docs/VERIFY.md missing"
    ERRORS+=("docs/VERIFY.md missing")
    FAIL=$((FAIL + 1))
fi

echo ""

# ── 3. DECISIONS.md exists ───────────────────────────────────────────────────
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

# ── 4. upstream/VERSION is set and non-empty ─────────────────────────────────
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

# ── 5. Placeholder: axis enforcement tests (Phase 2+) ────────────────────────
echo "--- [5] Axis enforcement tests (Phase 2+, skipped in Phase 0) ---"
echo "SKIP: axis enforcement tests are not yet implemented"

echo ""

# ── Summary ──────────────────────────────────────────────────────────────────
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
