#!/usr/bin/env bash
# Release script for fipro. Consolidates changesets, bumps version, tags, pushes.
# Usage: ./scripts/release.sh <patch|minor|major>
set -euo pipefail

cd "$(dirname "$0")/.."

BUMP="${1:-}"
if [[ -z "${BUMP}" || ! "${BUMP}" =~ ^(patch|minor|major)$ ]]; then
  echo "Usage: $0 <patch|minor|major>" >&2
  exit 1
fi

echo "==> verifying clean working tree"
if ! git diff-index --quiet HEAD --; then
  echo "Working tree has uncommitted changes. Commit or stash first." >&2
  exit 1
fi

echo "==> running quality gates"
uv run ruff check src/ tests/ conftest.py
uv run ruff format --check src/ tests/ conftest.py
uv run mypy src/
uv run pytest -q

echo "==> computing next version"
CURRENT=$(grep -m1 '^version' pyproject.toml | sed -E 's/version = "(.+)"/\1/')
IFS='.' read -r MAJOR MINOR PATCH <<< "${CURRENT}"
case "${BUMP}" in
  patch) NEXT="${MAJOR}.${MINOR}.$((PATCH + 1))" ;;
  minor) NEXT="${MAJOR}.$((MINOR + 1)).0" ;;
  major) NEXT="$((MAJOR + 1)).0.0" ;;
esac

echo "==> bumping ${CURRENT} -> ${NEXT}"
sed -i.bak "s/^version = \"${CURRENT}\"/version = \"${NEXT}\"/" pyproject.toml
rm pyproject.toml.bak

echo "==> consolidating changesets into CHANGELOG.md"
DATE=$(date +%Y-%m-%d)
python3 <<PY
from pathlib import Path
import re

changeset_dir = Path(".changeset")
entries = []
for path in sorted(changeset_dir.glob("*.md")):
    if path.name.lower() == "readme.md":
        continue
    text = path.read_text(encoding="utf-8")
    match = re.search(r"---\s*(.*?)\s*---\s*(.*)", text, re.DOTALL)
    if not match:
        continue
    body = match.group(2).strip()
    if body:
        entries.append(f"- {body}")
    path.unlink()

if entries:
    changelog = Path("CHANGELOG.md")
    old = changelog.read_text(encoding="utf-8")
    block = f"\n## [${NEXT}] - ${DATE}\n\n" + "\n".join(entries) + "\n"
    new = old.replace("## [Unreleased]", "## [Unreleased]\n" + block, 1)
    changelog.write_text(new, encoding="utf-8")
    print(f"Added {len(entries)} entries to CHANGELOG.md")
else:
    print("No changesets to consolidate")
PY

echo "==> committing and tagging"
git add pyproject.toml CHANGELOG.md .changeset/
git commit -m "chore: release v${NEXT}"
git tag -a "v${NEXT}" -m "Release v${NEXT}"

echo "==> pushing commit + tag"
echo "   To publish, run: git push origin HEAD && git push origin v${NEXT}"
echo "==> release prepared: v${NEXT}"
