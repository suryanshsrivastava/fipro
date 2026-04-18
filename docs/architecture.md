# Fipro Architecture

## 1. System Summary

Fipro is a local-first Python CLI pipeline for statement ingestion, parsing, transformation, consolidation, and export.

```
data/input/*.xls|*.xlsx
  -> src/core/ingestion.py
  -> src/core/orchestrator.py
      -> src/parsers/{hdfc,sbi,axis}.py
      -> src/core/transformer.py
      -> src/core/deduplicator.py
      -> src/core/transfer_detector.py
      -> src/exporters/goodbudget.py
      -> src/exporters/report.py
  -> data/output/{goodbudget_export.csv,processing_report.json}
```

## 2. Components

### CLI (`src/main.py`)
- Defines command surface (`process`, `status`, `dashboard`, `sheets`).
- Loads config and orchestrates top-level flows.

### Configuration (`src/config.py`, `config/config.toml`)
- Resolves filesystem paths and parser settings.
- Keeps runtime knobs externalized from code.

### Core Pipeline (`src/core/`)
- `ingestion.py`: input discovery and file handling.
- `orchestrator.py`: parser selection and end-to-end flow.
- `transformer.py`: mapping raw rows to domain model.
- `deduplicator.py`: hash-based duplicate elimination.
- `transfer_detector.py`: likely internal transfer classification.

### Parsers (`src/parsers/`)
- Bank-specific parsing logic behind a shared parser interface.
- Handles differing headers/date/amount conventions by bank.

### Models (`src/models/`)
- Dataclasses/enums representing transactions and processing results.
- `Decimal` for money values.

### Exporters (`src/exporters/`)
- `goodbudget.py`: strict export format for import workflows.
- `report.py`: machine-readable processing summary.
- `sheets.py`: optional Google Sheets publishing path.

### UI (`src/ui/dashboard.py`)
- Local dashboard over exported data for quick visual inspection.

## 3. Data Lifecycle

1. Input files are discovered in `data/input/`.
2. Each file is parsed and normalized into canonical transaction objects.
3. Consolidation merges all records, deduplicates, and flags transfers.
4. Outputs are written to `data/output/`.
5. Processed/failed file lifecycle is maintained under `data/processed/` and `data/failed/`.

## 4. Reliability Controls

- Quality gates enforced locally and in CI: Ruff, MyPy, pytest.
- Pre-commit guards formatting and common file hygiene checks.
- Secret scanning and static analysis run via GitHub workflows.
- Operational guidance lives in `RUNBOOK.md`.

## 5. Security & Privacy Posture

- Local-first by default; no mandatory external data transfer.
- Credentials and `.env` are gitignored.
- Fixture anonymization is required for all committed statement artifacts.

## 6. Canonical References

- Product requirements: `docs/PRD.md`
- Contributor workflow: `CONTRIBUTING.md`
- Agent/human conventions: `AGENTS.md`
- Operations: `RUNBOOK.md`
