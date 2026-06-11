"""Unit tests for Transaction model."""

from datetime import date
from decimal import Decimal

import pytest

from src.models.transactions import Transaction, TransactionStatus, TransactionType


class TestTransactionType:
    def test_debit_value(self):
        assert TransactionType.DEBIT.value == "debit"

    def test_credit_value(self):
        assert TransactionType.CREDIT.value == "credit"


class TestTransactionStatus:
    def test_all_statuses(self):
        assert TransactionStatus.PENDING.value == "pending"
        assert TransactionStatus.UNCLEARED.value == "uncleared"
        assert TransactionStatus.CLEARED.value == "cleared"
        assert TransactionStatus.TRANSFER.value == "internal_transfer"


class TestTransaction:
    @pytest.fixture
    def debit_transaction(self):
        return Transaction(
            transaction_date=date(2025, 1, 15),
            description="Swiggy Order",
            amount=Decimal("450.00"),
            transaction_type=TransactionType.DEBIT,
            source_bank="HDFC",
            source_file="/data/input/hdfc_jan.xls",
        )

    @pytest.fixture
    def credit_transaction(self):
        return Transaction(
            transaction_date=date(2025, 1, 16),
            description="Salary Credit",
            amount=Decimal("150000.00"),
            transaction_type=TransactionType.CREDIT,
            source_bank="AXIS",
            source_file="/data/input/axis_jan.xlsx",
        )

    def test_required_fields(self, debit_transaction):
        assert debit_transaction.transaction_date == date(2025, 1, 15)
        assert debit_transaction.description == "Swiggy Order"
        assert debit_transaction.amount == Decimal("450.00")
        assert debit_transaction.transaction_type == TransactionType.DEBIT
        assert debit_transaction.source_bank == "HDFC"
        assert debit_transaction.source_file == "/data/input/hdfc_jan.xls"

    def test_hash_generation(self, debit_transaction):
        assert debit_transaction.hash is not None
        assert len(debit_transaction.hash) == 16

    def test_hash_uniqueness(self, debit_transaction, credit_transaction):
        assert debit_transaction.hash != credit_transaction.hash

    def test_hash_with_balance(self):
        txn_without_balance = Transaction(
            transaction_date=date(2025, 1, 15),
            description="Test",
            amount=Decimal("100"),
            transaction_type=TransactionType.DEBIT,
            source_bank="HDFC",
            source_file="test.xls",
        )
        txn_with_balance = Transaction(
            transaction_date=date(2025, 1, 15),
            description="Test",
            amount=Decimal("100"),
            transaction_type=TransactionType.DEBIT,
            source_bank="HDFC",
            source_file="test.xls",
            balance=Decimal("5000"),
        )
        assert txn_without_balance.hash != txn_with_balance.hash

    def test_default_values(self, debit_transaction):
        assert debit_transaction.id is None
        assert debit_transaction.balance is None
        assert debit_transaction.category is None
        assert debit_transaction.envelope is None
        assert debit_transaction.status == TransactionStatus.PENDING
        assert debit_transaction.notes is None
        assert debit_transaction.raw_data is None
        assert debit_transaction.created_at is None

    def test_signed_amount_debit(self, debit_transaction):
        assert debit_transaction.signed_amount == Decimal("-450.00")

    def test_signed_amount_credit(self, credit_transaction):
        assert credit_transaction.signed_amount == Decimal("150000.00")

    def test_signed_amount_handles_negative_input(self):
        txn = Transaction(
            transaction_date=date(2025, 1, 15),
            description="Test",
            amount=Decimal("-100"),
            transaction_type=TransactionType.DEBIT,
            source_bank="HDFC",
            source_file="test.xls",
        )
        assert txn.signed_amount == Decimal("-100")

    def test_to_goodbudget_row_debit(self, debit_transaction):
        row = debit_transaction.to_goodbudget_row()
        assert row["Date"] == "2025-01-15"
        assert row["Envelope"] == "Unallocated"
        assert row["Account"] == "HDFC"
        assert row["Name"] == "Swiggy Order"
        assert row["Notes"] == ""
        assert row["Amount"] == "-450.00"
        assert row["Status"] == "cleared"

    def test_to_goodbudget_row_credit(self, credit_transaction):
        row = credit_transaction.to_goodbudget_row()
        assert row["Amount"] == "150000.00"

    def test_to_goodbudget_row_with_envelope(self, debit_transaction):
        debit_transaction.envelope = "Food"
        row = debit_transaction.to_goodbudget_row()
        assert row["Envelope"] == "Food"

    def test_to_goodbudget_row_with_notes(self, debit_transaction):
        debit_transaction.notes = "Weekly groceries"
        row = debit_transaction.to_goodbudget_row()
        assert row["Notes"] == "Weekly groceries"

    def test_to_goodbudget_row_truncates_long_description(self):
        long_desc = "A" * 100
        txn = Transaction(
            transaction_date=date(2025, 1, 15),
            description=long_desc,
            amount=Decimal("100"),
            transaction_type=TransactionType.DEBIT,
            source_bank="HDFC",
            source_file="test.xls",
        )
        row = txn.to_goodbudget_row()
        assert len(row["Name"]) == 50

    def test_optional_fields_can_be_set(self):
        txn = Transaction(
            transaction_date=date(2025, 1, 15),
            description="Test",
            amount=Decimal("100"),
            transaction_type=TransactionType.DEBIT,
            source_bank="HDFC",
            source_file="test.xls",
            id=1,
            balance=Decimal("5000"),
            category="Food",
            envelope="Groceries",
            status=TransactionStatus.CLEARED,
            notes="Test note",
            raw_data={"col1": "val1"},
            created_at="2025-01-15T10:00:00",
        )
        assert txn.id == 1
        assert txn.balance == Decimal("5000")
        assert txn.category == "Food"
        assert txn.envelope == "Groceries"
        assert txn.status == TransactionStatus.CLEARED
        assert txn.notes == "Test note"
        assert txn.raw_data == {"col1": "val1"}
        assert txn.created_at == "2025-01-15T10:00:00"

    def test_hash_deterministic(self):
        txn1 = Transaction(
            transaction_date=date(2025, 1, 15),
            description="Test",
            amount=Decimal("100"),
            transaction_type=TransactionType.DEBIT,
            source_bank="HDFC",
            source_file="test.xls",
        )
        txn2 = Transaction(
            transaction_date=date(2025, 1, 15),
            description="Test",
            amount=Decimal("100"),
            transaction_type=TransactionType.DEBIT,
            source_bank="HDFC",
            source_file="test.xls",
        )
        assert txn1.hash == txn2.hash

    def test_hash_differs_for_same_description_different_bank(self):
        hdfc = Transaction(
            transaction_date=date(2025, 1, 15),
            description="UPI-SWIGGY",
            amount=Decimal("450.00"),
            transaction_type=TransactionType.DEBIT,
            source_bank="HDFC",
            source_file="hdfc.xls",
        )
        sbi = Transaction(
            transaction_date=date(2025, 1, 15),
            description="UPI-SWIGGY",
            amount=Decimal("450.00"),
            transaction_type=TransactionType.CREDIT,
            source_bank="SBI",
            source_file="sbi.xls",
        )
        assert hdfc.hash != sbi.hash
