from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import gspread
import pytest

from src.config import GoodbudgetSettings, Settings
from src.core import orchestrator
from src.core.parser_registry import ExtractedStatement
from src.exporters.goodbudget import export_to_goodbudget
from src.exporters.sheets import export_to_google_sheets
from src.models.result import HubSummary
from src.models.transactions import Transaction, TransactionType
from src.ui import dashboard


def _mock_generate_report(_results, output_path, **_kwargs):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    return {}, HubSummary.empty()


class DummyParser:
    bank_name = "TEST"

    def __init__(self, transactions: list[Transaction]):
        self._transactions = transactions

    def extract_transactions(self, _df, _source_file: str) -> list[Transaction]:
        return list(self._transactions)


def _mock_parser_registry(monkeypatch: pytest.MonkeyPatch, parser: DummyParser) -> None:
    class FakeRegistry:
        def extract_transactions(self, filepath, **_kwargs):
            return ExtractedStatement(
                parser=parser, dataframe=None, transactions=parser.extract_transactions(None, filepath)
            )

    monkeypatch.setattr(orchestrator, "get_default_parser_registry", lambda: FakeRegistry())


def make_transaction(
    *,
    txn_date: date = date(2025, 8, 1),
    description: str = "Sample transaction",
    amount: str = "100.00",
    transaction_type: TransactionType = TransactionType.DEBIT,
    source_bank: str = "HDFC",
    source_file: str = "statement.xls",
) -> Transaction:
    return Transaction(
        transaction_date=txn_date,
        description=description,
        amount=Decimal(amount),
        transaction_type=transaction_type,
        source_bank=source_bank,
        source_file=source_file,
    )


def test_goodbudget_export_keeps_only_goodbudget_columns(tmp_path: Path):
    output_path = tmp_path / "goodbudget_export.csv"
    transaction = make_transaction()

    export_to_goodbudget(
        [transaction],
        str(output_path),
        GoodbudgetSettings(default_envelope="Unallocated", default_status="cleared"),
    )

    with output_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["Date", "Envelope", "Account", "Name", "Notes", "Amount", "Status"]
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["Name"] == transaction.description
    assert rows[0]["Amount"] == str(transaction.signed_amount)


def test_serve_dashboard_does_not_open_browser_without_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    csv_path = tmp_path / "dashboard.csv"
    csv_path.write_text("Date,Envelope,Account,Name,Notes,Amount,Status\n")

    opened_urls: list[str] = []

    class FakeHTTPServer:
        def __init__(self, *_args, **_kwargs):
            pass

        def serve_forever(self):
            return None

    monkeypatch.setattr(dashboard, "HTTPServer", FakeHTTPServer)
    monkeypatch.setattr(dashboard.webbrowser, "open", opened_urls.append)

    dashboard.serve_dashboard(str(csv_path), port=9090, open_browser=False)

    assert opened_urls == []


def test_load_csv_data_treats_invalid_amount_as_zero(tmp_path: Path):
    csv_path = tmp_path / "dashboard.csv"
    csv_path.write_text(
        "Date,Envelope,Account,Name,Notes,Amount,Status\n2025-01-15,Unallocated,HDFC,Test,,N/A,cleared\n"
    )

    rows = dashboard.load_csv_data(str(csv_path))

    assert len(rows) == 1
    assert rows[0]["amount"] == "N/A"
    assert rows[0]["transaction_type"] == "credit"


