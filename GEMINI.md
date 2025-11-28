This is an exceptionally detailed and well-structured design document. You have moved past the "idea" phase and have a concrete blueprint for implementation.

Here is a review of your design, highlighting strengths and potential pitfalls, followed by a Project Scaffold to help you kick off Phase 1 (Core Infrastructure) immediately.

Design Review & Feedback
Strengths:

Schema Design: The hash field in the transaction table is crucial. Without it, re-uploading the same bank statement would result in thousands of duplicates.
Strategy Pattern: Decoupling the PDF Parser into bank-specific strategies is the correct architectural choice. Bank formats change, and you don't want to break the whole app to fix one bank's layout.
Roadmap Reality: You have sensibly deferred the complex multi-language architecture (Go/Julia/Rust) to a future roadmap and focused on a robust Python/FastAPI MVP first.
Risks & Suggestions:

The "PDF Hell": Even with pdfplumber, banks often change layouts slightly (e.g., advertising banners shifting rows).
Suggestion: Implement a "Validation Layer" immediately after extraction. If the extracted total debits/credits don't match the "Opening/Closing Balance" summary usually found at the top/bottom of PDFs, flag the file as Manual Review Needed.
Hash Collision/Granularity:
Suggestion: For the hash, do not just hash the row. Concatenate Transaction Date + Amount + Description + Balance (if available). Sometimes you buy coffee twice at the same place for the same amount on the same day. The Balance column is often the only differentiator.
OCR Dependency: Tesseract is heavy.
Suggestion: Only load OCR libraries if the text extraction returns empty strings. 95% of modern bank statements are generated PDFs (text layer exists), not scanned images.
Phase 1: Implementation Scaffold
Based on your Technology Stack (Section 7) and Schema (Section 3), here is the initial project structure and code skeleton to get you started.

1. Project Directory Structure
text

fipro_backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI Entry Point
│   ├── core/
│   │   ├── config.py        # Env variables
│   │   └── security.py      # JWT & Hashing
│   ├── db/
│   │   ├── base.py
│   │   └── session.py       # DB connection
│   ├── models/              # SQLAlchemy Models
│   │   ├── transaction.py
│   │   └── category.py
│   ├── schemas/             # Pydantic Models
│   │   └── transaction.py
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           └── transactions.py
│   └── services/
│       ├── orchestrator.py  # File Orchestrator
│       └── parsers/         # The Strategy Pattern
│           ├── base.py      # Abstract Base Class
│           ├── hdfc.py
│           └── sbi.py
├── alembic/                 # Database Migrations
├── data/
│   ├── input/
│   ├── processed/
│   └── failed/
├── tests/
├── requirements.txt
└── .env
2. Database Models (app/models/transaction.py)
This maps directly to your SQL schema in Section 3.1.

Python

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, JSON, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    description = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    transaction_type = Column(String(10))  # 'debit' or 'credit'
    
    # Foreign Key to Categories
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Source metadata
    source_bank = Column(String(50), nullable=False, index=True)
    source_file = Column(String(255), nullable=False)
    
    # For debugging parsing logic later
    raw_data = Column(JSON, nullable=True)
    
    # Deduplication
    hash = Column(String(64), unique=True, nullable=False, index=True)
    balance = Column(Numeric(12, 2), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="transactions")
3. The Parser Strategy Pattern (app/services/parsers/base.py)
This implements the architecture defined in Section 2.3.1.

Python

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from datetime import date
from decimal import Decimal

class ExtractedTransaction(BaseModel):
    """Standardized Data Transfer Object"""
    transaction_date: date
    description: str
    amount: Decimal
    transaction_type: str # 'debit' or 'credit'
    balance: Optional[Decimal] = None
    raw_line: str

