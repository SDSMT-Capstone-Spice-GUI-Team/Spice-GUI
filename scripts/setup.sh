#!/usr/bin/env bash
set -e

echo "=== Spice-GUI Development Setup ==="

# Check prerequisites
PYTHON=""
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "ERROR: Python 3.11+ is required but not found."
    exit 1
fi

echo "Using Python: $($PYTHON --version)"

if ! command -v gh &>/dev/null; then
    echo "ERROR: GitHub CLI (gh) is required. Install from https://cli.github.com/"
    exit 1
fi

if ! gh auth status &>/dev/null; then
    echo "ERROR: gh CLI is not authenticated. Run: gh auth login"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
$PYTHON -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r app/requirements.txt
pip install pytest ruff

# Verify
echo "Verifying test collection..."
python -m pytest --co -q 2>/dev/null | tail -1

echo ""
echo "=== Setup complete ==="
echo "Activate with: source .venv/bin/activate"
