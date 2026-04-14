## Objective

Create a safe, repeatable fixture and regression-test baseline for raw bank
statement extraction so parser changes can be made quickly without breaking
bank-specific parsing behavior.

## Scope

- Build fixture sets for parser-level and combined extraction-level coverage.
- Add deterministic expected outputs for extraction-layer fields.
- Fix parser compatibility gaps required to read raw exports consistently.
- Add regression tests that run only from fixture files.

Non-goals:

- Deduplication logic
- Transfer detection logic
- Goodbudget export transformations
- Parser redesign beyond these compatibility gaps:
  - HDFC header detection preamble depth
  - `NaN` amount-cell normalization

## Data Safety Requirements (mandatory)

Before any file is committed to `tests/fixtures/`, sanitize:

- Account numbers, card numbers, UPI IDs, phone numbers, email addresses.
- Counterparty names that can identify real individuals.
- Narration text containing personally identifiable information.

Rules:

- Preserve parsing-critical shape (column headers, date formats, debit/credit
layouts, blank cells, row offsets).
- Preserve numeric behavior needed for parsing logic tests.
- Add a `meta.json` note per fixture confirming anonymization review completed.

## Approval Gate

Before starting Phase 1:

- Intern posts a short implementation note with fixture sources, anonymization
method, and planned test files.
- Maintainer gives explicit go-ahead in PR comment or task thread.

## Fixture Layout

- `tests/fixtures/parsers/<bank>/raw_monthly_export/input.<ext>`
- `tests/fixtures/parsers/<bank>/raw_monthly_export/expected.json`
- `tests/fixtures/parsers/<bank>/raw_monthly_export/meta.json`
- `tests/fixtures/extraction/raw_monthly_exports_aug_2025/input/<bank>.<ext>`
- `tests/fixtures/extraction/raw_monthly_exports_aug_2025/expected.json`
- `tests/fixtures/extraction/raw_monthly_exports_aug_2025/meta.json`

## Assertion Surface

Validate extraction-layer fields only:

- `transaction_date`
- `description`
- `amount`
- `transaction_type`
- `source_bank`
- `source_file`
- `balance`

Exclude `raw_data` from regression assertions to keep failures focused and avoid
brittle snapshots.

## Execution Plan (Intern Handoff)

### Phase 1: Fixture sourcing and sanitization

Owner: Intern  
Reviewer: Maintainer

Tasks:

1. Copy representative raw exports (HDFC, SBI, Axis) into a staging directory.
2. Sanitize sensitive values while preserving parser-relevant structure.
3. Create parser-level fixture directories and add `meta.json` notes.

Exit criteria:

- One sanitized `input.<ext>` per bank exists in fixture tree.
- Every fixture has `meta.json` with anonymization confirmation.
- Reviewer sign-off confirms no identifiable data remains.

### Phase 2: Expected-output authoring

Owner: Intern  
Reviewer: Maintainer

Tasks:

1. Define canonical extraction outputs in `expected.json` per bank.
2. Define combined extraction `expected.json` for multi-bank batch fixture.
3. Ensure field set matches the assertion surface exactly.

Exit criteria:

- Parser-level expected outputs exist for all 3 banks.
- Combined expected output exists and is deterministic.
- Field schema is consistent across all expected files.

### Phase 3: Parser compatibility fixes

Owner: Intern  
Reviewer: Maintainer

Tasks:

1. Expand HDFC header scan range to cover actual export preamble depth.
2. Normalize parser cell handling so `NaN` is treated as empty across parsers.
3. Re-run extraction locally against fixture inputs to validate behavior.

Exit criteria:

- HDFC fixture parses without header-detection failure.
- Credit rows with blank counterpart amount cells are not skipped due to
`"nan"` handling.
- No regression in SBI/Axis parser fixture extraction.

### Phase 4: Regression test implementation

Owner: Intern  
Reviewer: Maintainer

Tasks:

1. Add per-bank extraction regression tests.
2. Add one combined extraction regression test.
3. Ensure tests use fixture paths only (never raw source directory).

Exit criteria:

- Per-bank and combined tests pass locally.
- Tests fail when expected output is intentionally mismatched (sanity check).
- Test names and failure messages identify fixture and bank clearly.

### Phase 5: Handoff closeout

Owner: Intern  
Reviewer: Maintainer

Tasks:

1. Document what changed and known limitations.
2. Provide a short runbook for adding next-month fixture variants.
3. Submit PR with checklist completion.

Exit criteria:

- PR includes fixture safety checklist, test evidence, and runbook note.
- Reviewer can rerun tests from clean checkout and reproduce results.

## Deliverables

- Parser fixtures for HDFC/SBI/Axis with `input.<ext>`, `expected.json`,
`meta.json`.
- Combined multi-bank fixture set for `raw_monthly_exports_aug_2025`.
- Per-bank and combined extraction regression tests under `tests/`.
- Intern runbook note for adding next-month fixtures.

## Verification Command

- `python -m pytest tests/ -k "extraction or parser or hdfc or sbi or axis" -v`

## Definition of Done

- All fixture inputs are sanitized and reviewed.
- Parser-level fixtures exist for HDFC, SBI, and Axis.
- Combined multi-bank fixture and expected output exist.
- HDFC preamble/header detection fix implemented.
- `NaN` normalization fix implemented across parser cell handling.
- Per-bank extraction regression tests pass.
- Combined extraction regression test passes.
- Runbook note for future fixture additions is included.