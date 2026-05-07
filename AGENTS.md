# AGENTS.md - Development Guidelines for Fipro

## Project Overview

**Fipro** is a personal finance tool that automates extraction, consolidation, and tracking of bank transactions from Excel statements. The MVP is a Python CLI tool that processes Excel bank statements (HDFC, SBI, Axis) and exports consolidated, deduplicated CSV files compatible with Goodbudget.

### Key Value Proposition
- Eliminate manual data entry from bank statements
- Unified view of transactions from 3 banks
- Inter-bank transfer detection and reconciliation
- CSV export for Goodbudget integration

### Constraints (MVP)
- Single user, local-first (all data stays on machine)
- Manual download of statements from bank portals
- Python-only architecture
- No database, web UI, or auto-categorization

## Build/Test Commands

### Environment Setup
```bash
./scripts/setup.sh          # one-shot bootstrap (installs uv, syncs deps, hooks, runs gates)
```

Or manually:

```bash
uv sync --all-groups        # installs runtime + dev tools (ruff, mypy, pytest, pre-commit, vulture)
uv run pre-commit install   # one-time: installs the commit hooks
```

### Run Pipeline
```bash
uv run fipro process        # full pipeline
uv run fipro status         # list pending input files
uv run fipro dashboard      # local HTML dashboard on :8080
uv run fipro sheets --creds config/google_credentials.json
```

### Testing
```bash
uv run pytest               # runs suite + coverage gate (see pyproject.toml)
```

Coverage gate is currently a regression baseline (see `[tool.coverage.report]`). PRD section 14.1 targets 80%; raise the `fail_under` in pyproject.toml as tests are added, never lower it.

### Code Quality
```bash
uv run ruff check src/ tests/       # lint
uv run ruff format src/ tests/      # format (black-compatible)
uv run mypy src/                    # type check
uv run vulture                      # dead code detection (advisory, not gated)
gitleaks detect --config .gitleaks.toml   # secret scan (if gitleaks installed)
```

Ruff, ruff-format, and mypy must pass before commit. Pre-commit runs ruff automatically.
Vulture and gitleaks are advisory: run before merging but do not block commits.

## Technology Stack (MVP)

- **Python 3.14+**
- **Excel Parsing**: `pandas`, `xlrd` (xls), `openpyxl` (xlsx)
- **CLI**: Standard library or `click`
- **Config**: TOML (`config/config.toml`)
- **Logging**: Python `logging` with rotating file handler

## Core Data Model

```python
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional
from enum import Enum

class TransactionType(Enum):
    DEBIT = "debit"
    CREDIT = "credit"

class TransactionStatus(Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    TRANSFER = "internal_transfer"
    EXCLUDED = "excluded"

@dataclass(slots=True)
class Transaction:
    transaction_date: date
    description: str
    amount: Decimal
    transaction_type: TransactionType
    source_bank: str
    source_file: str

    id: Optional[int] = None
    hash: str = field(init=False)
    balance: Optional[Decimal] = None
    category: Optional[str] = None
    envelope: Optional[str] = None
    status: TransactionStatus = TransactionStatus.PENDING
    notes: Optional[str] = None
    raw_data: Optional[dict] = None

    def __post_init__(self):
        import hashlib
        unique_str = f"{self.transaction_date}{self.amount}{self.description}"
        if self.balance:
            unique_str += str(self.balance)
        self.hash = hashlib.sha256(unique_str.encode()).hexdigest()[:16]

    @property
    def signed_amount(self) -> Decimal:
        if self.transaction_type == TransactionType.DEBIT:
            return -abs(self.amount)
        return abs(self.amount)
```

## Project Structure

```
fipro/
├── config/
│   └── config.toml           # Bank patterns, paths, settings
├── data/
│   ├── input/                # Drop bank statements here
│   ├── processing/           # Temporary during processing
│   ├── processed/            # Successfully processed files
│   ├── failed/               # Failed files
│   └── output/               # Generated CSV exports
├── logs/
├── src/
│   ├── __init__.py
│   ├── main.py               # CLI entry point
│   ├── models.py             # Transaction, ProcessingResult dataclasses
│   ├── orchestrator.py       # File discovery and routing
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py           # BankParser ABC
│   │   ├── hdfc.py
│   │   ├── sbi.py
│   │   └── axis.py
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── cleaner.py        # Date/amount standardization
│   │   ├── deduplicator.py   # Hash-based deduplication
│   │   └── transfer_detector.py
│   └── export/
│       ├── __init__.py
│       └── goodbudget.py     # CSV exporter
└── tests/
    ├── test_parsers/
    ├── test_processing/
    └── fixtures/             # Anonymized sample statements
```

## Processing Pipeline

```
Stage 1: INGESTION
├── Scan data/input/ for *.xls, *.xlsx
├── Identify bank from filename pattern
└── Validate file is readable

Stage 2: EXTRACTION
├── Route file to BankParser (HDFC, SBI, Axis)
├── Find header row (banks have preamble)
└── Extract raw transactions

Stage 3: TRANSFORMATION
├── Map bank columns to Transaction schema
├── Parse dates (handle bank-specific formats)
├── Parse amounts (commas, currency symbols)
├── Generate hash for deduplication
└── Create Transaction objects

Stage 4: CONSOLIDATION
├── Merge transactions from all banks
├── Sort by date
├── Deduplicate using hash
├── Detect internal transfers (same date, amount, opposite types)
└── Flag transfers as "internal_transfer"

Stage 5: EXPORT
├── Format for Goodbudget CSV
├── Write to data/output/
└── Move processed files to data/processed/
```

## Bank Parser Specifications

