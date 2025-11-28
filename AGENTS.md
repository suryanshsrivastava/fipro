# AGENTS.md - Development Guidelines for Fipro

## Project Overview

**Fipro** is a comprehensive personal finance management application that automates PDF bank statement parsing and provides unified financial insights. The system processes statements from multiple banks (HDFC, SBI, Axis, etc.) and transforms unstructured data into actionable financial intelligence.

### Architecture Philosophy
- **Current**: Python-centric modular architecture
- **Future**: Polyglot microservices (Python, Go, Julia, Rust)
- **Design**: Data processing pipeline with loose coupling, high cohesion

## Build/Test Commands

### Environment Setup
- **Package Management**: Use `uv` for Python dependencies
- **Virtual Environment**: Check for existing `.fipro-env` before creating new ones
- **Dependencies**: Install with `uv add` or `pip install -r requirements.txt`

### Development Commands
```bash
# Setup development environment
uv sync
source .fipro-env/bin/activate

# Run processing pipeline
python -m src.process_bank_statements

# Start API server (FastAPI)
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

# Database operations
alembic upgrade head  # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
```

### Testing
- **Framework**: `pytest` for backend, `Jest + React Testing Library` for frontend
- **Coverage Target**: 80% for unit tests
- **Commands**:
  ```bash
  python -m pytest tests/ -v --cov=src
  npm test  # Frontend tests
  ```

### Code Quality
- **Linting**: `ruff` for Python, `ESLint` for TypeScript
- **Formatting**: `black` for Python, `Prettier` for TypeScript
- **Type Checking**: `mypy` for Python, TypeScript compiler for frontend

## Technology Stack

### Current Stack (Phase 1)
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy
- **Database**: SQLite (dev) → PostgreSQL (prod)
- **PDF Processing**: PyMuPDF (fitz), pdfplumber, Tesseract OCR
- **Frontend**: React 18 + TypeScript, Material-UI, Vite

### Future Multi-Language Architecture
- **Go**: File orchestration, I/O operations, API gateway
- **Julia**: Data processing, analytics, ML categorization
- **Rust**: Performance-critical components, PDF parsing core
- **Python**: Business logic, API development, integrations

## Data Model & Schema

### Core Transaction Model
```python
@dataclass(slots=True)
class Transaction:
    id: Optional[int] = None
    transaction_date: date
    description: str
    amount: Decimal
    transaction_type: str  # 'debit' or 'credit'
    category_id: Optional[int] = None
    source_bank: str
    source_file: str
    raw_data: Optional[Dict[str, Any]] = None
    hash: str = field(init=False)
    balance: Optional[Decimal] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
```

### Database Schema
- **Primary Table**: `transactions` with proper indexing
- **Supporting Tables**: `categories`, `bank_configs`
- **Key Fields**: `hash` for duplicate prevention, `raw_data` for audit trail

## Code Style Guidelines

### Data Structures
- Use `dataclasses` with `slots=True` for efficiency
- Import: `from dataclasses import dataclass, field`
- Example: `@dataclass(slots=True)`

### Imports & Organization
```python
# Standard library imports first
import os
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any

# Third-party imports
import pandas as pd
from fastapi import FastAPI
from sqlalchemy import Column, Integer, String

# Local imports
from src.models import Transaction
from utils import calculate_hash
```

