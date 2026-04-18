# Fipro Runbook

Operational procedures for running and maintaining Fipro. Living document; append new entries as incidents or recurring tasks appear.

## Monthly: Processing Bank Statements

1. Download latest monthly `.xls` exports from HDFC, SBI, and Axis portals.
2. Drop them into `data/input/`.
3. Run `uv run fipro process`.
4. Check `data/output/goodbudget_export.csv` for the consolidated transactions.
5. If anything failed, inspect `data/failed/` for the offending files and their `.error.txt` logs.
6. Review internal transfer flags in the output CSV (Status column = `internal_transfer`).
7. Import CSV into Goodbudget.

## Monthly: Refreshing Test Fixtures

See [docs/plans/2026-03-11-raw-export-extraction-fixtures-runbook.md](docs/plans/2026-03-11-raw-export-extraction-fixtures-runbook.md) for the fixture refresh procedure.

**Critical:** all fixture inputs and expected outputs must be anonymized. No real names, UPI reference numbers, or account numbers.

## Adding a New Bank Parser

1. Subclass `BankParser` in `src/parsers/<bank>.py`.
2. Implement `bank_name`, `can_parse`, `find_header_row`, `extract_transactions`.
3. Register the parser in `src/core/orchestrator.py` `parsers` list.
4. Add fixture under `tests/fixtures/parsers/<bank>/raw_monthly_export/` with anonymized input + expected JSON.
5. Add bank section to `config/config.toml`.
6. Run `uv run pytest` and `uv run mypy src/` to confirm green.

## Adding a Runtime Dependency

1. `uv add <package>`.
2. `uv lock`.
3. Stage both `pyproject.toml` and `uv.lock`.

## Incident: Pipeline Fails on a Specific Statement

1. Check `data/failed/<filename>.error.txt` for the traceback.
2. If header row detection failed, the bank may have changed format. Update `find_header_row` in the relevant parser.
3. If a column header changed, update the `COLUMN_MAPPINGS` in the parser.
4. Add a regression fixture before fixing.

## Incident: Dashboard Shows Stale Data

The dashboard reads from `data/output/goodbudget_export.csv` on server startup. Restart the dashboard after re-running `fipro process` to pick up new data.

## Incident: Google Sheets Export Fails

Known issue: `src/exporters/sheets.py` has pre-existing API-shape bugs tracked as SHEETS-001 (see PR #8 code review). Fix before using in production.

## Release Procedure

Fipro uses [Changesets](.changeset/README.md) + a tag-driven release script.

### During development

For any user-visible change, drop a markdown file into `.changeset/`:

```bash
cat > .changeset/fix-parser-header.md <<'EOF'
---
"fipro": patch
---

Fix HDFC parser missing header row when preamble has blank cells.
EOF
```

Bump types: `patch` (bug/chore), `minor` (feature), `major` (breaking).

### When releasing

```bash
./scripts/release.sh patch   # or minor / major
git push origin HEAD && git push origin <tag>
```

The script:
1. Verifies clean working tree and all quality gates pass.
2. Bumps version in `pyproject.toml`.
3. Consolidates `.changeset/*.md` into `CHANGELOG.md` under a new version heading.
4. Commits `chore: release vX.Y.Z` and creates a signed tag.

### Release Checklist (Pre-1.0)

- [ ] All 4 quality gates green: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy src/`, `uv run pytest`.
- [ ] Coverage does not regress below the `fail_under` threshold in `pyproject.toml`.
- [ ] PRD table in `fipro-docs/PRD.md` section 12.3 is updated with any new plan docs.
- [ ] `AGENTS.md` commands still work end-to-end.
- [ ] `.changeset/` contains at least one entry for this release (otherwise release is a no-op).
- [ ] `CHANGELOG.md` Unreleased section has been reviewed for accuracy.
