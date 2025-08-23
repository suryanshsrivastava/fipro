# Design Document: fipro (Financial Project)

**Version:** 1.1

## 1. Overview

### 1.1. Introduction

`fipro` is a personal finance management tool designed to automate the process of tracking expenses and income. It ingests digital bank statements (PDFs), extracts transaction data, cleans and categorizes it, and provides a unified view of a user's financial activity. The primary goal is to eliminate the manual effort of data entry and provide clear insights into spending habits.

### 1.2. Goals and Objectives

*   **Automate Data Entry:** Automatically extract transaction data from PDF bank statements from multiple financial institutions.
*   **Unify Financial Data:** Consolidate transactions from various accounts into a single, standardized format.
*   **Provide Insights:** Enable users to categorize transactions and eventually visualize spending patterns.
*   **Ensure Accuracy:** Maintain high accuracy in data extraction and processing.
*   **Be Extensible:** Design a modular system where new banks and new features can be added easily.

## 2. System Architecture

The system is designed as a multi-stage data processing pipeline. Each stage is a distinct module that performs a specific task, passing its output to the next stage.

### 2.1. Architectural Diagram

```
                               +------------------+
                               |   Input Folder   |
                               | (e.g., data/raw) |
                               +------------------+
                                        | (1. Ingestion)
                                        v
+-----------------+             +------------------+             +-----------------+
|   File Processor|------------>|  PDF Parser      |------------>|  Transaction    |
| (Orchestrator)  |   (File)    | (Bank-specific   |  (Raw Text) |    Extractor    |
+-----------------+             |    Strategies)   |             +-----------------+
        ^                       +------------------+                      | (Structured Data)
        |                                                                v
        |                                                        +-----------------+
        | (Success/Failure)                                      |  Data Cleaner & |
        +--------------------------------------------------------|  Standardizer   |
                                                                 +-----------------+
                                                                         | (Unified Records)
                                                                         v
                                                                 +-----------------+
                                                                 |   Database      |
                                                                 |  (SQLite/Postg) |
                                                                 +-----------------+
                                                                         |
                                                                         v
                                                                 +-----------------+
                                                                 |    API Server   |
                                                                 |    (FastAPI)    |
                                                                 +-----------------+
                                                                         |
                                                                         v
                                                                 +-----------------+
                                                                 |  Web Frontend   |
                                                                 |     (React)     |
                                                                 +-----------------+
```

### 2.2. Component Breakdown

*   **File Processor (Orchestrator):** A master script that monitors the input directory. When a new file appears, it identifies the bank (e.g., from the filename), triggers the appropriate parser, and manages the file's lifecycle (e.g., moving it to a `processed` or `failed` directory).
*   **PDF Parser:** A collection of modules, each designed to handle the specific layout and format of a single bank's statement (a "Strategy Pattern"). Its sole job is to extract raw text content accurately.
*   **Transaction Extractor:** Takes the raw text from the parser and uses regular expressions and logic to identify and extract individual transaction records.
*   **Data Cleaner & Standardizer:** Cleans the extracted data (e.g., removes currency symbols, standardizes date formats) and maps it to a unified data model.
*   **Database:** Stores the clean, unified transaction data.
*   **API Server:** Exposes the data in the database via a RESTful API for the frontend.
*   **Web Frontend:** A user interface for viewing, searching, and categorizing transactions.

## 3. Data Model and Schema

A core, unified data model is crucial for consolidation. All extracted transactions will be mapped to this schema.

**`transactions` Table Schema:**

| Column Name | Data Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key | `101` |
| `transaction_date` | `DATE` | The date the transaction occurred. | `2023-10-26` |
| `description` | `TEXT` | The raw transaction description. | `UPI/ MERCHANT/ AMAZON PAY` |
| `amount` | `DECIMAL(10, 2)` | The transaction amount. | `150.75` |
| `type` | `TEXT` | 'debit' or 'credit'. | `debit` |
| `category` | `TEXT` | User-defined category. | `Shopping` |
| `source_bank` | `TEXT` | The bank this transaction came from. | `HDFC` |
| `source_file` | `TEXT` | The filename of the source statement. | `hdfc_oct_2023.pdf` |
| `hash` | `TEXT` | An MD5/SHA256 hash of key fields to prevent duplicates. | `a1b2c3d4...` |
| `created_at` | `TIMESTAMP` | When the record was inserted. | `2023-10-27 10:00:00` |

## 4. Error Handling and Logging

*   **File Lifecycle:** Successfully processed files will be moved from `data/input` to `data/processed`. Files that fail at any stage will be moved to `data/failed`.
*   **Logging:** The system will use Python's `logging` module.
    *   `INFO`: Log major steps (e.g., "Starting processing for file X", "Found 50 transactions").
    *   `WARNING`: Log recoverable issues (e.g., "Could not parse one line, skipping").
    *   `ERROR`: Log critical failures (e.g., "PDF is password-protected and cannot be read").
*   **Duplicate Prevention:** The `hash` field in the database will have a `UNIQUE` constraint. The application will calculate the hash before insertion; if it violates the constraint, the transaction is a duplicate and will be skipped.

## 5. Project Roadmap and Status

### Milestone 1: Core Pipeline (In Progress)

*   [x] Basic PDF text extraction scripts.
*   [x] Parser for SBI statements.
*   [x] Parser for HDFC statements.
*   [ ] **To-Do:** Create a unified `Transaction` data model (e.g., as a Python class or dataclass).
*   [ ] **To-Do:** Implement a robust file orchestrator script.
*   [ ] **To-Do:** Implement data cleaning and standardization logic.
*   [ ] **To-Do:** Set up the SQLite database and `SQLAlchemy` ORM.
*   [ ] **To-Do:** Implement duplicate detection using hashing.

### Milestone 2: API and Basic Frontend (Not Started)

*   [ ] **To-Do:** Develop a FastAPI server with endpoints to `GET` transactions.
*   [ ] **To-Do:** Set up a basic React application using `create-react-app`.
*   [ ] **To-Do:** Create a simple table view to display all transactions.
*   [ ] **To-Do:** Add filtering and sorting to the transaction table.

### Milestone 3: Advanced Features (Future)

*   [ ] **To-Do:** Implement transaction categorization in the UI.
*   [ ] **To-Do:** Create a dashboard with summary widgets (e.g., spending by category).
*   [ ] **To-Do:** Add rule-based auto-categorization (e.g., "all transactions with 'AMAZON' are 'Shopping'").
*   [ ] **To-Do:** Research and implement simple charting/visualization.

## 6. Future Ideas (Post-MVP)

*   **Budgeting Module:** Allow users to set monthly budgets by category and track progress.
*   **Investment Tracking:** Connect to brokerage APIs or parse investment statements.
*   **ML-based Categorization:** Use machine learning to automatically suggest categories for new transactions.
*   **Cloud Deployment:** Package the application in Docker containers and deploy it to a cloud service.