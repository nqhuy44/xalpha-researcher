#!/usr/bin/env bash
# =============================================================================
# xalpha-researcher — Initial Setup Script
# Usage: bash scripts/setup.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Setting up xalpha-researcher..."
echo "   Project dir: $PROJECT_DIR"

# ---------------------------------------------------------------------------
# 1. Python Virtual Environment
# ---------------------------------------------------------------------------
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv "$PROJECT_DIR/.venv"
else
    echo "✅ Virtual environment already exists."
fi

# Activate venv
# shellcheck disable=SC1091
source "$PROJECT_DIR/.venv/bin/activate"

echo "📦 Upgrading pip..."
pip install --upgrade pip --quiet

# ---------------------------------------------------------------------------
# 2. Install Poetry & Dependencies
# ---------------------------------------------------------------------------
if ! command -v poetry &> /dev/null; then
    echo "📦 Installing Poetry..."
    pip install poetry --quiet
fi

echo "📦 Installing project dependencies..."
cd "$PROJECT_DIR"
poetry install

# ---------------------------------------------------------------------------
# 3. Environment File
# ---------------------------------------------------------------------------
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "📋 Creating .env from .env.example..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "⚠️  Please edit .env with your actual API keys and credentials."
else
    echo "✅ .env file already exists."
fi

# ---------------------------------------------------------------------------
# 4. Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================="
echo "✅ Setup complete!"
echo "============================================="
echo ""
echo "Next steps:"
echo "  1. Activate venv:  source .venv/bin/activate"
echo "  2. Edit .env:      nano .env"
echo "  3. Start infra:    make docker-up"
echo "  4. Run app:        make run"
echo ""
