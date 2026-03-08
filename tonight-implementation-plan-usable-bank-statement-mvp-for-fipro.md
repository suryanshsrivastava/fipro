# Tonight Implementation Plan: Usable Bank-Statement MVP for Fipro

## Summary
Build a working local CLI that processes HDFC, SBI, and Axis Excel statements from `data/input/`, consolidates them into one Goodbudget CSV, flags likely internal transfers, adds lightweight note tagging for configured external account payments (credit-card placeholder only), and emits a JSON processing report.

This plan explicitly does **not** implement any PDF or credit-card statement parsing tonight. Credit cards exist only as configured external accounts used for note tagging.

## Target Outcome
By the end of tonight, the command below must work on real files once:

```bash
python -m src.main process
```

Successful run behavior:
- reads `.xls` / `.xlsx` files from `data/input/`
- parses supported bank files
- merges and deduplicates transactions
- flags internal transfers
- includes flagged transfers in CSV
- tags likely external-account payments in `Notes`
- writes one Goodbudget CSV and one JSON report to `data/output/`
- moves successfully processed source files to `data/processed/`

Failure behavior chosen:
- if **any** input file fails to parse, treat the run as failed
- write **no** CSV/report
- move failed file(s) to `data/failed/` and write sidecar error text file(s)
- leave successfully parsed source files in `data/input/` unchanged

## Scope
### In scope
- Excel bank statements only: HDFC, SBI, Axis
- `process` CLI command
- minimal `status` CLI command
- config cleanup
- deduplication
- transfer detection
- Goodbudget export
- JSON run report
- external-account note tagging via config

### Out of scope
- PDF parsing
- credit-card statement ingestion
- database
- categorization
- envelope allocation logic
- UI
- persistent dedup across runs

## Public Interfaces / Behavior
### CLI
Implement in [`src/main.py`](/home/suryanshsrivastava/Work/Projects/fipro/src/main.py):
- `python -m src.main process [--config PATH]`
- `python -m src.main status [--config PATH]`

`process` exit codes:
- `0` on full success
- `1` on any parse/export/config failure

`status` output:
- input directory path
- count of pending files
- file list grouped by detected bank hint

### Config schema
Normalize [`config/config.toml`](/home/suryanshsrivastava/Work/Projects/fipro/config/config.toml) and [`src/config.py`](/home/suryanshsrivastava/Work/Projects/fipro/src/config.py) to this schema:

```toml
[fipro]
version = "0.1.0"
log_level = "INFO"

[paths]
input = "data/input"
output = "data/output"
processed = "data/processed"
failed = "data/failed"
log_file = "logs/fipro.log"

[processing]
supported_extensions = ["xls", "xlsx"]
include_internal_transfers = true
fail_on_file_error = true

[banks.hdfc]
patterns = ["*hdfc*", "*HDFC*"]

[banks.sbi]
patterns = ["*sbi*", "*SBI*"]

[banks.axis]
patterns = ["*axis*", "*Axis*"]

[external_accounts]
names = ["CREDIT_CARD"]
payment_keywords = ["CREDIT CARD", "CC PAYMENT", "CARD PAYMENT", "CRED"]
```

Defaults:
- config path default must resolve to repo-local `config/config.toml`
- only `.xls` and `.xlsx` are processed tonight

### Output files
Write to `data/output/`:
- `goodbudget_YYYYMMDD_HHMMSS.csv`
- `processing_report_YYYYMMDD_HHMMSS.json`

### CSV behavior
Goodbudget columns remain:
`Date,Envelope,Account,Name,Notes,Amount,Status`

Notes field rules:
- internal transfer: append `Internal transfer detected`
- external account payment match: append `External account payment: CREDIT_CARD`
- if both match, join with ` | `

Status column stays `cleared` for all exported rows tonight.

## File-by-File Implementation
### 1. Config and startup
[`src/config.py`](/home/suryanshsrivastava/Work/Projects/fipro/src/config.py)
- change required sections from broken `model/data/logging` validation to the schema above
- validate presence of `paths.input/output/processed/failed`, `processing.supported_extensions`
- resolve default config relative to repo root, not `../config/config.toml`

[`src/main.py`](/home/suryanshsrivastava/Work/Projects/fipro/src/main.py)
- build argparse CLI with `process` and `status`
- load config
- initialize logging via `setup_logging`
- dispatch to orchestrator / discovery helpers
- print concise success/failure summary to stdout
- return exit code via `sys.exit(...)`

### 2. Ingestion and loading
[`src/core/ingestion.py`](/home/suryanshsrivastava/Work/Projects/fipro/src/core/ingestion.py)
- keep current discovery logic
- rely on `processing.supported_extensions = ["xls", "xlsx"]`
- no PDF/csv handling

Loader strategy inside orchestrator:
- HDFC / Axis: `pd.read_excel(..., header=None)` with engine fallback `xlrd`, then `openpyxl`
- SBI: use `SBIParser.load_sbi_file(filepath)` first; if it returns `None`, treat as parse failure
- parser selection should be hint-first from filename, then `can_parse()` confirmation