class BankParserStrategy(ABC):
    """
    Abstract Base Class that all Bank Parsers must implement.
    """

    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """
        Check if this parser supports the given file 
        (e.g., by checking filename pattern or reading first line).
        """
        pass

    @abstractmethod
    def parse(self, file_path: str, password: str = None) -> List[ExtractedTransaction]:
        """
        Extract transactions from the PDF.
        """
        pass

    def normalize_date(self, date_str: str) -> date:
        """Helper to convert bank specific dates to Python date objects"""
        raise NotImplementedError
4. HDFC Implementation Example (app/services/parsers/hdfc.py)
Python

import pdfplumber
import re
from decimal import Decimal
from datetime import datetime
from app.services.parsers.base import BankParserStrategy, ExtractedTransaction

class HDFCParser(BankParserStrategy):
    
    def can_parse(self, file_path: str) -> bool:
        # Simple check: filename contains 'HDFC' or read PDF header
        return "HDFC" in file_path.upper()

    def parse(self, file_path: str, password: str = None) -> list[ExtractedTransaction]:
        transactions = []
        
        with pdfplumber.open(file_path, password=password) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                for line in text.split('\n'):
                    # Regex logic specific to HDFC standard format
                    # Example: 24/08/2025 UPI-AMAZON-PAY 500.00 Dr
                    match = re.match(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d+\.\d{2})\s+(Cr|Dr)', line)
                    
                    if match:
                        date_str, desc, amt, dr_cr = match.groups()
                        
                        t_type = 'debit' if 'Dr' in dr_cr else 'credit'
                        
                        trans = ExtractedTransaction(
                            transaction_date=datetime.strptime(date_str, "%d/%m/%Y").date(),
                            description=desc.strip(),
                            amount=Decimal(amt),
                            transaction_type=t_type,
                            raw_line=line
                        )
                        transactions.append(trans)
        
        return transactions
5. File Orchestrator Logic (app/services/orchestrator.py)
Python

import os
import hashlib
import shutil
from app.services.parsers.hdfc import HDFCParser
from app.services.parsers.sbi import SBIParser
# import db session...

class FileOrchestrator:
    def __init__(self, input_dir, processed_dir, failed_dir):
        self.input_dir = input_dir
        self.processed_dir = processed_dir
        self.failed_dir = failed_dir
        self.parsers = [HDFCParser(), SBIParser()]

    def generate_hash(self, t_data):
        """Create unique hash for deduplication"""
        unique_str = f"{t_data.transaction_date}{t_data.amount}{t_data.description}{t_data.balance}"
        return hashlib.sha256(unique_str.encode()).hexdigest()

    def process_directory(self):
        for filename in os.listdir(self.input_dir):
            if not filename.endswith('.pdf'):
                continue
                
            file_path = os.path.join(self.input_dir, filename)
            parser = next((p for p in self.parsers if p.can_parse(file_path)), None)

            if not parser:
                print(f"No parser found for {filename}")
                shutil.move(file_path, os.path.join(self.failed_dir, filename))
                continue

            try:
                # 1. Parse
                raw_transactions = parser.parse(file_path)
                
                # 2. Clean & Save to DB (Pseudo-code)
                # for t in raw_transactions:
                #     t_hash = self.generate_hash(t)
                #     if not db.exists(t_hash):
                #         db.save(t)
                
                # 3. Move to Success
                shutil.move(file_path, os.path.join(self.processed_dir, filename))
                
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
                shutil.move(file_path, os.path.join(self.failed_dir, filename))
Recommended Next Steps
Initialize Environment:

Bash

mkdir fipro_backend && cd fipro_backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary pdfplumber pytesseract
Database Setup:
Start with SQLite for local testing as per your Phase 1 plan.

Bash

# In app/core/config.py
DATABASE_URL = "sqlite:///./fipro.db"
Gather Test Data:
Download 3 months of PDF statements from your own bank accounts.
Important: Manually redact sensitive info (Account Numbers, Names) if you plan to commit these to a repo, or keep them in a .gitignore folder.

Run the Parser:
Don't build the API yet. Write a standalone script that instantiates FileOrchestrator and tries to parse your test PDFs. Print the output to the console. Tweak your Regex until it hits 100% accuracy on those files.