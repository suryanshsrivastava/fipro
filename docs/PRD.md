# Fipro Product Requirements Document (PRD)

## 1. Product Overview

Fipro is a local-first Python CLI that ingests monthly bank statement exports (HDFC, SBI, Axis), normalizes transactions, deduplicates records, detects probable internal transfers, and exports Goodbudget-compatible CSV.

## 2. Problem Statement

Manual statement entry is slow and error-prone. Users need a reliable way to consolidate multi-bank statements into one clean export without sending financial data to external services.

## 3. Goals

- Extract transactions accurately from supported statement formats.
- Provide one consolidated ledger across all configured banks.
- Minimize duplicate records and surface likely internal transfers.
- Export a Goodbudget-ready CSV with predictable formatting.

## 4. Non-Goals (MVP)

- Cloud sync / multi-user collaboration.
- Automated category prediction.
- Full personal finance dashboard product.
- OCR/PDF pipelines beyond current scoped parsers.

## 5. Target User

Single user operating on a personal machine who downloads statements manually from bank portals and wants quick monthly consolidation.

## 6. Functional Requirements

1. **Ingestion**: Discover `.xls`/`.xlsx` statements under `data/input/`.
2. **Routing**: Choose parser based on filename/content heuristics.
3. **Extraction**: Parse date, description, debit/credit, and balance metadata.
4. **Transformation**: Normalize to `Transaction` model using `Decimal` amounts.
5. **Consolidation**: Sort, deduplicate, and classify likely internal transfers.
6. **Export**:
   - `goodbudget_export.csv`
   - processing report (`processing_report.json`)
7. **CLI Commands**:
   - `fipro process`
   - `fipro status`
   - `fipro dashboard`
   - `fipro sheets`

## 7. Data & Privacy Requirements

- Local-first processing; no automatic upload of financial data.
- Secrets and credentials are excluded from git.
- Fixtures must remain anonymized (no real names/account IDs/UPI references).

## 8. Quality Requirements

- Lint/type/test gates must pass before merge:
  - `ruff check`
  - `ruff format --check`
  - `mypy`
  - `pytest`
- Coverage must not regress below configured threshold in `pyproject.toml`.

## 9. Performance & Reliability

- Typical monthly runs should complete quickly on a laptop (< 5s target for common fixture-scale inputs).
- Parser failures should be isolated per file and logged to `data/failed/*` with error context.

## 10. Packaging & Runtime

- Python 3.14+
- Dependency management with uv (`uv.lock` committed)
- Distribution as CLI application (`project.scripts` entrypoint)

## 11. Risks

- Bank format drift causing parser failures.
- Fixture anonymization regressions.
- Deduplication collisions if hash inputs are insufficiently unique.

## 12. Planning and Change Tracking

### 12.1 Source of truth

- Product/process expectations: `AGENTS.md`
- Runtime/ops behavior: `RUNBOOK.md`
- Architecture details: `docs/architecture.md`

### 12.2 Release discipline

- Use `.changeset/*.md` entries for user-visible changes.
- Consolidate releases into `CHANGELOG.md` using `scripts/release.sh`.

### 12.3 Plan Documents Index

| Date | Document | Purpose |
|------|----------|---------|
| 2026-03-11 | `docs/plans/2026-03-11-raw-export-extraction-fixtures-design.md` | Fixture-driven extraction design |
| 2026-03-11 | `docs/plans/2026-03-11-raw-export-extraction-fixtures-runbook.md` | Fixture refresh runbook |
| 2026-04-14 | `docs/plans/2026-04-14-agent-ready-minimum.md` | Agent-ready minimum quality baseline |
| 2026-04-18 | `docs/plans/2026-04-18-level-3-readiness-design.md` | Legit Level-3 readiness design |

## 13. Success Metrics

- High extraction accuracy on maintained fixture corpus.
- Stable dedup + transfer detection behavior over monthly runs.
- Repeatable contributor workflow (setup + CI parity + docs clarity).
