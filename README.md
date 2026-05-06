# fipro

Local-first personal finance pipeline for consolidating Indian bank statement Excel files into a Goodbudget-compatible CSV.

## What it does (MVP)

- Reads `.xls` / `.xlsx` statements from:
  - HDFC
  - SBI
  - Axis
- Parses and normalizes transactions
- Deduplicates merged transactions
- Detects likely inter-bank internal transfers
- Exports:
  - Goodbudget CSV
  - JSON processing report
- Moves files after run:
  - successful files -> `data/processed/`
  - failed files -> `data/failed/` (+ sidecar `*.error.txt`)

## Project layout

- `src/main.py` - CLI entrypoint (`process`, `status`)
- `src/core/` - discovery/orchestration/dedup/transfer detection
- `src/parsers/` - bank-specific parsers
- `src/exporters/` - Goodbudget CSV + JSON report exporters
- `config/config.toml` - runtime config
- `tests/` - parser/core/model/exporter/pipeline tests

## Requirements

- Python >= 3.14 (managed automatically by `uv`)
- `uv` installed

## Quick start

```bash
# from repo root
uv sync
```

Prepare directories and place statements:

```bash
mkdir -p data/input data/output data/processed data/failed logs
# copy bank statements into data/input/
```

See pending files:

```bash
uv run python -m src.main status
```

Process files:

```bash
uv run python -m src.main process
```

## CLI

```bash
uv run python -m src.main process [--config PATH]
uv run python -m src.main status [--config PATH]
```

Exit codes:

- `0` success
- `1` failure

## Config

Default config: `config/config.toml`

Important sections:

- `[paths]` input/output/processed/failed/log file locations
- `[processing]` supported file extensions and failure mode
- `[banks.*]` filename patterns
- `[external_accounts]` keyword-based payment note tagging

## Outputs

On successful processing run:

- `data/output/goodbudget_YYYYMMDD_HHMMSS.csv`
- `data/output/processing_report_YYYYMMDD_HHMMSS.json`

Goodbudget CSV columns:

`Date,Envelope,Account,Name,Notes,Amount,Status`

## Testing

```bash
uv run pytest -q
```

Current baseline in this branch: all tests passing.

## Notes

- MVP scope is Excel statements only (`.xls`, `.xlsx`)
- No PDF parsing in current implementation
- Local-first: no cloud sync/database required for core pipeline
