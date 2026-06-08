# Fipro - Product Requirements Document

**Version:** 1.0.0
**Last Updated:** 2026-06-09
**Author:** Suryansh Srivastava
**Status:** Active Development

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals & Success Criteria](#3-goals--success-criteria)
4. [Scope](#4-scope)
5. [User Personas](#5-user-personas)
6. [Core Data Model](#6-core-data-model)
7. [System Architecture](#7-system-architecture)
8. [Processing Pipeline](#8-processing-pipeline)
9. [Bank Parser Specifications](#9-bank-parser-specifications)
10. [Output Formats](#10-output-formats)
11. [Project Structure](#11-project-structure)
12. [Implementation Roadmap](#12-implementation-roadmap)
13. [Technical Specifications](#13-technical-specifications)
14. [Testing Strategy](#14-testing-strategy)
15. [Known Constraints & Risks](#15-known-constraints--risks)
16. [Future Directions](#16-future-directions)
17. [Appendices](#17-appendices)

---

## 1. Executive Summary

**Fipro** (Financial Project) is a personal finance management tool that automates the extraction, consolidation, and tracking of bank transactions from multiple financial institutions. The MVP focuses on processing Excel bank statements from HDFC, SBI, and Axis banks, consolidating them into a unified format, and exporting to Goodbudget-compatible CSV for external budget tracking.

### Key Value Proposition

- **Eliminate manual data entry**: Auto-extract transactions from bank statements
- **Unified view**: Consolidate transactions from 3 banks into one place
- **Transfer reconciliation**: Identify and handle inter-bank transfers
- **Budget integration**: Export to Goodbudget for envelope-based budgeting

### MVP Deliverable

A Python CLI tool that processes Excel bank statements and outputs a consolidated, deduplicated CSV file compatible with Goodbudget import.

---

## 2. Problem Statement

### Current Pain Points

1. **Manual effort**: Downloading statements from 3 banks and manually entering transactions into a budgeting app is time-consuming and error-prone
2. **Format inconsistency**: Each bank has different statement formats, column names, and date formats
3. **Transfer duplication**: Money moving between own accounts appears as both debit and credit, causing double-counting
4. **No unified view**: Financial data is scattered across multiple bank portals with no single source of truth

### User Story

> As a person managing finances across multiple bank accounts, I want to automatically consolidate my bank statements into a single view so that I can track my spending and upload to my budgeting app without manual data entry.

---

## 3. Goals & Success Criteria

### MVP Goals

| Goal | Success Metric |
|------|----------------|
| Parse all 3 bank Excel formats | 100% of transactions extracted from test files |
| Consolidate into unified format | Single CSV with standardized schema |
| Detect internal transfers | Matching debits/credits between own accounts flagged |
| Deduplicate transactions | No duplicate entries from re-processing same file |
| Goodbudget compatibility | CSV imports successfully into Goodbudget |

### Quality Targets

- **Accuracy**: 99%+ transaction extraction accuracy
- **Processing time**: < 5 seconds for typical monthly statements
- **Reliability**: Graceful handling of malformed/unexpected data

---

## 4. Scope

### In Scope (MVP)

- ✅ Excel file parsing (`.xls`, `.xlsx`) for HDFC, SBI, Axis
- ✅ Transaction extraction with date, description, amount, type
- ✅ Data cleaning and standardization
- ✅ Deduplication using hash-based approach
- ✅ Internal transfer detection between own accounts
- ✅ CSV export in Goodbudget-compatible format
- ✅ CLI interface for running the pipeline
- ✅ Configuration via TOML file
- ✅ Basic logging and error reporting
- ✅ Local HTML dashboard for reviewing exported transactions (`fipro dashboard`)
- ✅ Optional Google Sheets export for sharing or mobile viewing (`fipro sheets`)

### Out of Scope (MVP)

- ❌ PDF parsing (credit card statements) - **v1.1**
- ❌ Full web app (hosted React + FastAPI UI) - **v2.0**
- ❌ Database storage (SQLite/PostgreSQL) - **v1.2**
- ❌ Auto-categorization (rule-based or ML) - **v1.2**
- ❌ Envelope budgeting features - **v2.0**
- ❌ Multi-user support - **v3.0**
- ❌ Bank API integrations - **Future**
- ❌ Mobile app - **Future**

### Constraints

- **Single user**: Personal use only
- **Local first**: All data stays on local machine
- **Manual trigger**: User manually downloads statements and runs script
- **Python only**: No multi-language architecture for MVP

---

## 5. User Personas

### Primary Persona: Personal Finance Tracker

**Name:** Suryansh (You)
**Context:** Managing 3 bank accounts with different purposes

| Bank | Purpose | Statement Format |
|------|---------|------------------|
| Axis | Salary credit account | Excel (.xls) |
| HDFC | Daily granular transactions | Excel (.xls) |
| SBI | Structured/planned transactions | Excel (.xls) |

**Workflow:**
1. Monthly: Download statements from all 3 banks
2. Run fipro processing pipeline
3. Review consolidated output
4. Upload CSV to Goodbudget for budget tracking

---

## 6. Core Data Model

### 6.1 Transaction (Primary Entity)

The `Transaction` class is the core data structure. It's designed to support future envelope budgeting while remaining simple for MVP.

```python
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional
from enum import Enum
import hashlib

class TransactionType(Enum):
    DEBIT = "debit"
    CREDIT = "credit"

class TransactionStatus(Enum):
    PENDING = "pending"           # Just extracted
    VERIFIED = "verified"         # User confirmed
    TRANSFER = "internal_transfer" # Between own accounts
    EXCLUDED = "excluded"         # User marked to ignore

@dataclass(slots=True)
class Transaction:
    """
    Core transaction entity designed for:
    - MVP: CSV export to Goodbudget
    - Future: Zero-based/envelope budgeting integration
    """
    # Required fields
    transaction_date: date
    description: str
    amount: Decimal
    transaction_type: TransactionType
    source_bank: str
    source_file: str

    # Auto-generated
    id: Optional[int] = None
    hash: str = field(init=False)

    # Optional fields
    balance: Optional[Decimal] = None
    category: Optional[str] = None  # For future budgeting
    envelope: Optional[str] = None  # For future envelope budgeting
    status: TransactionStatus = TransactionStatus.PENDING
    notes: Optional[str] = None
    raw_data: Optional[dict] = None  # Original row for debugging

    # Metadata
    created_at: Optional[str] = None

    def __post_init__(self):
        """Generate unique hash for deduplication"""
        # Hash based on date + amount + description + balance (if available)
        unique_str = f"{self.transaction_date}{self.amount}{self.description}"
        if self.balance:
            unique_str += str(self.balance)
        self.hash = hashlib.sha256(unique_str.encode()).hexdigest()[:16]

    @property
    def signed_amount(self) -> Decimal:
        """Returns negative for debits, positive for credits"""
        if self.transaction_type == TransactionType.DEBIT:
            return -abs(self.amount)
        return abs(self.amount)

    def to_goodbudget_row(self) -> dict:
        """Convert to Goodbudget CSV format"""
        return {
            "Date": self.transaction_date.strftime("%Y-%m-%d"),
            "Envelope": self.envelope or "Unallocated",
            "Account": self.source_bank,
            "Name": self.description[:50],  # Goodbudget limit
            "Notes": self.notes or "",
            "Amount": str(self.signed_amount),
            "Status": "cleared"
        }
```

### 6.2 Account (Supporting Entity)

```python
@dataclass(slots=True)
class Account:
    """Represents a bank account"""
    bank: str                    # HDFC, SBI, AXIS
    account_number: str          # Last 4 digits only (security)
    nickname: str                # "Salary Account", "Daily Expenses"
    account_type: str            # savings, current
    is_active: bool = True
```

### 6.3 ProcessingResult (Pipeline Output)

```python
@dataclass
class ProcessingResult:
    """Result of processing a bank statement file"""
    source_file: str
    bank: str
    total_transactions: int
    successful: int
    failed: int
    duplicates_skipped: int
    transactions: list[Transaction]
    errors: list[str]
    warnings: list[str]
```

---

## 7. System Architecture

### 7.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FIPRO MVP                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  INPUT   │───▶│ EXTRACT  │───▶│ PROCESS  │───▶│  OUTPUT  │  │
│  │          │    │          │    │          │    │          │  │
│  │ *.xls    │    │ Bank     │    │ Clean    │    │ CSV      │  │
│  │ *.xlsx   │    │ Parsers  │    │ Dedup    │    │ (Good-   │  │
│  │          │    │ (HDFC,   │    │ Transfer │    │ budget)  │  │
│  │          │    │ SBI,Axis)│    │ Detect   │    │          │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │                │               │               │        │
│       ▼                ▼               ▼               ▼        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    CONFIG (config.toml)                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    LOGS & REPORTS                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **File Orchestrator** | Discover files, route to correct parser, manage lifecycle |
| **Bank Parsers** | Extract raw data from bank-specific Excel formats |
| **Data Cleaner** | Standardize dates, amounts, descriptions |
| **Deduplicator** | Detect and skip already-processed transactions |
| **Transfer Detector** | Identify money moving between own accounts |
| **Exporter** | Generate Goodbudget-compatible CSV |

---

## 8. Processing Pipeline

### 8.1 Pipeline Stages

```
Stage 1: INGESTION
├── Scan input directory for supported files
├── Identify bank from filename pattern
├── Validate file is readable and not empty
└── Create CrawledFile metadata [[objects]]

Stage 2: EXTRACTION
├── Route file to appropriate BankParser
├── Find header row (banks have varying preamble)
├── Extract transactions row by row
├── Handle multi-line descriptions if needed
└── Return list of raw transaction dicts

Stage 3: TRANSFORMATION
├── Map bank-specific columns to Transaction schema
├── Parse and standardize dates (DD-MM-YYYY → ISO)
├── Parse amounts (handle commas, currency symbols)
├── Determine debit/credit from amount or column
├── Generate hash for each transaction
└── Create Transaction [[objects]]

Stage 4: CONSOLIDATION
├── Merge transactions from all banks
├── Sort by date
├── Deduplicate using hash
├── Detect internal transfers
│   ├── Match: same date, same amount, opposite types
│   └── Flag both sides as "internal_transfer"
└── Generate consolidated transaction list

Stage 5: EXPORT
├── Filter out internal transfers (optional)
├── Format for Goodbudget CSV schema
├── Write to output file
└── Generate processing report
```

### 8.2 File Lifecycle

```
data/input/           # Drop bank statements here
    ├── hdfc.xls
    ├── sbi.xls
    └── axis.xls
          │
          ▼ (processing)
          │
data/processing/      # Files being processed (temporary)
          │
          ├── Success ──▶ data/processed/
          │                   └── hdfc_2025-11.xls
          │
          └── Failure ──▶ data/failed/
                              └── corrupt_file.xls

data/output/          # Generated outputs
    ├── consolidated_2025-11.csv
    └── processing_report_2025-11.json
```

---

## 9. Bank Parser Specifications

### 9.1 Parser Strategy Pattern

```python
from abc import ABC, abstractmethod

class BankParser(ABC):
    """Abstract base class for bank-specific parsers"""

    @property
    @abstractmethod
    def bank_name(self) -> str:
        """Return bank identifier (HDFC, SBI, AXIS)"""
        pass

    @abstractmethod
    def can_parse(self, filename: str, df: pd.DataFrame) -> bool:
        """Check if this parser can handle the file"""
        pass

    @abstractmethod
    def find_header_row(self, df: pd.DataFrame) -> int:
        """Find the row index where transaction data starts"""
        pass

    @abstractmethod
    def extract_transactions(self, df: pd.DataFrame, source_file: str) -> list[Transaction]:
        """Extract transactions from dataframe"""
        pass

    @abstractmethod
    def get_column_mapping(self) -> dict:
        """Map bank columns to standard schema"""
        pass
```

### 9.2 Bank-Specific Details

#### HDFC Bank

| Aspect | Details |
|--------|---------|
| File pattern | `*hdfc*.xls`, `*hdfc*.xlsx` |
| Header row | Usually row 15-20 (has bank logo/address preamble) |
| Date format | `DD/MM/YY` or `DD-MM-YYYY` |
| Amount columns | Separate `Withdrawal` and `Deposit` columns |
| Description | `Narration` column |
| Balance | `Closing Balance` column |

**Expected columns:**
```
Date, Narration, Chq./Ref.No., Value Dt, Withdrawal Amt., Deposit Amt., Closing Balance
```

#### SBI Bank

| Aspect | Details |
|--------|---------|
| File pattern | `*sbi*.xls`, `*sbi*.xlsx` |
| Header row | Variable (scan first 20 rows) |
| Date format | `DD MMM YYYY` (e.g., "15 Nov 2025") |
| Amount columns | Separate `Debit` and `Credit` columns |
| Description | `Description` or `Particulars` column |
| Balance | `Balance` column |

**Expected columns:**
```
Txn Date, Value Date, Description, Ref No./Cheque No., Debit, Credit, Balance
```

#### Axis Bank

| Aspect | Details |
|--------|---------|
| File pattern | `*axis*.xls`, `*axis*.xlsx` |
| Header row | Usually row 10-15 |
| Date format | `DD-MM-YYYY` |
| Amount columns | Single `Amount` with sign, or separate columns |
| Description | `Particulars` column |
| Balance | `Balance` column |

**Expected columns:**
```
Tran Date, Particulars, Chq No, Debit, Credit, Balance
```

### 9.3 Column Mapping Reference

```python
COLUMN_MAPPINGS = {
    # Standard name -> [possible bank column names]
    "transaction_date": ["Date", "Tran Date", "Txn Date", "Transaction Date", "Value Date"],
    "description": ["Narration", "Description", "Particulars", "Details"],
    "debit": ["Withdrawal", "Withdrawal Amt.", "Debit", "Dr"],
    "credit": ["Deposit", "Deposit Amt.", "Credit", "Cr"],
    "balance": ["Balance", "Closing Balance", "Available Balance"],
    "reference": ["Chq./Ref.No.", "Ref No.", "Cheque No.", "Reference"],
}
```

---

## 10. Output Formats

### 10.1 Goodbudget CSV Format

**Target schema for Goodbudget import:**

```csv
Date,Envelope,Account,Name,Notes,Amount,Status
2025-11-15,Food,HDFC,Swiggy Order,Dinner,-450.00,cleared
2025-11-16,Income,AXIS,Salary Credit,,150000.00,cleared
2025-11-17,Transfer,SBI,Transfer to HDFC,Internal,-10000.00,cleared
```

| Column | Description | Required |
|--------|-------------|----------|
| Date | YYYY-MM-DD format | Yes |
| Envelope | Budget category (use "Unallocated" for MVP) | Yes |
| Account | Bank name | Yes |
| Name | Transaction description (max 50 chars) | Yes |
| Notes | Additional details | No |
| Amount | Signed amount (negative for debits) | Yes |
| Status | "cleared" or "pending" | Yes |

### 10.2 Processing Report Format

```json
{
  "run_id": "2025-11-28T10:30:00",
  "summary": {
    "files_processed": 3,
    "total_transactions": 245,
    "new_transactions": 230,
    "duplicates_skipped": 15,
    "internal_transfers": 8,
    "errors": 0
  },
  "by_bank": {
    "HDFC": { "transactions": 120, "debits": 95, "credits": 25 },
    "SBI": { "transactions": 75, "debits": 50, "credits": 25 },
    "AXIS": { "transactions": 50, "debits": 20, "credits": 30 }
  },
  "date_range": {
    "earliest": "2025-10-01",
    "latest": "2025-10-31"
  },
  "files": [
    { "name": "hdfc.xls", "status": "success", "transactions": 120 },
    { "name": "sbi.xls", "status": "success", "transactions": 75 },
    { "name": "axis.xls", "status": "success", "transactions": 50 }
  ]
}
```

---

## 11. Project Structure

### 11.1 Recommended Directory Layout

```
fipro/
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── config.py                  # Configuration loader
│   │
│   ├── models/                    # Data models
│   │   ├── __init__.py
│   │   ├── transaction.py         # Transaction, TransactionType, etc.
│   │   ├── account.py             # Account model
│   │   └── result.py              # ProcessingResult
│   │
│   ├── parsers/                   # Bank-specific parsers
│   │   ├── __init__.py
│   │   ├── base.py                # BankParser ABC
│   │   ├── hdfc.py                # HDFCParser
│   │   ├── sbi.py                 # SBIParser
│   │   └── axis.py                # AxisParser
│   │
│   ├── core/                      # Core processing logic
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # Main processing controller
│   │   ├── ingestion.py           # File discovery
│   │   ├── transformer.py         # Data cleaning/standardization
│   │   ├── deduplicator.py        # Hash-based deduplication
│   │   └── transfer_detector.py   # Internal transfer detection
│   │
│   ├── exporters/                 # Output formatters
│   │   ├── __init__.py
│   │   ├── goodbudget.py          # Goodbudget CSV exporter
│   │   └── report.py              # Processing report generator
│   │
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── date_parser.py         # Date format handling
│       ├── amount_parser.py       # Amount/currency parsing
│       └── logger.py              # Logging configuration
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── test_models.py
│   ├── test_parsers/
│   │   ├── test_hdfc.py
│   │   ├── test_sbi.py
│   │   └── test_axis.py
│   ├── test_pipeline.py
│   └── fixtures/                  # Test data (anonymized)
│       ├── hdfc_sample.xls
│       ├── sbi_sample.xls
│       └── axis_sample.xls
│
├── data/                          # Data directories
│   ├── input/                     # Drop statements here
│   ├── processing/                # Temporary during processing
│   ├── processed/                 # Successfully processed
│   ├── failed/                    # Failed files
│   └── output/                    # Generated CSVs
│
├── config/
│   └── config.toml                # Main configuration
│
├── logs/                          # Log files
│   └── fipro.log
│
├── fipro-docs/                    # Documentation (existing)
│   ├── PRD.md                     # This document
│   └── ...
│
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── README.md
└── AGENTS.md                      # AI/Dev guidelines
```

### 11.2 Files to Create/Modify

| File | Action | Priority |
|------|--------|----------|
| `src/models/transaction.py` | Create | P0 |
| `src/parsers/base.py` | Create | P0 |
| `src/parsers/hdfc.py` | Create | P0 |
| `src/parsers/sbi.py` | Create | P0 |
| `src/parsers/axis.py` | Create | P0 |
| `src/pipeline/orchestrator.py` | Create | P0 |
| `src/exporters/goodbudget.py` | Create | P0 |
| `src/main.py` | Create | P0 |
| `config/config.toml` | Move & update | P0 |
| `tests/` | Create | P1 |
| Old files (`extract_transactions.py`, etc.) | Delete or archive | P1 |

---

## 12. Implementation Roadmap

### 12.1 Step-by-Step TODO List

#### Phase 0: Project Setup (Day 1)
- [x] **0.1** Clean up project structure
  - [x] Create new directory structure as defined in Section 11
  - [x] Move `config.toml` to `config/` directory
  - [x] Archive old scripts to `archive/` or delete
  - [x] Update `.gitignore` for `data/input/`, `logs/`
- [x] **0.2** Set up dependencies
  - [x] Update `pyproject.toml` with correct dependencies
  - [x] Add: `pandas`, `xlrd`, `openpyxl`, `tomli` (or use stdlib `tomllib`)
  - [x] Verify Python version (3.11+ for `tomllib`)
- [x] **0.3** Create empty module files with docstrings

#### Phase 1: Core Models (Day 2)
- [x] **1.1** Implement `Transaction` dataclass in `src/models/transaction.py`
  - [ ] Include hash generation in `__post_init__`
  - [ ] Include `to_goodbudget_row()` method
  - [ ] Add `TransactionType` and `TransactionStatus` enums
- [x] **1.2** Implement `Account` dataclass
- [x] **1.3** Implement `ProcessingResult` dataclass
- [x] **1.4** Write unit tests for models

#### Phase 2: Bank Parsers (Days 3-5)
- [ ] **2.1** Implement `BankParser` abstract base class
  - [ ] Define interface methods
  - [ ] Add helper methods for common operations
- [ ] **2.2** Implement `HDFCParser`
  - [ ] `find_header_row()` logic
  - [ ] Column mapping
  - [ ] Date parsing (DD/MM/YY format)
  - [ ] Handle Withdrawal/Deposit columns
- [ ] **2.3** Implement `SBIParser`
  - [ ] Header detection
  - [ ] Date parsing (DD MMM YYYY format)
  - [ ] Handle Debit/Credit columns
- [ ] **2.4** Implement `AxisParser`
  - [ ] Header detection
  - [ ] Date parsing
  - [ ] Column mapping
- [ ] **2.5** Write tests for each parser using sample files

#### Phase 3: Processing Pipeline (Days 6-7)
- [ ] **3.1** Implement file discovery in `ingestion.py`
  - [ ] Scan directory for supported files
  - [ ] Identify bank from filename
  - [ ] Create `CrawledFile` [[objects]]
- [ ] **3.2** Implement `transformer.py`
  - [ ] Date standardization
  - [ ] Amount parsing (handle commas, symbols)
  - [ ] Description cleaning
- [ ] **3.3** Implement `deduplicator.py`
  - [ ] Track processed hashes (in-memory for MVP)
  - [ ] Skip duplicates, log count
- [ ] **3.4** Implement `transfer_detector.py`
  - [ ] Match same-day, same-amount, opposite-type transactions
  - [ ] Flag as internal transfers
- [ ] **3.5** Implement `orchestrator.py`
  - [ ] Wire all stages together
  - [ ] Handle errors gracefully
  - [ ] Move files to processed/failed directories

#### Phase 4: Export & CLI (Day 8)
- [ ] **4.1** Implement Goodbudget CSV exporter
  - [ ] Format according to spec
  - [ ] Handle encoding (UTF-8)
- [ ] **4.2** Implement processing report generator (JSON)
- [ ] **4.3** Implement CLI in `main.py`
  - [ ] `fipro process` - run full pipeline
  - [ ] `fipro status` - show pending files
  - [ ] Basic argument parsing with `argparse`
- [ ] **4.4** Add logging throughout pipeline

#### Phase 5: Testing & Polish (Days 9-10)
- [ ] **5.1** Create anonymized test fixtures
- [ ] **5.2** Write integration tests for full pipeline
- [ ] **5.3** Test with real bank statements
- [ ] **5.4** Fix edge cases discovered
- [ ] **5.5** Update README with usage instructions
- [ ] **5.6** Clean up code, add docstrings

### 12.2 Milestone Checkpoints

| Milestone | Deliverable | Target |
|-----------|-------------|--------|
| M1 | Models complete with tests | Day 2 |
| M2 | All 3 parsers working | Day 5 |
| M3 | Full pipeline working E2E | Day 7 |
| M4 | CLI + CSV export working | Day 8 |
| M5 | Tested & documented | Day 10 |

### 12.3 Implementation Plan Sync

Implementation plans live in `docs/plans/`. The PRD stays aligned with those plan chunks by recording the active implementation slices and their intended scope here.

| Date | Plan File | Scope | Status |
|------|-----------|-------|--------|
| 2026-03-07 | `docs/plans/2026-03-07-fixture-regression-design.md` | Checked-in parser and pipeline fixture strategy for regression coverage | Merged into implementation branch and main |
| 2026-03-08 | `docs/plans/2026-03-08-usable-bank-statement-mvp-implementation-plan.md` | End-to-end Excel statement MVP: CLI, orchestration, deduplication, transfer detection, Goodbudget export, processing report | Implemented on `feature/implementation`, merged into `origin/main` on 2026-03-08 |
| 2026-03-11 | `docs/plans/2026-03-11-raw-export-extraction-fixtures-design.md` | Raw monthly export extraction fixtures and regression tests | On `feature/budgetting` |
| 2026-04-14 | `docs/plans/2026-04-14-agent-ready-minimum.md` | Wire ruff/mypy/pytest-cov, pre-commit, uv.lock, README, .cursor/rules for agent productivity | On `feature/budgetting` |

Sync rule for future sessions:
- add each implementation-plan chunk under `docs/plans/`
- update this table with the new chunk, scope, and status
- keep the PRD focused on product-level intent while plan files capture session-level execution detail

---

## 13. Technical Specifications

### 13.1 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.11+ |
| Excel parsing | pandas + xlrd/openpyxl | pandas 2.x |
| Configuration | TOML (stdlib) | tomllib |
| CLI | argparse (stdlib) | - |
| Testing | pytest | 7.x |
| Logging | logging (stdlib) | - |
| Linting | ruff | latest |
| Formatting | ruff format (black-compatible) | latest |
| Type checking | mypy | latest |

### 13.2 Configuration Schema

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
logs = "logs"

[processing]
supported_extensions = ["xls", "xlsx"]
skip_internal_transfers = false  # Include in export or not
date_format_output = "%Y-%m-%d"

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

### 13.3 Logging Configuration

```python
LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/fipro.log",
            "maxBytes": 5242880,  # 5MB
            "backupCount": 3,
            "formatter": "standard"
        }
    },
    "loggers": {
        "fipro": {
            "handlers": ["console", "file"],
            "level": "DEBUG"
        }
    }
}
```

---

## 14. Testing Strategy

### 14.1 Test Categories

| Category | Purpose | Coverage Target |
|----------|---------|-----------------|
| Unit tests | Individual functions | 80% |
| Parser tests | Each bank parser | 100% of known formats |
| Integration tests | Full pipeline | Happy path + error cases |
| Regression tests | Previously failed cases | As discovered |

### 14.2 Test Data Requirements

1. **Anonymized samples**: Create fake bank statements with realistic structure
2. **Edge cases**: Empty files, corrupted files, unusual formats
3. **Real data validation**: Test with actual (gitignored) statements

### 14.3 Sample Test Cases

```python
# test_hdfc_parser.py

def test_hdfc_finds_correct_header_row():
    """HDFC statements have ~15 rows of preamble before data"""

def test_hdfc_parses_withdrawal_correctly():
    """Withdrawal column should map to debit transaction"""

def test_hdfc_handles_missing_balance():
    """Should not fail if balance column is empty"""

# test_transfer_detection.py

def test_detects_same_day_transfer():
    """Rs 10000 from HDFC to SBI on same day = internal transfer"""

def test_does_not_flag_coincidental_amounts():
    """Different dates should not be flagged as transfer"""
```

---

## 15. Known Constraints & Risks

### 15.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Bank format changes | Parser breaks | Modular parsers, easy to update |
| Date format variations | Parsing errors | Multiple format attempts with fallback |
| Excel version issues | Read failures | Support both xls and xlsx with xlrd/openpyxl |
| Large files | Memory issues | Stream processing if needed (future) |

### 15.2 Known Limitations

1. **Manual download**: User must download statements from bank portals
2. **No real-time sync**: Batch processing only
3. **Limited deduplication**: In-memory hash tracking (resets each run)
4. **No categorization**: All transactions exported as "Unallocated"

### 15.3 Assumptions

1. Bank statement format remains consistent within a bank
2. User has access to download Excel statements
3. Statements are in English
4. Amounts are in INR

---

## 16. Future Directions

This section captures ambitious features and architectural changes for post-MVP development. These ideas are preserved from earlier planning but are explicitly **out of scope** for the initial release.

### 16.1 Version Roadmap

```
v1.0 (MVP) ─────────────────────────────────────────────────────────────
│ • Excel parsing (HDFC, SBI, Axis)
│ • CLI interface
│ • CSV export for Goodbudget
│ • Internal transfer detection
│ • Hash-based deduplication
│
v1.1 (PDF Support) ─────────────────────────────────────────────────────
│ • Credit card PDF parsing
│ • LLMWhisperer/Tesseract OCR integration
│ • Password-protected PDF handling
│
v1.2 (Persistence) ─────────────────────────────────────────────────────
│ • SQLite database storage
│ • Persistent deduplication
│ • Transaction editing/correction
│ • Rule-based auto-categorization
│
v2.0 (Budgeting) ───────────────────────────────────────────────────────
│ • Web UI (React + FastAPI)
│ • Zero-based/envelope budget features
│ • Envelope allocation & funding
│ • Budget vs. actual tracking
│ • Monthly rollover with carryover rules
│ • Splitwise integration handling
│
v3.0 (Multi-user) ──────────────────────────────────────────────────────
  • Local-first architecture (CRDTs for sync)
  • Optional cloud backup
  • Family account support
  • End-to-end encryption
```

### 16.2 PDF Parsing Strategy (v1.1)

For credit card statements:
- **Primary tool**: `pdfplumber` for text extraction
- **OCR fallback**: Tesseract for scanned documents
- **LLMWhisperer**: Proven in POC for complex layouts
- **Password handling**: `PyMuPDF` with password parameter

### 16.3 Envelope Budgeting System (v2.0)

Based on Goodbudget analysis and personal workflow requirements:

#### Core Concepts

1. **Two-Layer Mental Model**
   - **Accounts Layer**: Actual money in bank accounts (HDFC, SBI, Axis)
   - **Envelopes Layer**: Virtual allocation of that money for different purposes

2. **Envelope vs Account Distinction**
   - Account balance = actual money you have
   - Envelope balance = how you've allocated that money
   - Sum of all envelope balances should equal sum of all account balances

3. **Envelope Properties**
   ```python
   class Envelope:
       name: str
       allocated: Decimal      # Budget for this period
       spent: Decimal          # Sum of transactions
       remaining: Decimal      # allocated - spent
       carryover: bool         # Roll unused funds to next period
       group: str              # Category grouping (Needs, Wants, Savings)
   ```

#### Your Account Strategy (from Budgeting.md)

| Account | Purpose | Usage Pattern |
|---------|---------|---------------|
| **Axis** | Salary credit | Income arrives here, primary savings |
| **HDFC** | Daily transactions | Quick 4-digit PIN, convenience |
| **SBI** | Recurring payments | Medical, commute, structured expenses |

#### Envelope Categories (from your workflow)

**Needs (Fixed)**
- Rent
- Medical (ADHD meds, psych, therapy) - ₹6000/month
- Commute/Work - ₹1000/month
- Bills & Utilities

**Wants (Variable)**
- Food & Dining
- Shopping
- Entertainment
- Personal Grooming
- House/Decor

**Savings & Goals**
- Emergency Fund (keep separate from savings)
- SIPs (HDFC account)
- Volatile Trading (SBI account)
- Long-term Investments (Axis - includes annual premiums)

#### Special Transaction Handling

**Splitwise Transactions**
Two-part mental model:
1. **Money owed TO you**: Treat as expense (assume won't be paid back)
2. **Money YOU owe**: Future expense, similar to credit card

**Credit Card Transactions**
- Backdated transactions that affect budget timing
- Pay off after earning interest on savings
- Track cashback as negative expense → envelope boost

**Internal Transfers**
- Between own accounts: Not income/expense
- Flag and optionally exclude from budget calculations

#### Envelope Funding Workflow (Monthly)

```
1. Income arrives (salary credit to Axis)
2. Calculate total available = Sum of all account balances
3. Allocate to envelopes:
   ├── Fixed envelopes first (rent, bills, medical)
   ├── Savings goals second (emergency fund, SIPs)
   └── Variable envelopes last (food, entertainment)
4. Over-budget warning if allocations > available
5. Start tracking expenses against envelopes
```

### 16.4 Database Schema (v1.2)

```sql
-- Future SQLite schema
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    hash TEXT UNIQUE NOT NULL,
    transaction_date DATE NOT NULL,
    description TEXT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    transaction_type TEXT CHECK(transaction_type IN ('debit', 'credit')),
    category_id INTEGER REFERENCES categories(id),
    envelope_id INTEGER REFERENCES envelopes(id),
    source_bank TEXT NOT NULL,
    source_file TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    balance DECIMAL(12,2),
    raw_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    parent_id INTEGER REFERENCES categories(id),
    is_income BOOLEAN DEFAULT FALSE
);

CREATE TABLE envelopes (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    budget_amount DECIMAL(12,2),
    category_id INTEGER REFERENCES categories(id)
);

CREATE TABLE categorization_rules (
    id INTEGER PRIMARY KEY,
    pattern TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    priority INTEGER DEFAULT 0
);

-- Envelope budgeting tables (v2.0)
CREATE TABLE envelopes (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    group_name TEXT,  -- 'Needs', 'Wants', 'Savings'
    allocated DECIMAL(12,2) DEFAULT 0,
    carryover BOOLEAN DEFAULT FALSE,
    color TEXT DEFAULT '#6366f1',
    icon TEXT DEFAULT 'wallet',
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE envelope_periods (
    id INTEGER PRIMARY KEY,
    envelope_id INTEGER REFERENCES envelopes(id),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    budgeted DECIMAL(12,2) NOT NULL,
    carried_over DECIMAL(12,2) DEFAULT 0
);

CREATE TABLE accounts (
    id INTEGER PRIMARY KEY,
    bank TEXT NOT NULL,
    nickname TEXT,
    account_type TEXT,  -- 'savings', 'current', 'credit'
    last_4_digits TEXT,
    is_active BOOLEAN DEFAULT TRUE
);
```

### 16.5 Multi-Language Architecture (Preserved Vision)

The following was explored for a high-performance, production system. Preserved for future reference:

#### Go - I/O Layer
- File system monitoring with `fsnotify`
- Concurrent PDF processing with goroutines
- API gateway with `gin` or `echo`

#### Julia - Analytics Engine
- Large-scale data processing with `DataFrames.jl`
- ML categorization with `MLJ.jl`
- Financial calculations

#### Rust - Performance Components
- PDF parsing core with `lopdf`
- Cryptographic operations with `ring`
- WASM for browser-based processing

**Note**: This architecture is premature for a personal project. Revisit only if:
- Processing 10,000+ transactions/month
- Building for public release
- Performance becomes a bottleneck

### 16.6 Local-First Multi-User Architecture

For eventual family/shared use with privacy:
- **CRDTs**: Conflict-free replicated data types for sync
- **End-to-end encryption**: Data encrypted before any sync
- **Optional cloud**: Self-hostable sync server
- **Local-first**: Full functionality without internet

### 16.7 Advanced Features (from Design Analysis)

**Transaction Ingestion Sources (Future)**
- SMS parsing for real-time expense tracking (Android advantage)
- Email ingestion (IMAP collector for receipts)
- Bank API integration (Plaid/Yodlee equivalent for India)

**Intelligent Features**
- ML-based transaction categorization (BERT embeddings → envelope assignment)
- Active learning: Low-confidence predictions flagged for user review
- Cashback detection and flexible allocation (original envelope, general fund, or specific target)

**Debt Management**
- EMI handling with principal/interest breakdown
- Prepayment scenario modeling
- Interest savings calculators

**UI/UX Features**
- Drag-and-drop envelope funding interface
- Color-coded envelope status (green/yellow/red)
- One-click transfer between envelopes
- "Emergency Fund" quick access
- Projected next month's budget preview

**Reporting & Analytics**
- Spending trends over time
- Category breakdown visualization
- Budget vs. actual comparison
- Cash flow forecasting

---

## 17. Appendices

### Appendix A: Goodbudget Import Specification

Source: Goodbudget official documentation

**Required columns**: Date, Envelope, Account, Name, Amount, Status
**Optional columns**: Notes
**Date format**: YYYY-MM-DD (ISO 8601)
**Amount format**: Signed decimal (negative for expenses)
**Encoding**: UTF-8
**File type**: CSV with headers

### Appendix B: Sample Bank Statement Structures

#### HDFC Sample (rows 1-20)
```
Row 1-14: Bank logo, address, account details, period
Row 15: Headers (Date, Narration, Chq./Ref.No., Value Dt, Withdrawal Amt., Deposit Amt., Closing Balance)
Row 16+: Transaction data
```

#### SBI Sample
```
Row 1-10: Account summary, statement period
Row 11: Headers (Txn Date, Value Date, Description, Ref No., Debit, Credit, Balance)
Row 12+: Transaction data
```

### Appendix C: Common Transaction Patterns

For future auto-categorization:

| Pattern | Category |
|---------|----------|
| `UPI.*SWIGGY` | Food & Dining |
| `UPI.*ZOMATO` | Food & Dining |
| `UPI.*AMAZON` | Shopping |
| `NEFT.*SALARY` | Income |
| `ATM.*WDL` | Cash Withdrawal |
| `UPI.*PHONEPE` | Transfers (needs context) |

### Appendix D: Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-28 | Python-only MVP | Multi-language premature for personal project |
| 2025-11-28 | CSV export over database | Faster path to Goodbudget integration |
| 2025-11-28 | No web UI for MVP | CLI sufficient for personal use |
| 2025-11-28 | Local-first architecture | Privacy critical for financial data |
| 2025-11-28 | Goodbudget as external budget tracker | Leverage existing app while building parser |

### Appendix E: External Resources

| Resource | Purpose |
|----------|---------|
| [Goodbudget App](https://goodbudget.com) | External envelope budgeting (current workflow) |
| [Budget Google Sheet](https://docs.google.com/spreadsheets/d/1CB6OIvYwx6saB7GxmiTty8VF3hOmIz_NeHZmrR431rM/) | Your envelope allocation reference |
| [Goodbudget Video Tutorial](https://www.youtube.com/watch?v=27WBTAQOJfc) | Envelope budgeting workflow reference |
| LLMWhisperer | PDF OCR tool (used in POC for credit cards) |

### Appendix F: Your Workflow Context

**Monthly Frequency**
1. Download statements from all 3 banks around salary credit date
2. Mark the row containing salary as reference point
3. Run fipro to consolidate
4. Upload CSV to Goodbudget
5. Allocate envelopes per your Google Sheet budget

**Validation Checkpoints**
- Compare totals before/after processing
- Verify balance matches bank account
- Check internal transfers are correctly flagged

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-28 | Initial PRD consolidating all docs |

---

*This document is the single source of truth for Fipro development. All other documentation (fipro-DESIGN_DOC.md, fipro-NOTES.md, app_to_maintain_finances.md) is now considered archived reference material.*
