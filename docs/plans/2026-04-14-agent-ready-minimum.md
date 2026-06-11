# 2026-04-14 Agent Ready Minimum

Wire the tools AGENTS.md promises, add pre-commit feedback, make setup reproducible, and tighten `.cursor/rules` for Cursor/Codex agents. Scope is deliberately pragmatic: only changes that directly affect agent productivity.

## Alignment with PRD

| PRD clause | Response |
|---|---|
| 13.1: ruff (linting) | Wired as `[tool.ruff]` in `pyproject.toml` |
| 13.1: mypy (type checking) | Wired as `[tool.mypy]` in `pyproject.toml` |
| 13.1: pytest (testing) | Wired as `[tool.pytest.ini_options]` in `pyproject.toml` |
| 13.1: black (formatting) | Replaced by `ruff format` (black-compatible output, single tool). PRD 13.1 updated to reflect. |
| 14.1: 80% coverage target | `pytest-cov` wired with `fail_under = 50` as regression baseline; raise to 80% as tests are added |
| 12.3: Plan sync rule | This plan file; PRD 12.3 table updated |

## Five Levers

### Lever 1 — Honest build/test/lint commands

- `pyproject.toml` gains `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`, `[tool.coverage.*]`.
- Dev deps extended: `pytest-cov`, `ruff`, `mypy`, `pre-commit`.
- `conftest.py` at repo root ensures pytest imports resolve from any cwd.

### Lever 2 — Pre-commit feedback

- `.pre-commit-config.yaml` with ruff (lint + format), large-file detection (500KB cap), merge-conflict, TOML/YAML validation.
- `check-added-large-files` explicitly guards the class of issue that caused PR #8 binary fixture bloat.

### Lever 3 — Reproducible setup

- `uv.lock` tracked (removed from `.gitignore`).
- Root `README.md` with quickstart and common commands.

### Lever 4 — Cursor/Codex rules

- `.cursor/rules/instructions.mdc` (renamed from typo `instuctions.mdc`), aligned with actual `src/utils/` layout.
- `.cursor/rules/python-best-practices.mdc` expanded with `Decimal`-for-money, `Enum` for choices, `slots=True`, PII ban on fixtures.
- `.cursor/rules/agent-guardrails.mdc` added — always-applied, lists the pre-commit command set and explicit PII prohibition.

### Lever 5 — PRD sync

- This file mirrored into `docs/plans/`.
- PRD section 12.3 table gains a 2026-04-14 row.
- PRD section 13.1 updated to replace `black` with `ruff format (black-compatible)`.
- PRD `Last Updated` bumped.

## Coverage Ratchet

Current coverage is 51% across 40 tests. The 80% PRD target is aspirational. The `fail_under` gate is set at 50% so future commits cannot regress. Raise the gate incrementally as tests are added. Never lower it.

Recommended next targets:
- Add tests for `src/core/transformer.py` (0% today) → +5% overall
- Add tests for `src/utils/utils.py` (0% today) → +2% overall
- Add tests for `src/config.py` (0% today) → +3% overall
- Add integration tests for `src/core/orchestrator.py` → +5% overall

## Out of Scope (deferred)

- GitHub Actions CI
- CODEOWNERS, PR/issue templates
- Secret scanning (gitleaks)
- `.devcontainer`
- PR #8 code-review blockers (PII scrub, hash fix, Goodbudget CSV split) — separate plan

## Outcome

Agent running `AGENTS.md` commands end-to-end lands a green build. Pre-commit catches formatting, large files, and merge conflicts before they land. `uv sync --all-groups` gives deterministic dependency resolution. `.cursor/rules/` explicitly forbid the PII pattern that caused PR #8 critical finding. PRD stays truthful.
