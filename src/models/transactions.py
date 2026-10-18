"""
Transaction data models for Fipro.

This module defines the core Transaction dataclass and related enums used throughout
the application. The Transaction model is designed to support both MVP CSV export
and future envelope budgeting features.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum

from src.utils.narration import counterparty, payment_mode


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
    id: int | None = None
    hash: str = field(init=False)

    # Optional fields
    balance: Decimal | None = None
    category: str | None = None
    envelope: str | None = None
    external_account_name: str | None = None
    status: TransactionStatus = TransactionStatus.PENDING
    notes: str | None = None
    # Filled from corpus/state/annotations.csv and category_rules.csv, never from the statement itself.
    review_status: str = ""
    need_want: str = ""
    frequency: str = ""
    splitwise: bool = False
    raw_data: dict | None = None

    # Metadata
    created_at: str | None = None

    def __post_init__(self):
        """Generate unique hash for deduplication.

        All whitespace is stripped from the narration first: banks re-wrap the same narration
        differently between statement runs (SBI shifts the line break by a character, splitting
        the text in a different place), and a transaction reported in two overlapping statements
        must still hash the same.
        """
        unique_str = (
            f"{self.transaction_date}{self.amount}{self.narration_key}{self.transaction_type.value}{self.source_bank}"
        )
        if self.balance:
            unique_str += str(self.balance)
        self.hash = hashlib.sha256(unique_str.encode()).hexdigest()[:16]

    @property
    def narration_key(self) -> str:
        """The description with all whitespace removed: the form used to compare narrations across statements."""
        return "".join(self.description.split())

    @property
    def payment_mode(self) -> str:
        return payment_mode(self.description)

    @property
    def counterparty(self) -> str:
        return counterparty(self.description)

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
            "Status": "cleared",
        }
