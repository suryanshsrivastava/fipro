import csv
import os
from datetime import date
from decimal import Decimal

from src.core.audit_log import AUDIT_LOG_NAME, write_audit_logs
from src.models.result import ProcessingResult
from src.models.transactions import Transaction, TransactionType


def _result(path, *dates):
    txns = [Transaction(d, "x", Decimal("1"), TransactionType.DEBIT, "SBI", str(path)) for d in dates]
    return ProcessingResult(str(path), "SBI", len(txns), len(txns), 0, 0, txns, [], [])


def _rows(folder):
    with (folder / AUDIT_LOG_NAME).open(newline="") as f:
        return list(csv.DictReader(f))


def test_audit_log_records_period_and_entries_and_keeps_created(tmp_path):
    stmt = tmp_path / "s.xlsx"
    stmt.write_bytes(b"x")
    os.utime(stmt, (1_700_000_000, 1_700_000_000))
    write_audit_logs([_result(stmt, date(2025, 3, 9), date(2025, 1, 2), date(2025, 2, 1))])
    (row,) = _rows(tmp_path)
    assert (row["period_start"], row["period_end"], row["entries"]) == ("2025-01-02", "2025-03-09", "3")
    assert row["date_created"] == row["date_modified"]

    os.utime(stmt, (1_800_000_000, 1_800_000_000))  # statement edited after first being logged
    write_audit_logs([_result(stmt, date(2025, 1, 2))])
    (row,) = _rows(tmp_path)
    assert row["date_created"] != row["date_modified"]
    assert row["entries"] == "1"


def test_audit_log_records_readable_statement_with_no_transactions(tmp_path):
    stmt = tmp_path / "empty.xlsx"
    stmt.write_bytes(b"x")
    write_audit_logs([_result(stmt)])
    (row,) = _rows(tmp_path)
    assert (row["entries"], row["period_start"], row["period_end"]) == ("0", "", "")


def test_audit_log_skips_failed_and_locked_statements(tmp_path):
    bad, locked = tmp_path / "bad.xlsx", tmp_path / "locked.xlsx"
    bad.write_bytes(b"x")
    locked.write_bytes(b"x")
    failed = ProcessingResult(str(bad), "SBI", 0, 0, 1, 0, [], ["boom"], [])
    pending = ProcessingResult(str(locked), "SBI", 0, 0, 0, 0, [], [], ["password-protected"])
    write_audit_logs([failed, pending])
    assert not (tmp_path / AUDIT_LOG_NAME).exists()


def test_audit_log_write_failure_does_not_raise(tmp_path):
    stmt = tmp_path / "s.xlsx"
    stmt.write_bytes(b"x")
    tmp_path.chmod(0o500)  # read-only folder: the audit can't be written
    try:
        write_audit_logs([_result(stmt, date(2025, 1, 2))])
    finally:
        tmp_path.chmod(0o700)
    assert not (tmp_path / AUDIT_LOG_NAME).exists()


def test_audit_log_with_unexpected_header_is_left_untouched(tmp_path):
    stmt = tmp_path / "s.xlsx"
    stmt.write_bytes(b"x")
    (tmp_path / AUDIT_LOG_NAME).write_text("name,rows\ns.xlsx,3\n")
    write_audit_logs([_result(stmt, date(2025, 1, 2))])
    assert (tmp_path / AUDIT_LOG_NAME).read_text() == "name,rows\ns.xlsx,3\n"
