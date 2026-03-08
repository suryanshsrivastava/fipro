# Fixture-Based Regression Test Plan for Fipro

## Summary

Create a checked-in fixture system that provides stable, reviewable input-output
pairs for both parser-level unit tests and pipeline-level functional tests.

The fixtures serve two purposes:
- regression protection for selective bank-statement parsing behavior
- an evolving corpus of representative statement formats and edge cases

## Test Layers

### Parser regression tests
- one sample statement file per case
- one `expected.json` with normalized transactions
- validates header detection, extraction, parsing, and bank quirks

### Pipeline functional tests
- one fixture input folder with mixed bank files
- one `expected_goodbudget.csv`
- one `expected_report.json`
- validates orchestration, deduplication, transfer tagging, note tagging, and export

## Canonical Structure

```text
tests/
  fixtures/
    parsers/
      hdfc/<case>/
      sbi/<case>/
      axis/<case>/
    pipeline/
      mixed_basic/
```

Each case directory contains:
- `input.*`
- `expected.json` or final output goldens
- `meta.json`

## Rules

- fixture inputs are checked in and edited intentionally
- expected outputs are checked in and reviewed like normal code
- tests never regenerate expected outputs
- parser goldens use JSON
- functional goldens use CSV plus JSON report
- no real financial data is committed
