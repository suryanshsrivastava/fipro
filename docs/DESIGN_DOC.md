# Design Document: fipro (Financial Project)

**Version:** 1.2

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

The system is designed as a multi-stage data processing pipeline. Each stage is a distinct module that performs a specific task, passing its output to the next stage. **Note:** The current implementation is Python-based, but the architecture is designed to evolve into a multi-language microservices platform as outlined in the Future Roadmap (Section 7).

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

### Current Implementation Status

*   [x] Basic PDF text extraction scripts.
*   [x] Parser for SBI statements.
*   [x] Parser for HDFC statements.
*   [ ] **To-Do:** Create a unified `Transaction` data model (e.g., as a Python class or dataclass).
*   [ ] **To-Do:** Implement a robust file orchestrator script.
*   [ ] **To-Do:** Implement data cleaning and standardization logic.
*   [ ] **To-Do:** Set up the SQLite database and `SQLAlchemy` ORM.
*   [ ] **To-Do:** Implement duplicate detection using hashing.

### Short-term Goals (Next 3 months)

*   [ ] **To-Do:** Develop a FastAPI server with endpoints to `GET` transactions.
*   [ ] **To-Do:** Set up a basic React application using `create-react-app`.
*   [ ] **To-Do:** Create a simple table view to display all transactions.
*   [ ] **To-Do:** Add filtering and sorting to the transaction table.

### Medium-term Goals (3-6 months)

*   [ ] **To-Do:** Implement transaction categorization in the UI.
*   [ ] **To-Do:** Create a dashboard with summary widgets (e.g., spending by category).
*   [ ] **To-Do:** Add rule-based auto-categorization (e.g., "all transactions with 'AMAZON' are 'Shopping'").
*   [ ] **To-Do:** Research and implement simple charting/visualization.

**Note:** For the comprehensive multi-language architecture roadmap, see Section 7: Future Roadmap: Multi-Language Architecture.

## 6. Future Ideas (Post-MVP)

*   **Budgeting Module:** Allow users to set monthly budgets by category and track progress.
*   **Investment Tracking:** Connect to brokerage APIs or parse investment statements.
*   **ML-based Categorization:** Use machine learning to automatically suggest categories for new transactions.
*   **Cloud Deployment:** Package the application in Docker containers and deploy it to a cloud service.

**Note:** For detailed technology recommendations and the multi-language architecture roadmap, see the companion document: `docs/TECH_STACK.md`.

## 7. Future Roadmap: Multi-Language Architecture

### 7.1. Vision Statement

Transform `fipro` from a Python-centric application into a **polyglot microservices architecture** where each component is built in the language best suited for its specific function. This approach leverages the strengths of different programming languages to achieve optimal performance, maintainability, and developer productivity.

### 7.2. Language-Specific Component Mapping

#### **Go (Golang) - I/O and Concurrency Layer**
*   **Primary Responsibilities:**
    *   File system monitoring and orchestration
    *   High-throughput PDF ingestion pipeline
    *   Concurrent processing of multiple bank statements
    *   Real-time file change detection (using `fsnotify`)
    *   HTTP API gateway and load balancing
*   **Why Go:**
    *   **Goroutines:** Handle thousands of concurrent PDF processing tasks
    *   **Channels:** Implement backpressure and work distribution
    *   **Zero-copy I/O:** Efficient file handling for large PDFs
    *   **Static binaries:** Easy deployment without runtime dependencies
*   **Target Components:**
    *   File orchestrator service
    *   PDF ingestion service
    *   API gateway
    *   Task queue manager

#### **Julia - Data Processing and Analytics Engine**
*   **Primary Responsibilities:**
    *   Large-scale transaction data consolidation
    *   Statistical analysis and pattern recognition
    *   Financial data cleaning and transformation
    *   Machine learning model training for categorization
    *   Complex financial calculations and aggregations
*   **Why Julia:**
    *   **Performance:** Near-C speed for numerical computations
    *   **DataFrames.jl:** Superior to pandas for large datasets
    *   **Multiple dispatch:** Elegant handling of different data types
    *   **Parallel computing:** Built-in support for distributed processing
    *   **Financial packages:** Rich ecosystem for financial analysis
*   **Target Components:**
    *   Data processing service
    *   Analytics engine
    *   ML categorization service
    *   Financial reporting service

#### **Rust - Performance-Critical Components**
*   **Primary Responsibilities:**
    *   PDF parsing core (replacing Python libraries)
    *   High-frequency database operations
    *   Memory-intensive data structures
    *   Cryptographic operations (hashing, encryption)
