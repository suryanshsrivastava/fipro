# Transaction Extraction Script

This project contains multiple scripts for processing bank statements and extracting transaction data:

1. **`extract_transactions.py`** - Extracts transactions from text files
2. **`process_bank_statements.py`** - Processes multiple bank statement files (PDF, Excel, CSV)
3. **`ingest_transactions.py`** - Ingests and processes transaction data

## Configuration

All scripts use a single `config.toml` file to configure paths and settings:

```toml
[paths]
# Input file path for extract_transactions.py
input_file = "/mnt/c/Users/Suryansh Srivastava/Downloads/data/*.pdf"

# Output file path for extract_transactions.py
output_file = "output.csv"

# Input data directory for process_bank_statements.py
input_data = "data/input"

# Output data directory for process_bank_statements.py
output_data = "data/output"
```

## Usage

### 1. Extract Transactions
```bash
python extract_transactions.py
```
- Reads from `input_file` specified in config
- Outputs to `output_file` specified in config

### 2. Process Bank Statements
```bash
python process_bank_statements.py
```
- Reads from `input_data` directory specified in config
- Outputs consolidated transactions to `output_data` directory

### 3. Ingest Transactions
```bash
python ingest_transactions.py
```
- Reads from `input_file` specified in config
- Outputs to `output_file` specified in config

## Features

- **Centralized Configuration**: All paths configured in one TOML file
- **Multiple File Formats**: Supports PDF, Excel, and CSV files
- **Bank Consolidation**: Groups transactions by bank (HDFC, SBI, AXIS)
- **Data Validation**: Ensures data integrity and consistency
- **Transaction Classification**: Automatically tags transactions by category

## Requirements

- Python 3.11+ (for `tomllib` support)
- pandas
- Input files should contain transaction data in expected formats


