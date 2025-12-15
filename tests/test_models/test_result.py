"""Unit tests for ProcessingResult model."""

from datetime import date
from decimal import Decimal

import pytest

from src.models.result import ProcessingResult
from src.models.transactions import Transaction, TransactionType


class TestProcessingResult:
    @pytest.fixture
    def sample_transactions(self):
        return [
            Transaction(
                transaction_date=date(2025, 1, 15),
                description="Swiggy Order",
                amount=Decimal("450.00"),
                transaction_type=TransactionType.DEBIT,
                source_bank="HDFC",
                source_file="/data/input/hdfc_jan.xls",
            ),
            Transaction(
                transaction_date=date(2025, 1, 16),
                description="Salary Credit",
                amount=Decimal("150000.00"),
                transaction_type=TransactionType.CREDIT,
                source_bank="HDFC",
                source_file="/data/input/hdfc_jan.xls",
            ),
        ]

    @pytest.fixture
    def successful_result(self, sample_transactions):
        return ProcessingResult(
            source_file="/data/input/hdfc_jan.xls",
            bank="HDFC",
            total_transactions=2,
            successful=2,
            failed=0,
            duplicates_skipped=0,
            transactions=sample_transactions,
            errors=[],
            warnings=[],
        )

    def test_all_fields_populated(self, successful_result, sample_transactions):
        assert successful_result.source_file == "/data/input/hdfc_jan.xls"
        assert successful_result.bank == "HDFC"
        assert successful_result.total_transactions == 2
        assert successful_result.successful == 2
        assert successful_result.failed == 0
        assert successful_result.duplicates_skipped == 0
        assert successful_result.transactions == sample_transactions
        assert successful_result.errors == []
        assert successful_result.warnings == []

    def test_result_with_errors(self):
        result = ProcessingResult(
            source_file="/data/input/bad_file.xls",
            bank="SBI",
            total_transactions=10,
            successful=7,
            failed=3,
            duplicates_skipped=0,
            transactions=[],
            errors=["Row 5: Invalid date format", "Row 8: Missing amount"],
            warnings=["Row 2: Unusual amount detected"],
        )
        assert result.failed == 3
        assert len(result.errors) == 2
        assert len(result.warnings) == 1

    def test_result_with_duplicates(self, sample_transactions):
        result = ProcessingResult(
            source_file="/data/input/hdfc_jan.xls",
            bank="HDFC",
            total_transactions=5,
            successful=2,
            failed=0,
            duplicates_skipped=3,
            transactions=sample_transactions,
            errors=[],
            warnings=[],
        )
        assert result.duplicates_skipped == 3
        assert result.total_transactions == 5
        assert len(result.transactions) == 2

    def test_empty_result(self):
        result = ProcessingResult(
            source_file="/data/input/empty.xls",
            bank="AXIS",
            total_transactions=0,
            successful=0,
            failed=0,
            duplicates_skipped=0,
            transactions=[],
            errors=[],
            warnings=["File contains no transactions"],
        )
        assert result.total_transactions == 0
        assert len(result.transactions) == 0

    def test_result_transactions_are_accessible(self, successful_result):
        assert len(successful_result.transactions) == 2
        assert successful_result.transactions[0].description == "Swiggy Order"
        assert successful_result.transactions[1].amount == Decimal("150000.00")
