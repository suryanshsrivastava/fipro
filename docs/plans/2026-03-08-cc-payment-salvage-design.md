# CC Payment Salvage Design

## Summary

Salvage the durable part of the old `feature/cc-payments-processing` branch by
making credit-card and other external-account payments a first-class
classification in the current pipeline.

## Context

- The old branch snapshot does not contain a merge-ready CC-payments feature.
- Config already defined `external_accounts` keywords in tests, but `main` did
  not classify transactions until this salvage pass.
- Project notes list "Annotate PDF for credit card statements" as a future
  direction, so this pass improves classification rather than add PDF ingestion.

## Decision

- Keep the modern parser/orchestrator architecture from `main`.
- Add a dedicated detector for external-account payments in `src/core/`.
- Store the matched external account on each transaction instead of overloading
  transaction status.
- Keep the exporter responsible only for formatting notes from transaction data.

## Data Flow

1. Parse source files into transactions.
2. Deduplicate transactions.
3. Detect internal transfers.
4. Detect external-account payments from configured keywords.
5. Export classified transactions to Goodbudget and the processing report.

## Testing

- Unit tests for the detector (`tests/test_core/test_external_account_detector.py`).
- Exporter note formatting tests (`tests/test_exporters/test_goodbudget.py`).
- Pipeline fixture `tests/fixtures/pipeline/mixed_basic/` for end-to-end CC tagging.

## Deferred Work

- Salvaging text-grouping heuristics from the old `extract_transactions.py` for
  messy statement formats.
- PDF annotation or ingestion for credit-card statements.