### 3. Orchestration
[`src/core/orchestrator.py`](/home/suryanshsrivastava/Work/Projects/fipro/src/core/orchestrator.py)
- instantiate `HDFCParser`, `SBIParser`, `AxisParser`
- discover files
- for each file:
  - load dataframe
  - route parser
  - call `extract_transactions`
  - collect `ProcessingResult` per file
- after all files parse successfully:
  - merge all transactions
  - deduplicate
  - detect transfers
  - export CSV
  - generate report
  - move all source files to processed
- on any file failure:
  - collect errors
  - move failed file(s) to failed
  - write sidecar `<filename>.error.txt`
  - do not export anything
  - do not move successful files
  - raise/return failure for CLI exit code

Implement helper behavior explicitly:
- `route_file_to_parser`: first try parser matching discovered bank hint, then fallback over all parsers using `can_parse()`
- `move_file_to_processed`: move to configured processed dir, preserving basename
- `move_file_to_failed`: move to configured failed dir, preserving basename, and write sidecar error log

### 4. Deduplication
[`src/core/deduplicator.py`](/home/suryanshsrivastava/Work/Projects/fipro/src/core/deduplicator.py)
- implement in-memory dedup only
- keep first occurrence, drop later duplicates
- `get_seen_hashes_from_file` returns empty set
- `save_seen_hashes_to_file` remains no-op
- dedup happens after all files are merged, not per-file

### 5. Transfer detection
[`src/core/transfer_detector.py`](/home/suryanshsrivastava/Work/Projects/fipro/src/core/transfer_detector.py)
- `is_transfer_pair(txn1, txn2)` returns true only when:
  - same `transaction_date`
  - same absolute `amount`
  - opposite `transaction_type`
  - different `source_bank`
- `detect_transfers`:
  - sort by `(date, amount, source_bank)`
  - greedily pair unmatched transactions
  - mark both as `TransactionStatus.TRANSFER`
  - do not remove them from list
- do not attempt fuzzy matching by description tonight

### 6. External-account note tagging
Implement in [`src/exporters/goodbudget.py`](/home/suryanshsrivastava/Work/Projects/fipro/src/exporters/goodbudget.py), not as a new status enum.
- normalize description to uppercase
- if any configured keyword substring matches and transaction is a debit:
  - add note `External account payment: CREDIT_CARD`
- use configured `external_accounts.names[0]` as the label tonight
- keep this logic config-driven, not hardcoded beyond default config values

### 7. Export
[`src/exporters/goodbudget.py`](/home/suryanshsrivastava/Work/Projects/fipro/src/exporters/goodbudget.py)
- sort by `transaction_date`, then `source_bank`, then `description`
- always include transfers in CSV because that was selected
- use `Transaction.to_goodbudget_row()` as base row
- override `Notes` with composed notes described above
- write UTF-8 CSV with header row

### 8. Report
[`src/exporters/report.py`](/home/suryanshsrivastava/Work/Projects/fipro/src/exporters/report.py)
- include:
  - `run_id`
  - `summary.total_files`
  - `summary.total_transactions`
  - `summary.exported_transactions`
  - `summary.duplicates_skipped`
  - `summary.transfers_detected`
  - `summary.failed_files`
  - `by_bank`
  - `date_range`
  - `files`
- `files` entries should include source file, bank, total, duplicates skipped, warnings, errors

## Deliberate Non-Changes
- Do **not** force usage of [`src/core/transformer.py`](/home/suryanshsrivastava/Work/Projects/fipro/src/core/transformer.py) tonight; current parsers already emit `Transaction` objects directly.
- Do **not** introduce persistent dedup state.
- Do **not** add new dependencies unless a parser absolutely fails on local files with current stack.

## Testing Plan
### Unit tests to add
- config loader validates new schema and resolves default path
- deduplicator removes repeated hashes and counts skipped rows
- transfer detector marks same-date/same-amount/opposite-type/different-bank pairs
- transfer detector does not match same-bank mirrored amounts
- exporter includes transfers and writes composed notes correctly
- external payment tagging only applies to debits with configured keyword
- orchestrator fail-whole-run produces no export on a single-file parse failure

### Manual acceptance run tonight
1. Place one real HDFC, one SBI, one Axis statement in `data/input/`
2. Run `python -m src.main status`
3. Run `python -m src.main process`
4. Confirm one CSV and one JSON report appear in `data/output/`
5. Confirm parsed files moved to `data/processed/`
6. Inspect CSV:
   - rows exist from all intended banks
   - transfer rows are still present
   - transfer notes appear
   - at least one known card-payment row gets external-payment note if keyword matches
7. Spot-check totals and a few dates/descriptions against source statements

## Acceptance Criteria
- CLI runs from repo root with no code edits outside planned files
- at least one real end-to-end import succeeds tonight
- no PDF or credit-card parser exists in the path
- failures are explicit and non-partial
- outputs are stable enough to import into Goodbudget once tonight

## Assumptions and Chosen Defaults
- credit cards are modeled as external accounts only; no statement ingestion
- transfer export mode: **include flagged transfers**
- failure mode: **fail whole run**
- external account scope: **config plus note tagging**
- only Excel statements are supported tonight
- parser identification is filename-hinted first, parser-confirmed second
- successful-file moves happen only after successful export
