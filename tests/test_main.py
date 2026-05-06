"""CLI command behavior tests."""

import argparse
from pathlib import Path

from src import main as main_module
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
    assert "Config path:" in captured.out
    assert f"Input directory: {input_dir}" in captured.out
    assert "Pending files: 2" in captured.out
    assert "AXIS:" in captured.out
    assert "HDFC:" in captured.out


def test_main_uses_default_config_path_when_flag_is_omitted(monkeypatch):
    captured: dict[str, object] = {}

    def fake_load_config(config_path):
        captured["config_path"] = config_path
        return {
            "fipro": {"log_level": "INFO"},
            "paths": {"log_file": None},
        }

    def fake_setup_logging(level, log_file):
        captured["logging"] = (level, log_file)

    def fake_cmd_process(args, config):
        captured["args"] = args
        captured["config"] = config
        return 0

    monkeypatch.setattr(main_module, "load_config", fake_load_config)
    monkeypatch.setattr(main_module, "setup_logging", fake_setup_logging)
    monkeypatch.setattr(main_module, "cmd_process", fake_cmd_process)
    monkeypatch.setattr(
        argparse.ArgumentParser,
        "parse_args",
        lambda self: argparse.Namespace(command="process", config=None),
    )

    assert main_module.main() == 0
    assert captured["config_path"] is None
