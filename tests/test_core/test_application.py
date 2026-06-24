from dataclasses import dataclass, field

import pytest

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
    lines = run_status_command({}, discoverer=lambda _config: files)
    assert lines == [
        "HDFC: 2 file(s)",
        "  - a.xls",
        "  - c.xls",
        "SBI: 1 file(s)",
        "  - b.xls",
    ]


def test_run_status_command_with_no_files():
    assert run_status_command({}, discoverer=lambda _config: []) == ["No files to process."]


def test_prepare_dashboard_launch_requires_existing_csv():
    with pytest.raises(CommandInputError, match="CSV not found"):
        prepare_dashboard_launch("missing.csv", 8080, False, path_exists=lambda _path: False)


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
        lambda _config: type("Run", (), {"results": [1]})(),
    )
    monkeypatch.setattr("src.core.application.summarize_pipeline_run", lambda _run: ["ok"])
    assert run_process_command({}) == ["ok"]
