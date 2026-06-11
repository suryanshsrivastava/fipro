# Changelog

All notable changes to Fipro are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/).

Changesets accumulate under `.changeset/` between releases. Run the release script to consolidate them into this file.

## [Unreleased]

### Added

- Changesets workflow under `.changeset/` for release tracking.
- `CHANGELOG.md` at repo root.
- `scripts/release.sh` for tag-based release automation.
- Full agent-readiness tooling: ruff lint + format, mypy, pytest-cov, pre-commit hooks, uv.lock, vulture, gitleaks config.
- Level 1 baseline: CODEOWNERS, `.env.example`, `.devcontainer/`, `RUNBOOK.md`.
- Level 3 additions: `ARCHITECTURE.md`, `scripts/setup.sh`, integration test suite.
- `.cursor/rules/` expanded with agent guardrails and PII ban on fixtures.

### Changed

- `AGENTS.md` commands aligned with wired tooling (all `uv run ...` now executable).
- `fipro-docs/PRD.md` section 12.3 table updated; section 13.1 formatter entry revised to `ruff format (black-compatible)`.
- `pyproject.toml` now gates on `fail_under = 50` coverage baseline (PRD section 14.1 aspirational target 80%; ratchet upward over time).

### Deferred

- PR #8 code-review blockers: PII scrub in fixtures, Transaction hash collision risk (`HASH-001`), Goodbudget CSV column split (`CSV-001`), Google Sheets API-shape bugs (`SHEETS-001`), transfer detector O(n^2) + 1:many matching (`PERF-001`). Track via separate plan.

## [0.1.0] — Initial

- Project scaffolded. Bank statement parsing for HDFC, SBI, Axis. Goodbudget CSV export. Local dashboard. Google Sheets exporter (advisory; has known bugs).
