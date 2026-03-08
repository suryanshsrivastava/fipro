# Transaction Extraction Script

This project contains multiple scripts for processing bank statements and extracting transaction data:

1. **`ingest_transactions.py`** - Main script for discovering files and loading them into dataframes
2. **`extract_transactions.py`** - Legacy script for extracting transactions from text files
3. **`process_bank_statements.py`** - Processes multiple bank statement files (PDF, Excel, CSV)

## Configuration

All scripts use a single `config.toml` file to configure paths and settings:

```toml
[paths]
# Input directory for file discovery
input = "data/input"

# Output file path for legacy extract_transactions.py
output_file = "output.csv"

# Input data directory for process_bank_statements.py
input_data = "data/input"

# Output data directory for process_bank_statements.py
output_data = "data/output"
```

## Usage

### 1. Discover Files and Load Dataframes (Recommended)
```bash
python ingest_transactions.py
```
- Discovers files in the `input` directory specified in config
- Checks file permissions and basic structure
- Loads files into pandas dataframes
- Groups files by bank (HDFC, SBI, AXIS)
- Provides file analysis and summary

### 2. Legacy: Extract Transactions
```bash
python extract_transactions.py
```
- Reads from `input_file` specified in config
- Outputs to `output_file` specified in config

### 3. Process Bank Statements
```bash
python process_bank_statements.py
```
- Reads from `input_data` directory specified in config
- Outputs consolidated transactions to `output_data` directory

## Features

- **File Discovery**: Automatically discovers supported file types (PDF, Excel, CSV)
- **Permission Checking**: Verifies file readability before processing
- **Dataframe Loading**: Loads files into pandas dataframes for analysis
- **Bank Consolidation**: Groups files by bank (HDFC, SBI, AXIS)
- **Centralized Configuration**: All paths configured in one TOML file
- **Multiple File Formats**: Supports PDF, Excel, and CSV files
- **Data Validation**: Ensures data integrity and consistency

## Key Functions

### `discover_files(config)`
- Discovers files in the input directory
- Checks file permissions and basic structure
- Returns list of `CrawledFile` objects with metadata

### `load_files_to_dataframes(files)`
- Loads discovered files into pandas dataframes
- Handles CSV, Excel (all sheets), and PDF files
- Returns dictionary mapping file paths to dataframes

### `analyze_discovered_files(files)`
- Provides summary statistics of discovered files
- Groups by extension, bank, and size

## Requirements

- Python 3.11+ (for `tomllib` support)
- pandas
- Input files should contain transaction data in expected formats