*   **Why Rust:**
    *   **Memory safety:** Zero-cost abstractions with guaranteed safety
    *   **Performance:** C/C++ level performance without GC overhead
    *   **Concurrency:** Fearless concurrency with ownership system
    *   **WASM support:** Potential for browser-based processing
*   **Target Components:**
    *   PDF parsing engine
    *   Database connector
    *   Security service

#### **Python - Orchestration and Integration Layer**
*   **Primary Responsibilities:**
    *   Service coordination and workflow management
    *   API development and business logic
    *   Integration with external services
    *   Configuration management and deployment
*   **Why Python (Retained):**
    *   **Ecosystem:** Rich libraries for web frameworks, ML, and data science
    *   **Developer productivity:** Rapid prototyping and iteration
    *   **Integration:** Excellent support for various APIs and protocols
    *   **Team expertise:** Existing knowledge and experience

### 7.3. Architecture Evolution Phases

#### **Phase 1: Foundation (Months 1-3)**
*   Implement Go-based file orchestrator
*   Create service communication layer (gRPC/HTTP)
*   Establish containerized deployment pipeline
*   **Success Metrics:** 10x improvement in concurrent file processing

#### **Phase 2: Data Processing (Months 4-6)**
*   Migrate data processing to Julia service
*   Implement distributed data processing pipeline
*   Add real-time analytics capabilities
*   **Success Metrics:** 5x improvement in large dataset processing

#### **Phase 3: Performance Optimization (Months 7-9)**
*   Integrate Rust-based PDF parser
*   Optimize database operations
*   Implement caching and memoization layers
*   **Success Metrics:** 3x improvement in PDF processing speed

#### **Phase 4: Advanced Features (Months 10-12)**
*   ML-powered categorization service
*   Real-time financial insights dashboard
*   Advanced reporting and visualization
*   **Success Metrics:** 90%+ accuracy in auto-categorization

### 7.4. Technical Implementation Strategy

#### **Service Communication**
*   **Primary:** gRPC for inter-service communication (type-safe, high-performance)
*   **Fallback:** HTTP REST APIs for external integrations
*   **Message Queue:** Redis Streams or Apache Kafka for async processing

#### **Data Flow Architecture**
```
PDF Files → Go Orchestrator → Rust Parser → Julia Processor → Python API → Frontend
    ↓              ↓              ↓            ↓           ↓
  File System   Task Queue   Raw Data    Clean Data   Business Logic
```

#### **Deployment Strategy**
*   **Containerization:** Docker containers for each service
*   **Orchestration:** Kubernetes for production, Docker Compose for development
*   **Service Mesh:** Istio for advanced traffic management and observability
*   **Monitoring:** Prometheus + Grafana for metrics, Jaeger for tracing

### 7.5. Migration and Compatibility

#### **Backward Compatibility**
*   Maintain Python API compatibility during transition
*   Implement feature flags for gradual rollout
*   Provide migration scripts for existing data

#### **Data Migration Strategy**
*   **Phase 1:** Dual-write to both old and new systems
*   **Phase 2:** Read from new system, validate against old
*   **Phase 3:** Complete cutover with rollback capability

#### **Testing Strategy**
*   **Contract testing:** Ensure service interfaces remain stable
*   **Performance testing:** Validate improvements at each phase
*   **Chaos engineering:** Test system resilience and failure modes

### 7.6. Risk Mitigation

#### **Technical Risks**
*   **Complexity:** Mitigate with comprehensive documentation and training
*   **Integration challenges:** Use well-established protocols (gRPC, REST)
*   **Performance regressions:** Implement continuous performance monitoring

#### **Operational Risks**
*   **Team expertise:** Invest in training and knowledge sharing
*   **Deployment complexity:** Use infrastructure as code and automated testing
*   **Monitoring gaps:** Implement comprehensive observability from day one

### 7.7. Success Criteria and KPIs

#### **Performance Metrics**
*   **Throughput:** Process 1000+ PDFs concurrently
*   **Latency:** Sub-second response time for API calls
*   **Scalability:** Linear scaling with additional resources

#### **Business Metrics**
*   **Accuracy:** 99%+ transaction extraction accuracy
*   **Reliability:** 99.9% uptime for critical services
*   **Developer Velocity:** 2x faster feature development

#### **Operational Metrics**
*   **Deployment Frequency:** Multiple deployments per day
*   **Lead Time:** < 1 hour from commit to production
*   **MTTR:** < 15 minutes for critical incidents

This multi-language architecture represents a significant evolution of the `fipro` system, transforming it from a monolithic Python application into a high-performance, scalable, and maintainable microservices platform that leverages the best capabilities of each programming language.