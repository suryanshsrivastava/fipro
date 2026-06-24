from datetime import date
from decimal import Decimal

from src.exporters.report import summarize_pipeline_run
from src.models.result import HubSummary, PipelineRun, ProcessingResult
from src.models.transactions import Transaction, TransactionType


def _transaction() -> Transaction:
    return Transaction(
        transaction_date=date(2026, 1, 1),
        description="Test txn",
        amount=Decimal("100.00"),
        transaction_type=TransactionType.DEBIT,
        source_bank="HDFC",
        source_file="hdfc.xls",
    )


def _run_with_results() -> PipelineRun:
    result = ProcessingResult(
        source_file="hdfc.xls",
        bank="HDFC",
        total_transactions=2,
        successful=1,
        failed=0,
        duplicates_skipped=1,
        transactions=[_transaction()],
        errors=["row parse warning"],
        warnings=[],
    )
    return PipelineRun(
        results=[result],
        deduplicated_transactions=[_transaction()],
        goodbudget_csv_path="data/output/goodbudget_export.csv",
        report_json_path="data/output/processing_report.json",
        hub_csv_path="data/output/hub_summary.csv",
        hub_summary=HubSummary(
            earliest="2026-01-01",
            latest="2026-01-31",
            cash_flow={"net_cash_flow": "123.45"},
            total_across_statements="999.99",
            reason_if_no_total=None,
        ),
    )


def test_summarize_pipeline_run_for_empty_inputs():
    run = PipelineRun(
        results=[],
        deduplicated_transactions=[],
        goodbudget_csv_path="",
        report_json_path="",
        hub_csv_path="",
        hub_summary=HubSummary.empty(),
    )

    assert summarize_pipeline_run(run) == ["No input files found."]


def test_summarize_pipeline_run_includes_operational_lines():
    lines = summarize_pipeline_run(_run_with_results())

    assert lines == [
        "Processed 1 file(s): 2 parsed, 1 exported after dedup, 1 error(s).",
        "Statement window: 2026-01-01 to 2026-01-31",
        "Net cash flow (export scope): 123.45",
        "Statement balances sum (not net worth): 999.99",
    ]
