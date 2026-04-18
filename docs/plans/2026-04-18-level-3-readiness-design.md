# Level 3 Readiness Design (Legit, Not Checkbox-Only)

**Date:** 2026-04-18
**Repo:** `fipro`
**Goal:** Raise the repository to practical Level-3 engineering readiness while preserving a lightweight Python CLI workflow.

## Problem

Fipro already has strong local tooling (uv, Ruff, MyPy, pytest, pre-commit, runbook), but collaboration and automation gaps remain:

- missing GitHub workflow scaffolding (`.github/workflows`)
- missing issue/PR contribution templates
- broken doc references (`fipro-docs/*` paths no longer exist)
- no CI-enforced freshness checks for `AGENTS.md` and critical docs links

## Design Principles

1. **Keep local-first ergonomics**: no heavy platform dependencies.
2. **Mirror local quality gates in CI**: Ruff, format-check, MyPy, pytest.
3. **Make contribution flow explicit**: templates, labels, dependabot.
4. **Make docs canonical and real**: fix broken links and create stable docs paths.
5. **Prefer practical safety controls**: gitleaks + CodeQL + agent-doc freshness checks.

## Proposed Changes

### 1) Documentation foundation

- Add `docs/PRD.md` as canonical product requirements doc.
- Add `docs/architecture.md` as canonical architecture doc.
- Update `README.md`, `ARCHITECTURE.md`, and `RUNBOOK.md` to reference canonical paths.
- Add `CONTRIBUTING.md` with setup, quality gates, and PR expectations.

### 2) CI and security automation

- Add `.github/workflows/ci.yml` for lint/type/test checks.
- Add `.github/workflows/codeql.yml` for static security analysis.
- Add `.github/workflows/gitleaks.yml` for secret scanning.
- Add `.github/workflows/agents-freshness.yml` to validate AGENTS/docs linkage and command references.

### 3) Contribution and maintenance scaffolding

- Add issue templates (`bug_report.yml`, `feature_request.yml`, `config.yml`).
- Add PR template (`.github/PULL_REQUEST_TEMPLATE.md`).
- Add labels config (`.github/labels.yml`) for consistent triage taxonomy.
- Add `.github/dependabot.yml` for dependency and action updates.

## Out of Scope

- Large architecture rewrites or feature changes in core processing pipeline.
- Cloud deployment setup.
- Multi-maintainer governance policy beyond current CODEOWNERS baseline.

## Validation Plan

- Run local checks:
  - `uv run ruff check src/ tests/ conftest.py`
  - `uv run ruff format --check src/ tests/ conftest.py`
  - `uv run mypy src/`
  - `uv run pytest -q`
- Verify docs links and paths resolve.
- Confirm `.github/` automation files are syntactically valid.

## Expected Outcome

A practical, maintainable repository that is ready for:

- reliable agent/human onboarding,
- consistent quality enforcement in PRs,
- baseline security scanning,
- clear and current documentation,
- structured contribution flow.
