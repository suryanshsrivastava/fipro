# Contributing to Fipro

Thanks for contributing.

## Development Setup

```bash
./scripts/setup.sh
```

Or manual setup:

```bash
uv sync --all-groups
uv run pre-commit install
```

## Required Quality Gates

Run before opening a PR:

```bash
uv run ruff check src/ tests/ conftest.py
uv run ruff format --check src/ tests/ conftest.py
uv run mypy src/
uv run pytest -q
```

## Change Process

1. Create a feature branch.
2. Implement and test.
3. Add/update docs when behavior changes.
4. Add a `.changeset/*.md` entry for user-visible changes.
5. Open PR using the repository PR template.

## Data Safety Rules

- Never commit real customer/bank data.
- Keep fixtures anonymized.
- Do not commit credentials (service account JSON, `.env`, tokens).

## Pull Request Expectations

- Explain the user impact.
- Include test evidence.
- Call out any parser format assumptions.
- Mention follow-up work if scope is intentionally limited.

## Releases

Use:

```bash
./scripts/release.sh <patch|minor|major>
```

See `RUNBOOK.md` for full release checklist.
