## Summary

- What changed?
- Why was it needed?

## Validation

- [ ] `uv run ruff check src/ tests/ conftest.py`
- [ ] `uv run ruff format --check src/ tests/ conftest.py`
- [ ] `uv run mypy src/`
- [ ] `uv run pytest -q`

## Risk and Rollback

- Risk level: low / medium / high
- Rollback strategy:

## Data & Privacy

- [ ] No real financial/PII data introduced in fixtures, logs, or docs.
- [ ] No secrets/credentials committed.

## Documentation

- [ ] README / RUNBOOK / docs updated (if behavior changed)
- [ ] `.changeset/*.md` entry added for user-visible changes
