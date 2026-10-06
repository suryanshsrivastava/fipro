"""Password-protected statements and bank detection from folder names."""

from __future__ import annotations

from pathlib import Path

import pytest
from msoffcrypto.format.ooxml import OOXMLFile
from openpyxl import Workbook

from src.core.ingestion import get_bank_from_path
from src.core.orchestrator import load_statement_dataframe, process_pipeline
from src.parsers.sbi import SBIParser

SBI_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "parsers" / "sbi" / "raw_monthly_export" / "input.xls"
PASSWORD = "test-password"


def _write_encrypted_sbi_xlsx(dest: Path) -> None:
    """Rebuild the SBI fixture (tab-separated text) as an .xlsx, preamble included, then password-protect it."""
    workbook = Workbook()
    sheet = workbook.active
    for line in SBI_FIXTURE.read_text(encoding="utf-8").splitlines():
        sheet.append([cell.strip() for cell in line.split("\t")])
    plain = dest.with_name("plain.xlsx")
    workbook.save(plain)
    with plain.open("rb") as src, dest.open("wb") as out:
        OOXMLFile(src).encrypt(PASSWORD, out)
    plain.unlink()


def _config(tmp_path: Path) -> dict:
    return {
        "paths": {
            "input": str(tmp_path / "input"),
            "output": str(tmp_path / "output"),
            "processed": str(tmp_path / "processed"),
            "failed": str(tmp_path / "failed"),
        },
        "processing": {
            "supported_extensions": ["xls", "xlsx"],
            "seen_hashes_path": str(tmp_path / ".seen_hashes"),
        },
    }


@pytest.fixture
def encrypted_statement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for var in ("FIPRO_SBI_STATEMENT_PASSWORD", "FIPRO_STATEMENT_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    # Mirrors real SBI downloads: no bank in the filename, only in the parent folder.
    statement = tmp_path / "input" / "2026-07-15" / "SBI" / "AccountStatement_15072026_004021.xlsx"
    statement.parent.mkdir(parents=True)
    _write_encrypted_sbi_xlsx(statement)
    return statement


@pytest.mark.parametrize(
    ("relative_path", "expected"),
    [
        ("current_finance_data/2026-07-15/SBI/AccountStatement_1.xlsx", "SBI"),
        ("Axis/statement.xls", "AXIS"),
        ("hdfc_2025.xls", "HDFC"),
        ("SBI/hdfc_export.xls", "HDFC"),
        ("misc/statement.xlsx", "UNKNOWN"),
    ],
)
def test_get_bank_from_path_prefers_filename_then_nearest_folder(relative_path, expected):
    assert get_bank_from_path(relative_path) == expected


@pytest.mark.parametrize("env_var", ["FIPRO_SBI_STATEMENT_PASSWORD", "FIPRO_STATEMENT_PASSWORD"])
def test_process_pipeline_decrypts_statement_in_bank_folder(tmp_path, monkeypatch, encrypted_statement, env_var):
    monkeypatch.setenv(env_var, PASSWORD)
    expected = SBIParser().extract_transactions(
        load_statement_dataframe(str(SBI_FIXTURE), bank="SBI"), str(SBI_FIXTURE)
    )

    run = process_pipeline(_config(tmp_path))

    [result] = run.results
    assert result.bank == "SBI"
    assert result.errors == []
    assert result.total_transactions == len(expected) > 0
    assert [(t.transaction_date, t.amount, t.transaction_type) for t in run.deduplicated_transactions] == [
        (t.transaction_date, t.amount, t.transaction_type) for t in expected
    ]
    assert (tmp_path / "processed" / encrypted_statement.name).exists()


def test_process_pipeline_fails_encrypted_statement_without_password(tmp_path, encrypted_statement):
    run = process_pipeline(_config(tmp_path))

    [result] = run.results
    assert "set FIPRO_SBI_STATEMENT_PASSWORD or FIPRO_STATEMENT_PASSWORD" in result.errors[0]
    assert (tmp_path / "failed" / encrypted_statement.name).exists()


def test_process_pipeline_reports_wrong_password_without_leaking_it(tmp_path, monkeypatch, encrypted_statement):
    monkeypatch.setenv("FIPRO_SBI_STATEMENT_PASSWORD", "not-the-password")

    run = process_pipeline(_config(tmp_path))

    [result] = run.results
    assert result.errors == [
        f"Could not decrypt {encrypted_statement.name}: wrong password in FIPRO_SBI_STATEMENT_PASSWORD"
    ]
    error_log = tmp_path / "failed" / f"{encrypted_statement.name}.error.txt"
    assert "not-the-password" not in error_log.read_text()
