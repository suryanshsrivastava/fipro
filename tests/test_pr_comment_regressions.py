from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import gspread
import pytest

from src.core import orchestrator
from src.core.deduplicator import save_seen_hashes_to_file
from src.exporters.goodbudget import export_to_goodbudget
from src.exporters.sheets import export_to_google_sheets
from src.models.transactions import Transaction, TransactionType
from src.ui import dashboard


class DummyParser:
    bank_name = "TEST"

    def __init__(self, transactions: list[Transaction]):
        self._transactions = transactions

    def extract_transactions(self, _df, _source_file: str) -> list[Transaction]:
        return list(self._transactions)


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
        {"export": {"goodbudget": {"default_envelope": "Unallocated", "default_status": "cleared"}}},
    )

    with output_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["Date", "Envelope", "Account", "Name", "Notes", "Amount", "Status"]
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["Name"] == transaction.description
    assert rows[0]["Amount"] == str(transaction.signed_amount)


def test_save_seen_hashes_to_file_creates_parent_directory(tmp_path: Path):
    target = tmp_path / "nested" / "seen_hashes.txt"

    save_seen_hashes_to_file({"abc123", "def456"}, str(target))

    assert target.exists()
    assert target.read_text().splitlines() == ["abc123", "def456"]


def test_move_file_to_processed_avoids_overwriting_existing_archive(tmp_path: Path):
    source = tmp_path / "input" / "hdfc.xls"
    source.parent.mkdir(parents=True)
    source.write_text("new statement")
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    existing = processed_dir / "hdfc.xls"
    existing.write_text("old statement")

    dest = orchestrator.move_file_to_processed(str(source), str(processed_dir))

    assert dest == str(processed_dir / "hdfc_1.xls")
    assert not source.exists()
    assert existing.read_text() == "old statement"
    assert Path(dest).read_text() == "new statement"


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
    monkeypatch.setattr(orchestrator, "load_statement_dataframe", lambda _path: None)
    monkeypatch.setattr(orchestrator, "route_file_to_parser", lambda *_args: parser)
    monkeypatch.setattr(orchestrator, "get_seen_hashes_from_file", lambda _path: set())
    monkeypatch.setattr(orchestrator, "save_seen_hashes_to_file", lambda *_args: None)
    monkeypatch.setattr(orchestrator, "move_file_to_processed", lambda *_args: None)
    monkeypatch.setattr(orchestrator, "generate_report", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        orchestrator,
        "export_to_goodbudget",
        lambda transactions, *_args: exported.setdefault("transactions", list(transactions)),
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

    orchestrator.process_pipeline(config)

    assert exported["transactions"] == []


def test_process_pipeline_moves_files_only_after_successful_export(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    transaction = make_transaction(source_file="statement.xls")
    parser = DummyParser([transaction])
    crawled = [SimpleNamespace(filepath="statement.xls", filename="statement.xls", metadata={})]
    processed_moves: list[str] = []

    monkeypatch.setattr(orchestrator, "discover_files", lambda _config: crawled)
    monkeypatch.setattr(orchestrator, "load_statement_dataframe", lambda _path: None)
    monkeypatch.setattr(orchestrator, "route_file_to_parser", lambda *_args: parser)
    monkeypatch.setattr(orchestrator, "get_seen_hashes_from_file", lambda _path: set())
    monkeypatch.setattr(orchestrator, "save_seen_hashes_to_file", lambda *_args: None)
    monkeypatch.setattr(orchestrator, "move_file_to_processed", lambda source, *_args: processed_moves.append(source))
    monkeypatch.setattr(orchestrator, "generate_report", lambda *_args, **_kwargs: {})

    def fail_export(*_args, **_kwargs):
        raise RuntimeError("export failed")

    monkeypatch.setattr(orchestrator, "export_to_goodbudget", fail_export)

    config = {
        "paths": {
            "input": str(tmp_path / "input"),
            "output": str(tmp_path / "output"),
            "processed": str(tmp_path / "processed"),
            "failed": str(tmp_path / "failed"),
        },
        "processing": {"skip_internal_transfers": False},
        "export": {"goodbudget": {}},
    }

    with pytest.raises(RuntimeError, match="export failed"):
        orchestrator.process_pipeline(config)

    assert processed_moves == []


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
