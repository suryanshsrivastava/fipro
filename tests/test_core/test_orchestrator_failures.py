"""Failure-mode tests for the file processing pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.config import Settings
from src.core.orchestrator import process_pipeline

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def test_process_pipeline_aborts_on_bad_file_and_leaves_everything_in_place(tmp_path, pipeline_config_factory):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    shutil.copy(
        FIXTURES_ROOT / "parsers" / "hdfc" / "raw_monthly_export" / "input.xls",
        input_dir / "hdfc.xls",
    )
    (input_dir / "bad_axis.xlsx").write_text("not an excel file", encoding="utf-8")

    config = pipeline_config_factory(
        input_dir=input_dir,
        output_dir=output_dir,
        fail_on_file_error=True,
    )
    config["external_accounts"] = {"names": ["CREDIT_CARD"], "payment_keywords": ["CREDIT CARD", "CRED"]}

    with pytest.raises(RuntimeError, match="failed to parse"):
        process_pipeline(Settings.from_config(config))

    # The bad file is never quarantined: input is the archive, so a failed run changes nothing.
    assert (input_dir / "hdfc.xls").exists()
    assert (input_dir / "bad_axis.xlsx").exists()
    assert not output_dir.exists() or not list(output_dir.iterdir())


def test_process_pipeline_continues_past_bad_file_and_still_exports_good_ones(tmp_path, pipeline_config_factory):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    shutil.copy(
        FIXTURES_ROOT / "parsers" / "hdfc" / "raw_monthly_export" / "input.xls",
        input_dir / "hdfc.xls",
    )
    (input_dir / "bad_axis.xlsx").write_text("not an excel file", encoding="utf-8")

    config = pipeline_config_factory(
        input_dir=input_dir,
        output_dir=output_dir,
        fail_on_file_error=False,
    )
    config["external_accounts"] = {"names": ["CREDIT_CARD"], "payment_keywords": ["CREDIT CARD", "CRED"]}

    run = process_pipeline(Settings.from_config(config))

    assert len(run.results) == 2
    failed = [result for result in run.results if result.errors]
    assert [Path(result.source_file).name for result in failed] == ["bad_axis.xlsx"]
    assert (output_dir / "goodbudget_export.csv").exists()
    # Both files are still exactly where they were dropped.
    assert sorted(path.name for path in input_dir.iterdir() if path.name != "audit_log.csv") == [
        "bad_axis.xlsx",
        "hdfc.xls",
    ]