def test_process_pipeline_skips_internal_transfers_from_export(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    debit = make_transaction(
        txn_date=date(2025, 8, 2),
        description="Transfer out",
        amount="500.00",
        transaction_type=TransactionType.DEBIT,
        source_bank="HDFC",
        source_file="one.xls",
    )
    credit = make_transaction(
        txn_date=date(2025, 8, 2),
        description="Transfer in",
        amount="500.00",
        transaction_type=TransactionType.CREDIT,
        source_bank="SBI",
        source_file="two.xls",
    )
    parser = DummyParser([debit, credit])
    crawled = [
        SimpleNamespace(filepath="one.xls", filename="one.xls", metadata={}),
        SimpleNamespace(filepath="two.xls", filename="two.xls", metadata={}),
    ]
    exported: dict[str, list[Transaction]] = {}

    monkeypatch.setattr(orchestrator, "discover_files", lambda _config: crawled)
    _mock_parser_registry(monkeypatch, parser)
    monkeypatch.setattr(orchestrator, "generate_report", _mock_generate_report)

    def capture_goodbudget(transactions, csv_path, *_args, **_kwargs):
        exported.setdefault("transactions", list(transactions))
        path = Path(csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Date\n", encoding="utf-8")

    monkeypatch.setattr(
        orchestrator,
        "export_to_goodbudget",
        capture_goodbudget,
    )

    config = {
        "paths": {
            "input": str(tmp_path / "input"),
            "output": str(tmp_path / "output"),
            "processed": str(tmp_path / "processed"),
            "failed": str(tmp_path / "failed"),
        },
        "processing": {"skip_internal_transfers": True},
        "export": {"goodbudget": {}},
    }

    orchestrator.process_pipeline(Settings.from_config(config))

    assert exported["transactions"] == []


def test_process_pipeline_leaves_statements_in_place_when_export_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    transaction = make_transaction(source_file="statement.xls")
    parser = DummyParser([transaction])
    crawled = [SimpleNamespace(filepath="statement.xls", filename="statement.xls", metadata={})]

    monkeypatch.setattr(orchestrator, "discover_files", lambda _config: crawled)
    _mock_parser_registry(monkeypatch, parser)
    monkeypatch.setattr(orchestrator, "generate_report", _mock_generate_report)

    def fail_export(*_args, **_kwargs):
        raise RuntimeError("export failed")

    monkeypatch.setattr(orchestrator, "export_to_goodbudget", fail_export)

    config = {
        "paths": {"input": str(tmp_path / "input"), "output": str(tmp_path / "output")},
        "processing": {"skip_internal_transfers": False},
        "export": {"goodbudget": {}},
    }

    with pytest.raises(RuntimeError, match="export failed"):
        orchestrator.process_pipeline(Settings.from_config(config))

    output_dir = tmp_path / "output"
    assert not output_dir.exists() or not list(output_dir.glob("goodbudget_export.csv"))


def test_export_to_google_sheets_uses_batch_update_request_body(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    csv_path = tmp_path / "goodbudget.csv"
    csv_path.write_text(
        "Date,Envelope,Account,Name,Notes,Amount,Status\n2025-08-01,Unallocated,HDFC,Groceries,, -100.00,cleared\n"
    )
    id_path = tmp_path / "sheet_id.txt"

    recorded_requests: list[object] = []
    created_titles: list[str] = []

    class FakeWorksheet:
        row_count = 2

        def update(self, *_args, **_kwargs):
            return None

        def append_rows(self, *_args, **_kwargs):
            return None

        def format(self, *_args, **_kwargs):
            return None

        def batch_clear(self, *_args, **_kwargs):
            return None

    class FakeSpreadsheet:
        def __init__(self):
            self.sheet1 = FakeWorksheet()
            self.id = "sheet-abc"
            self.url = "https://example.test/sheet"

        def batch_update(self, request_body):
            recorded_requests.append(request_body)

    class FakeClient:
        def open(self, title: str):
            if title == "Test":
                return FakeSpreadsheet()
            raise gspread.SpreadsheetNotFound

        def create(self, title: str):
            created_titles.append(title)
            return FakeSpreadsheet()

    monkeypatch.setattr(
        "src.exporters.sheets.gspread.service_account",
        lambda **_kwargs: FakeClient(),
    )

    export_to_google_sheets(
        str(csv_path),
        credentials_path=str(tmp_path / "creds.json"),
        spreadsheet_title="Test",
        spreadsheet_id_path=str(id_path),
    )

    assert created_titles == []
    assert id_path.read_text(encoding="utf-8") == "sheet-abc"
    assert recorded_requests == [
        {
            "requests": [
                {"autoResizeDimensions": {"dimensions": {"dimension": "COLUMNS", "startIndex": 0, "endIndex": 7}}}
            ]
        }
    ]


def test_export_to_google_sheets_reuses_existing_spreadsheet_by_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    csv_path = tmp_path / "goodbudget.csv"
    csv_path.write_text(
        "Date,Envelope,Account,Name,Notes,Amount,Status\n2025-08-01,Unallocated,HDFC,Groceries,, -100.00,cleared\n"
    )
    id_path = tmp_path / "sheet_id.txt"
    id_path.write_text("existing-sheet-id", encoding="utf-8")

    created_titles: list[str] = []
    opened_keys: list[str] = []
    cleared_ranges: list[str] = []

    class FakeWorksheet:
        row_count = 5

        def update(self, *_args, **_kwargs):
            return None

        def append_rows(self, *_args, **_kwargs):
            return None

        def format(self, *_args, **_kwargs):
            return None

        def batch_clear(self, ranges):
            cleared_ranges.extend(ranges)

    class FakeSpreadsheet:
        def __init__(self):
            self.sheet1 = FakeWorksheet()
            self.id = "existing-sheet-id"
            self.url = "https://example.test/existing"

        def batch_update(self, _request_body):
            return None

    class FakeClient:
        def open_by_key(self, key: str):
            opened_keys.append(key)
            if key == "existing-sheet-id":
                return FakeSpreadsheet()
            raise gspread.SpreadsheetNotFound

        def open(self, title: str):
            raise AssertionError(f"should not open by title, got {title}")

        def create(self, title: str):
            created_titles.append(title)
            return FakeSpreadsheet()

    monkeypatch.setattr(
        "src.exporters.sheets.gspread.service_account",
        lambda **_kwargs: FakeClient(),
    )

    export_to_google_sheets(
        str(csv_path),
        credentials_path=str(tmp_path / "creds.json"),
        spreadsheet_id_path=str(id_path),
    )

    assert created_titles == []
    assert opened_keys == ["existing-sheet-id"]
    assert cleared_ranges == ["A3:G5"]


def test_export_to_google_sheets_creates_new_when_stored_id_is_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    csv_path = tmp_path / "goodbudget.csv"
    csv_path.write_text(
        "Date,Envelope,Account,Name,Notes,Amount,Status\n2025-08-01,Unallocated,HDFC,Groceries,, -100.00,cleared\n"
    )
    id_path = tmp_path / "sheet_id.txt"
    id_path.write_text("deleted-sheet-id", encoding="utf-8")

    created_titles: list[str] = []

    class FakeWorksheet:
        row_count = 2

        def update(self, *_args, **_kwargs):
            return None

        def append_rows(self, *_args, **_kwargs):
            return None

        def format(self, *_args, **_kwargs):
            return None

        def batch_clear(self, *_args, **_kwargs):
            return None

    class FakeSpreadsheet:
        def __init__(self):
            self.sheet1 = FakeWorksheet()
            self.id = "fresh-sheet-id"
            self.url = "https://example.test/fresh"

        def batch_update(self, _request_body):
            return None

    class FakeClient:
        def open_by_key(self, _key: str):
            raise gspread.SpreadsheetNotFound

        def open(self, title: str):
            raise AssertionError(f"should not open by title when id is stale, got {title}")

        def create(self, title: str):
            created_titles.append(title)
            return FakeSpreadsheet()

    monkeypatch.setattr(
        "src.exporters.sheets.gspread.service_account",
        lambda **_kwargs: FakeClient(),
    )

    export_to_google_sheets(
        str(csv_path),
        credentials_path=str(tmp_path / "creds.json"),
        spreadsheet_id_path=str(id_path),
    )

    assert created_titles == ["Fipro Transactions"]
    assert id_path.read_text(encoding="utf-8") == "fresh-sheet-id"


def test_process_pipeline_export_phase_leaves_no_artifacts_on_hub_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    transaction = make_transaction(source_file="statement.xls")
    parser = DummyParser([transaction])
    crawled = [SimpleNamespace(filepath="statement.xls", filename="statement.xls", metadata={})]
    output_dir = tmp_path / "output"

    monkeypatch.setattr(orchestrator, "discover_files", lambda _config: crawled)
    _mock_parser_registry(monkeypatch, parser)
    monkeypatch.setattr(orchestrator, "export_to_goodbudget", lambda *_args, **_kwargs: None)

    def fail_hub(*_args, **_kwargs):
        raise RuntimeError("hub export failed")

    monkeypatch.setattr(orchestrator, "export_hub_csv", fail_hub)

    config = {
        "paths": {"input": str(tmp_path / "input"), "output": str(output_dir)},
        "processing": {"skip_internal_transfers": False},
        "export": {"goodbudget": {}},
    }

    with pytest.raises(RuntimeError, match="hub export failed"):
        orchestrator.process_pipeline(Settings.from_config(config))

    assert not output_dir.exists() or not list(output_dir.glob("goodbudget_export.csv"))
    assert not output_dir.exists() or not list(output_dir.glob("hub_summary.csv"))
    assert not output_dir.exists() or not list(output_dir.glob("processing_report.json"))
    assert not output_dir.exists() or not list(output_dir.glob("dashboard_data.csv"))


def test_process_pipeline_rerun_reproduces_the_same_export(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Because input is re-read every run, a second run must export the same rows, not zero."""
    transaction = make_transaction(source_file="statement.xls")
    parser = DummyParser([transaction])
    crawled = [SimpleNamespace(filepath="statement.xls", filename="statement.xls", metadata={})]

    monkeypatch.setattr(orchestrator, "discover_files", lambda _config: crawled)
    _mock_parser_registry(monkeypatch, parser)
    monkeypatch.setattr(orchestrator, "generate_report", _mock_generate_report)

    config = {
        "paths": {"input": str(tmp_path / "input"), "output": str(tmp_path / "output")},
        "processing": {"skip_internal_transfers": False},
        "export": {"goodbudget": {}},
    }

    run1 = orchestrator.process_pipeline(Settings.from_config(config))
    assert run1.results[0].successful == 1
    assert run1.exported_count == 1

    run2 = orchestrator.process_pipeline(Settings.from_config(config))
    assert run2.results[0].successful == 1
    assert run2.exported_count == 1
    assert run2.results[0].duplicates_skipped == 0
