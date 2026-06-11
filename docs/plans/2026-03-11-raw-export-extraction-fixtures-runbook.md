# Raw Export Fixture Runbook

## Purpose

Provide a repeatable process for adding next-month raw export fixtures without
breaking extraction regression coverage.

## Monthly Update Steps

1. Collect one export per bank (HDFC, SBI, Axis) for the target month.
2. Sanitize all personal identifiers while preserving parser-relevant shape:
   - keep header row depth, column labels, and blank-cell patterns,
   - keep date and numeric formats needed by parsers.
3. Replace fixture files:
   - `tests/fixtures/parsers/<bank>/raw_monthly_export/input.<ext>`
   - `tests/fixtures/extraction/raw_monthly_exports_2025_08_27/input/<bank>.<ext>`
4. Regenerate expected outputs by running extraction locally and copying only the
   assertion-surface fields:
   - `transaction_date`
   - `description`
   - `amount`
   - `transaction_type`
   - `source_bank`
   - `source_file`
   - `balance`
5. Update each `meta.json`:
   - increment `fixture_version`,
   - keep `anonymization_review.completed = true`,
   - update `title` and `purpose` if month or fixture shape changed.
6. Run regression tests:
   - `python -m pytest tests/test_extraction/test_raw_export_fixtures.py -v`

## Review Checklist

- No real account numbers, UPI IDs, phone numbers, or personal names remain.
- Parser fixture tests pass for all 3 banks.
- Combined extraction fixture test passes.
- Expected outputs contain only assertion-surface fields.
