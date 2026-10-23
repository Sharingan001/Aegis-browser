#!/usr/bin/env bash
# tools/install_hooks.sh — install Aegis git hooks
# Run once from the repo root: bash tools/install_hooks.sh

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
    echo "ERROR: $HOOKS_DIR not found. Run 'git init' first."
    exit 1
fi

cp "$REPO_ROOT/tools/pre-commit.hook" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"
echo "Installed: $HOOKS_DIR/pre-commit"
echo "Done. The hook runs tests/runner.sh before every commit."
