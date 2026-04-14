"""
Transaction data models for Fipro.

This module defines the core Transaction dataclass and related enums used throughout
the application. The Transaction model is designed to support both MVP CSV export
and future envelope budgeting features.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional
from enum import Enum
import hashlib


class TransactionType(Enum):
    """Transaction type enumeration."""
    DEBIT = "debit"
    CREDIT = "credit"


class TransactionStatus(Enum):
    """Transaction status enumeration."""
    PENDING = "pending"
    UNCLEARED = "uncleared"
    CLEARED = "cleared"
    TRANSFER = "internal_transfer"
    SPLIT = "split"


@dataclass(slots=True)
class Transaction:
    """
    Core transaction entity.
    
    Designed for:
    - MVP: CSV export to Goodbudget
    - Future: Zero-based/envelope budgeting integration
    
    Attributes:
        transaction_date: Date of the transaction
        description: Transaction description/narration
        amount: Transaction amount (always positive)
        transaction_type: DEBIT or CREDIT
        source_bank: Bank name (HDFC, SBI, AXIS)
        source_file: Source file path
        id: Optional unique identifier
        hash: Auto-generated hash for deduplication
        balance: Account balance after transaction (optional)
        category: Transaction category (for future budgeting)
        envelope: Envelope assignment (for future envelope budgeting)
        status: Transaction status
        notes: Additional notes
        raw_data: Original row data for debugging
        created_at: Timestamp when transaction was created
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
    category: Optional[str] = None
    envelope: Optional[str] = None
    status: TransactionStatus = TransactionStatus.PENDING
    notes: Optional[str] = None
    raw_data: Optional[dict] = None
    
    # Metadata
    created_at: Optional[str] = None
    
    def __post_init__(self):
        """Generate unique hash for deduplication."""
        unique_str = f"{self.transaction_date}{self.amount}{self.description}"
        if self.balance:
            unique_str += str(self.balance)
        self.hash = hashlib.sha256(unique_str.encode()).hexdigest()[:16]
    
    @property
    def signed_amount(self) -> Decimal:
        """Returns negative for debits, positive for credits."""
        if self.transaction_type == TransactionType.DEBIT:
            return -abs(self.amount)
        return abs(self.amount)
    
    def to_goodbudget_row(self) -> dict:
        """Convert to Goodbudget CSV format."""
        return {
            "Date": self.transaction_date.strftime("%Y-%m-%d"),
            "Envelope": self.envelope or "Unallocated",
            "Account": self.source_bank,
            "Name": self.description[:50],
            "Notes": self.notes or "",
            "Amount": str(self.signed_amount),
            "Status": "cleared"
        }

