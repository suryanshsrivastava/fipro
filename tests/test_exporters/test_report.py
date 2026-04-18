"""Processing report tests."""

import json
from datetime import date
from decimal import Decimal

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


def test_cash_flow_excludes_transfers_when_config_says_so(tmp_path):
    transfer = Transaction(
        transaction_date=date(2025, 1, 5),
        description="Transfer to SBI",
        amount=Decimal("500.00"),
        transaction_type=TransactionType.DEBIT,
        source_bank="HDFC",
        source_file="sample.xls",
        status=TransactionStatus.TRANSFER,
    )
    debit = Transaction(
        transaction_date=date(2025, 1, 6),
        description="Coffee",
        amount=Decimal("100.00"),
        transaction_type=TransactionType.DEBIT,
        source_bank="HDFC",
        source_file="sample.xls",
    )
    result = ProcessingResult(
        source_file="sample.xls",
        bank="HDFC",
        total_transactions=2,
        successful=2,
        failed=0,
        duplicates_skipped=0,
        transactions=[transfer, debit],
        errors=[],
        warnings=[],
    )
    report_path = tmp_path / "report.json"
    report = generate_report(
        [result],
        str(report_path),
        config={"processing": {"include_internal_transfers": False}},
    )
    assert report["cash_flow"]["total_debits"] == "100.00"
    assert report["cash_flow"]["total_credits"] == "0"
    assert report["cash_flow"]["net_cash_flow"] == "-100.00"


def test_net_worth_proxy_null_when_balances_missing(tmp_path):
    debit = Transaction(
        transaction_date=date(2025, 1, 6),
        description="Coffee",
        amount=Decimal("100.00"),
        transaction_type=TransactionType.DEBIT,
        source_bank="HDFC",
        source_file="/data/a.xls",
        balance=None,
    )
    result = ProcessingResult(
        source_file="/data/a.xls",
        bank="HDFC",
        total_transactions=1,
        successful=1,
        failed=0,
        duplicates_skipped=0,
        transactions=[debit],
        errors=[],
        warnings=[],
    )
    report_path = tmp_path / "report.json"
    report = generate_report([result], str(report_path))
    assert report["net_worth_proxy"]["total_across_statements"] is None
    assert report["net_worth_proxy"]["reason_if_no_total"] == (
        "missing_balance_on_one_or_more_statements_not_a_full_net_worth_view"
    )


def test_top_descriptions_counts_normalized_strings(tmp_path):
    t1 = Transaction(
        transaction_date=date(2025, 1, 1),
        description="  SWIGGY  ORDER  ",
        amount=Decimal("50.00"),
        transaction_type=TransactionType.DEBIT,
        source_bank="HDFC",
        source_file="a.xls",
    )
    t2 = Transaction(
        transaction_date=date(2025, 1, 2),
        description="SWIGGY ORDER",
        amount=Decimal("60.00"),
        transaction_type=TransactionType.DEBIT,
        source_bank="HDFC",
        source_file="a.xls",
    )
    result = ProcessingResult(
        source_file="a.xls",
        bank="HDFC",
        total_transactions=2,
        successful=2,
        failed=0,
        duplicates_skipped=0,
        transactions=[t1, t2],
        errors=[],
        warnings=[],
    )
    report_path = tmp_path / "report.json"
    report = generate_report([result], str(report_path))
    assert report["top_descriptions"][0]["description"] == "SWIGGY ORDER"
    assert report["top_descriptions"][0]["count"] == 2
