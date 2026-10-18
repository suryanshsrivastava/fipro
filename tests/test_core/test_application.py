from dataclasses import dataclass, field
from pathlib import Path

import pytest

from src.config import PathSettings, Settings
from src.core.application import (
    CommandInputError,
    prepare_dashboard_launch,
    run_process_command,
    run_sheets_command,
    run_status_command,
)


@dataclass(slots=True)
class FakeCrawledFile:
    filename: str
    metadata: dict = field(default_factory=dict)


def test_run_status_command_groups_files_by_bank():
    files = [
        FakeCrawledFile(filename="a.xls", metadata={"bank": "HDFC"}),
        FakeCrawledFile(filename="b.xls", metadata={"bank": "SBI"}),
        FakeCrawledFile(filename="c.xls", metadata={"bank": "HDFC"}),
    ]
    lines = run_status_command(Settings(PathSettings(input="in")), discoverer=lambda _config: files)
    assert lines == [
        "HDFC: 2 file(s)",
        "  - a.xls",
        "  - c.xls",
        "SBI: 1 file(s)",
        "  - b.xls",
    ]


def test_run_status_command_with_no_files():
    assert run_status_command(Settings(PathSettings(input="in")), discoverer=lambda _config: []) == [
        "No files to process."
    ]


def test_prepare_dashboard_launch_starts_without_csv_so_locked_files_can_be_unlocked():
    launch = prepare_dashboard_launch("missing.csv", 8080, False, path_exists=lambda _path: False)
    assert launch.lines[-1] == "No transactions yet (missing.csv not found); showing locked statements only."


def test_run_sheets_command_requires_credentials():
    def fake_exists(path):
        return str(path).endswith("goodbudget.csv")

    with pytest.raises(CommandInputError, match="Google credentials not found"):
        run_sheets_command("goodbudget.csv", "missing.json", "Title", path_exists=fake_exists)


def test_run_sheets_command_returns_output_line():
    result = run_sheets_command(
        "goodbudget.csv",
        "creds.json",
        "Title",
        path_exists=lambda _path: True,
        exporter=lambda *_args: "https://example.com/sheet",
    )
    assert result.url == "https://example.com/sheet"
    assert result.lines == ["Done. Open: https://example.com/sheet"]


def test_run_process_command_returns_pipeline_lines(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "src.core.application.process_pipeline",
        lambda _config, **_kwargs: type("Run", (), {"results": [1]})(),
    )
    monkeypatch.setattr("src.core.application.summarize_pipeline_run", lambda _run: ["ok"])
    assert run_process_command(Settings(PathSettings(input="in"))) == ["ok"]


def test_run_process_command_reads_saved_statement_passwords(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """`fipro process` gets its passwords from the configured file, not only from the dashboard."""
    passwords_path = tmp_path / "statement_passwords.json"
    passwords_path.write_text('{"SBI": "from-file"}')
    captured: dict = {}

    def fake_pipeline(_settings, passwords=None):
        captured["passwords"] = passwords
        return type("Run", (), {"results": [1]})()

    monkeypatch.setattr("src.core.application.process_pipeline", fake_pipeline)
    monkeypatch.setattr("src.core.application.summarize_pipeline_run", lambda _run: ["ok"])
    settings = Settings(PathSettings(input="in", statement_passwords=str(passwords_path)))

    assert run_process_command(settings) == ["ok"]
    assert captured["passwords"] == {"SBI": "from-file"}
