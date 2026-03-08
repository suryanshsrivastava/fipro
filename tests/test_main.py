"""CLI command behavior tests."""

from pathlib import Path

from src.main import cmd_status


def test_cmd_status_groups_files_by_bank(capsys, tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "hdfc_alpha.xls").write_text("sample", encoding="utf-8")
    (input_dir / "axis_beta.xlsx").write_text("sample", encoding="utf-8")

    config = {
        "paths": {"input": str(input_dir)},
        "processing": {"supported_extensions": ["xls", "xlsx"]},
    }

    exit_code = cmd_status(None, config)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"Input directory: {input_dir}" in captured.out
    assert "Pending files: 2" in captured.out
    assert "AXIS:" in captured.out
    assert "HDFC:" in captured.out
