"""Password-protected statements: bank detection from folders, decryption, and the dashboard unlock flow."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from msoffcrypto.format.ooxml import OOXMLFile
from openpyxl import Workbook

from src.connectors.gmail import PasswordHint, save_password_hints
from src.core.ingestion import get_bank_from_path
from src.core.orchestrator import load_statement_dataframe, process_pipeline
from src.exporters.report import summarize_pipeline_run
from src.parsers.sbi import SBIParser
from src.ui.dashboard import build_server

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


def test_process_pipeline_uses_password_passed_in_for_this_run(tmp_path, encrypted_statement):
    run = process_pipeline(_config(tmp_path), passwords={"SBI": PASSWORD})

    assert run.locked_files == []
    assert run.results[0].total_transactions > 0
    assert (tmp_path / "processed" / encrypted_statement.name).exists()


def test_locked_statement_stays_in_input_and_previous_exports_survive(tmp_path, encrypted_statement):
    previous_export = tmp_path / "output" / "dashboard_data.csv"
    previous_export.parent.mkdir()
    previous_export.write_text("previous run\n")

    run = process_pipeline(_config(tmp_path))

    assert run.locked_files == [str(encrypted_statement)]
    [result] = run.results
    assert result.errors == []
    assert "set FIPRO_SBI_STATEMENT_PASSWORD or FIPRO_STATEMENT_PASSWORD" in result.warnings[0]
    assert encrypted_statement.exists()
    assert not (tmp_path / "failed").exists()
    assert previous_export.read_text() == "previous run\n"
    assert "unlock them in `fipro dashboard`" in "\n".join(summarize_pipeline_run(run))


def test_wrong_password_keeps_file_locked_without_leaking_password(tmp_path, monkeypatch, encrypted_statement):
    monkeypatch.setenv("FIPRO_SBI_STATEMENT_PASSWORD", "not-the-password")

    run = process_pipeline(_config(tmp_path))

    [result] = run.results
    assert result.warnings == [
        f"Could not decrypt {encrypted_statement.name}: wrong password in FIPRO_SBI_STATEMENT_PASSWORD"
    ]
    assert run.locked_files == [str(encrypted_statement)]
    assert encrypted_statement.exists()


@pytest.fixture
def dashboard_url(tmp_path, encrypted_statement):
    config = _config(tmp_path) | {
        "paths": _config(tmp_path)["paths"] | {"password_hints": str(tmp_path / "hints.json")}
    }
    save_password_hints(
        [
            PasswordHint(
                "SBI", "Password is the last 5 digits of your mobile </script><b>", "Statement", "2026-07-15", "m1"
            )
        ],
        config["paths"]["password_hints"],
    )
    server = build_server(str(tmp_path / "output" / "dashboard_data.csv"), 0, config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _post(url: str, body: dict, headers: dict[str, str]) -> tuple[int, dict]:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_dashboard_shows_locked_statement_with_escaped_gmail_hint(dashboard_url, encrypted_statement):
    html = urllib.request.urlopen(dashboard_url).read().decode()

    assert encrypted_statement.name in html
    assert "last 5 digits of your mobile" in html
    assert "</script><b>" not in html


def test_dashboard_unlock_processes_statement_with_entered_password(dashboard_url, tmp_path, encrypted_statement):
    status, out = _post(
        f"{dashboard_url}/unlock", {"passwords": {"SBI": PASSWORD}}, {"Content-Type": "application/json"}
    )

    assert status == 200
    assert out["locked"] == []
    assert out["lines"][0].startswith("Processed 1 file(s)")
    assert (tmp_path / "processed" / encrypted_statement.name).exists()


@pytest.mark.parametrize(
    ("headers", "expected_status"),
    [
        ({"Content-Type": "text/plain"}, 415),
        ({"Content-Type": "application/json", "Origin": "http://evil.example"}, 403),
        ({"Content-Type": "application/json", "Host": "evil.example:8080"}, 403),
    ],
)
def test_dashboard_unlock_refuses_cross_site_requests(dashboard_url, encrypted_statement, headers, expected_status):
    status, _ = _post(f"{dashboard_url}/unlock", {"passwords": {"SBI": PASSWORD}}, headers)

    assert status == expected_status
    assert encrypted_statement.exists()


def test_decrypt_legacy_xls_does_not_pass_verify_password(tmp_path, monkeypatch):
    """Xls97File.load_key(password=None) has no verify_password parameter."""
    from src.core import orchestrator

    class FakeXls97File:
        def __init__(self, _file):
            pass

        def load_key(self, password=None):
            assert password == PASSWORD

        def decrypt(self, outfile):
            outfile.write(b"decrypted")

    statement = tmp_path / "SBI" / "old.xls"
    statement.parent.mkdir()
    statement.write_bytes(b"x")
    monkeypatch.setenv("FIPRO_SBI_STATEMENT_PASSWORD", PASSWORD)
    monkeypatch.setattr(orchestrator.msoffcrypto, "OfficeFile", FakeXls97File)

    assert orchestrator._decrypt_statement(str(statement), "SBI", {}).read() == b"decrypted"
