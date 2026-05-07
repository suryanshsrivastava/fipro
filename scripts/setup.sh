#!/usr/bin/env bash
# One-shot developer bootstrap. Idempotent.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> installing uv (if missing)"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "==> syncing dependencies"
uv sync --all-groups

echo "==> installing pre-commit hooks"
uv run pre-commit install

echo "==> running quality gates"
uv run ruff check src/ tests/ conftest.py
uv run ruff format --check src/ tests/ conftest.py
uv run mypy src/
uv run pytest -q

echo "==> setup complete"