### Naming Conventions
- **Classes**: PascalCase (e.g., `Transaction`, `BankParser`)
- **Functions/variables**: snake_case (e.g., `extract_transactions`, `process_pdf`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_FILE_SIZE`, `DEFAULT_TIMEOUT`)
- **Private members**: prefix with underscore

### File Organization
```
src/
├── models.py              # Data models and schemas
├── parsers/               # Bank-specific PDF parsers
│   ├── __init__.py
│   ├── hdfc_parser.py
│   ├── sbi_parser.py
│   └── axis_parser.py
├── api/                   # FastAPI application
│   ├── __init__.py
│   ├── main.py
│   └── routes/
├── processing/            # Data processing pipeline
│   ├── __init__.py
│   ├── extractor.py
│   ├── cleaner.py
│   └── standardizer.py
└── database/             # Database operations
    ├── __init__.py
    ├── models.py
    └── migrations/
```

## Bank Parser Implementation

### Strategy Pattern for Banks
```python
class BankParser(ABC):
    @abstractmethod
    def extract_transactions(self, pdf_text: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def validate_statement(self, filename: str) -> bool:
        pass

class HDFCParser(BankParser):
    def extract_transactions(self, pdf_text: str) -> List[Dict]:
        # HDFC-specific parsing logic
        pass
```

### Configuration Management
- Use YAML files for bank-specific parsing rules
- Store regex patterns and date formats in config
- Environment-specific configurations via `config.toml`

## Error Handling & Logging

### Error Classification
- **Level 1 (Critical)**: Database failures, auth issues, file system errors
- **Level 2 (Processing)**: PDF parsing failures, validation errors
- **Level 3 (User)**: Invalid inputs, duplicate uploads

### Logging Configuration
```python
LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'detailed': {
            'format': '{levelname} {asctime} [{name}] {message}',
            'style': '{'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/fipro.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed'
        }
    },
    'loggers': {
        'fipro': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
```

### File Lifecycle Management
```
data/input/ → data/processing/ → data/processed/ (success)
                                    └── data/failed/ (failure)
```

## Security & Privacy

### Data Protection
- **Encryption**: AES-256 for sensitive data at rest
- **Transit**: TLS 1.3 for all API communications
- **Local Storage**: SQLite with encrypted database files
- **File Security**: Automatic cleanup after processing

### Authentication
- **JWT Tokens**: 15-minute access tokens with refresh mechanism
- **Password Security**: bcrypt hashing with salt rounds
- **API Security**: Rate limiting and request validation

## Performance Targets

### Processing Performance
- **File Processing**: < 30 seconds for typical bank statement (1-50 transactions)
- **API Response**: < 500ms for transaction queries
- **Database Queries**: < 100ms for filtered transaction lists
- **File Upload**: Support files up to 10MB

### Scalability Considerations
- **Concurrent Processing**: 100+ simultaneous users (production target)
- **Database Optimization**: Proper indexing and query optimization
- **Caching Strategy**: Redis for session management and frequent queries

## Development Phases

### Phase 1: Core Infrastructure (Weeks 1-4)
- [x] Basic PDF text extraction scripts
- [x] SBI and HDFC statement parsers
- [ ] Implement unified Transaction data model
- [ ] Create robust file orchestrator with error handling
- [ ] Set up SQLite database with SQLAlchemy ORM
- [ ] Implement duplicate detection using hash-based approach

### Phase 2: API & Frontend Foundation (Weeks 5-8)
- [ ] FastAPI server with authentication
- [ ] RESTful API endpoints for transactions
- [ ] React application setup with TypeScript
- [ ] Material-UI component library integration
- [ ] Transaction table with sorting/filtering

### Phase 3: Advanced Features (Weeks 9-12)
- [ ] Rule-based auto-categorization engine
- [ ] Machine learning model for transaction classification
- [ ] Interactive dashboard with key metrics
- [ ] Support for 5+ major Indian banks

### Phase 4: Production Ready (Weeks 13-16)
- [ ] PostgreSQL migration for production
- [ ] Docker containerization
- [ ] CI/CD pipeline setup
- [ ] Security audit and penetration testing

## Testing Strategy

### Testing Pyramid
- **Unit Tests (80%)**: Individual component testing
- **Integration Tests**: API endpoint and database interaction testing
- **End-to-End Tests**: Complete user workflow testing
- **Performance Tests**: Load testing with realistic data volumes

### Test Data Management
- **Sample Statements**: Anonymized bank statements for each supported bank
- **Test Database**: Separate test database with known data sets
- **Mock Services**: Mock external services for consistent testing

## API Development Guidelines

### Core Endpoints
```python
# Transaction management
GET /api/v1/transactions
POST /api/v1/transactions
PUT /api/v1/transactions/{id}
DELETE /api/v1/transactions/{id}

# File processing
POST /api/v1/upload
GET /api/v1/upload/status/{upload_id}

# Analytics
GET /api/v1/analytics/summary
GET /api/v1/analytics/trends

# Categories
GET /api/v1/categories
POST /api/v1/categories
```

### FastAPI Best Practices
- Use Pydantic models for request/response validation
- Implement proper HTTP status codes
- Add comprehensive error handling
- Include automatic OpenAPI documentation
- Use dependency injection for database sessions

## Code Quality Standards

### General Guidelines
- Add reusable code to `utils.py` to avoid duplication
- Use properties for computed attributes in dataclasses
- Follow PEP 8 formatting standards
- Include docstrings for public functions
- Implement proper type hints throughout

### Database Best Practices
- Use SQLAlchemy ORM with proper relationships
- Implement database migrations with Alembic
- Add proper indexes for query performance
- Use connection pooling for production
- Implement proper transaction management

### Frontend Guidelines
- Use TypeScript for type safety
- Implement proper error boundaries
- Use React Hook Form with Zod validation
- Follow Material-UI design patterns
- Implement proper state management with Redux Toolkit

## Deployment & DevOps

### Containerization
```dockerfile
# Multi-stage builds for optimization
FROM python:3.11-slim as builder
# Build dependencies

FROM python:3.11-slim as runtime
# Runtime dependencies
```

### Environment Configuration
- Use environment variables for sensitive configuration
- Implement proper secret management
- Support multiple deployment environments (dev, staging, prod)
- Use infrastructure as code for reproducible deployments

---

**Note**: This document should be updated as the project evolves. Refer to the comprehensive design documents in `fipro-docs/` for detailed architectural specifications and technical requirements.