"""Processing report tests."""

from datetime import date
from decimal import Decimal
import json

from src.exporters.report import generate_report
from src.models.result import ProcessingResult
from src.models.transactions import Transaction, TransactionStatus, TransactionType


def test_generate_report_uses_actual_exported_transaction_count(tmp_path):
    transfer = Transaction(
        transaction_date=date(2025, 1, 5),
        description="Transfer to SBI",
        amount=Decimal("500.00"),
        transaction_type=TransactionType.DEBIT,
        source_bank="HDFC",
        source_file="sample.xls",
        status=TransactionStatus.TRANSFER,
    )
    result = ProcessingResult(
        source_file="sample.xls",
        bank="HDFC",
        total_transactions=1,
        successful=1,
        failed=0,
        duplicates_skipped=0,
        transactions=[transfer],
        errors=[],
        warnings=[],
    )

    report_path = tmp_path / "report.json"
    report = generate_report([result], str(report_path), exported_transactions=0)
    written_report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["summary"]["exported_transactions"] == 0
    assert written_report["summary"]["exported_transactions"] == 0
    assert written_report["summary"]["transfers_detected"] == 1