### Parser Interface
```python
from abc import ABC, abstractmethod
import pandas as pd

class BankParser(ABC):
    @property
    @abstractmethod
    def bank_name(self) -> str:
        pass

    @abstractmethod
    def can_parse(self, filename: str, df: pd.DataFrame) -> bool:
        pass

    @abstractmethod
    def find_header_row(self, df: pd.DataFrame) -> int:
        pass

    @abstractmethod
    def extract_transactions(self, df: pd.DataFrame, source_file: str) -> list:
        pass
```

### Bank-Specific Details

| Bank | File Pattern | Header Row | Date Format | Amount Columns |
|------|-------------|------------|-------------|----------------|
| HDFC | `*hdfc*.xls` | Row 15-20 | DD/MM/YY or DD-MM-YYYY | `Withdrawal Amt.`, `Deposit Amt.` |
| SBI | `*sbi*.xls` | Scan first 20 rows | DD MMM YYYY | `Debit`, `Credit` |
| Axis | `*axis*.xls` | Row 10-15 | DD-MM-YYYY | `Debit`, `Credit` |

### Column Mapping
```python
COLUMN_MAPPINGS = {
    "transaction_date": ["Date", "Tran Date", "Txn Date", "Value Date"],
    "description": ["Narration", "Description", "Particulars"],
    "debit": ["Withdrawal", "Withdrawal Amt.", "Debit"],
    "credit": ["Deposit", "Deposit Amt.", "Credit"],
    "balance": ["Balance", "Closing Balance"],
    "reference": ["Chq./Ref.No.", "Ref No.", "Cheque No."],
}
```

## Goodbudget Export Format

```csv
Date,Envelope,Account,Name,Notes,Amount,Status
2025-11-15,Unallocated,HDFC,Swiggy Order,,-450.00,cleared
2025-11-16,Unallocated,AXIS,Salary Credit,,150000.00,cleared
```

| Column | Description |
|--------|-------------|
| Date | YYYY-MM-DD (ISO 8601) |
| Envelope | "Unallocated" for MVP |
| Account | Bank name |
| Name | Transaction description (max 50 chars) |
| Amount | Signed decimal (negative for debits) |
| Status | "cleared" |

## Code Style Guidelines

### Imports Order
```python
# Standard library
import os
from datetime import date
from decimal import Decimal
from typing import Optional

# Third-party
import pandas as pd

# Local
from src.models import Transaction
```

### Naming Conventions
- Classes: `PascalCase` (e.g., `Transaction`, `HDFCParser`)
- Functions/variables: `snake_case` (e.g., `extract_transactions`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_FILE_SIZE`)
- Private: prefix with `_`

### Data Structures
- Use `dataclasses` with `slots=True` for efficiency
- Use `Decimal` for money (never float)
- Use `Enum` for fixed choices

## Configuration

```toml
# config/config.toml

[fipro]
version = "1.0.0"
log_level = "INFO"

[paths]
input = "data/input"
output = "data/output"
processed = "data/processed"
failed = "data/failed"

[processing]
supported_extensions = ["xls", "xlsx"]
skip_internal_transfers = false

[banks.hdfc]
name = "HDFC"
patterns = ["*hdfc*", "*HDFC*"]
date_format = "%d/%m/%y"

[banks.sbi]
name = "SBI"
patterns = ["*sbi*", "*SBI*"]
date_format = "%d %b %Y"

[banks.axis]
name = "AXIS"
patterns = ["*axis*", "*Axis*"]
date_format = "%d-%m-%Y"

[export.goodbudget]
default_envelope = "Unallocated"
default_status = "cleared"
max_description_length = 50
```

## Error Handling

### Error Classification
- **Critical**: File system errors, config missing → Exit with error
- **Processing**: Parse failures, invalid data → Log, move to `data/failed/`
- **Warnings**: Unexpected formats, missing optional fields → Log, continue

### Logging
```python
LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"}
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/fipro.log",
            "maxBytes": 5242880,
            "backupCount": 3,
            "formatter": "standard"
        }
    },
    "loggers": {
        "fipro": {"handlers": ["console", "file"], "level": "DEBUG"}
    }
}
```

## Testing Strategy

### Test Categories
| Category | Coverage Target |
|----------|-----------------|
| Unit tests | 80% |
| Parser tests | 100% of known formats |
| Integration tests | Happy path + error cases |

### Test Data
- Use anonymized sample statements in `tests/fixtures/`
- Real statements should be `.gitignore`d

### Sample Tests
```python
def test_hdfc_finds_correct_header_row():
    """HDFC statements have ~15 rows of preamble before data"""

def test_hdfc_parses_withdrawal_correctly():
    """Withdrawal column should map to debit transaction"""

def test_detects_same_day_transfer():
    """Rs 10000 from HDFC to SBI on same day = internal transfer"""
```

## Quality Targets

| Metric | Target |
|--------|--------|
| Accuracy | 99%+ transaction extraction |
| Processing time | < 5 seconds for monthly statements |
| Reliability | Graceful handling of malformed data |

## Development Phases

### Phase 1: MVP (Current)
- [x] Basic PDF/Excel text extraction scripts
- [x] SBI and HDFC statement parsers (partial)
- [ ] Complete all 3 bank parsers (HDFC, SBI, Axis)
- [ ] Implement unified Transaction model
- [ ] Robust file orchestrator with lifecycle management
- [ ] Hash-based deduplication
- [ ] Internal transfer detection
- [ ] Goodbudget CSV export
- [ ] CLI interface
- [ ] Configuration via TOML

### Future Versions (Out of Scope)
- v1.1: PDF parsing (credit card statements)
- v1.2: SQLite database, auto-categorization
- v2.0: Web UI, envelope budgeting
- v3.0: Multi-user, cloud sync

---

**Reference**: See `docs/PRD.md` for full product requirements and future roadmap.
