#!/bin/bash
# Install GeoRisk Oracle git hooks
# Run once after cloning: bash scripts/install-hooks.sh

HOOK_DIR=".git/hooks"
SCRIPT_DIR="scripts"

echo "Installing GeoRisk Oracle git hooks..."

# Pre-commit: blocks sensitive data
cp "$SCRIPT_DIR/pre-commit-hook.sh" "$HOOK_DIR/pre-commit"
chmod +x "$HOOK_DIR/pre-commit"
echo "✅ pre-commit hook installed"

echo ""
echo "Done. Every commit will now be scanned for sensitive data."
echo "To test: git commit --dry-run"
