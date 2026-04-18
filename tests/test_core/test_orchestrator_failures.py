"""Failure-mode tests for the file processing pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.core.orchestrator import process_pipeline


FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def test_process_pipeline_fails_whole_run_and_moves_only_bad_file(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    processed_dir = tmp_path / "processed"
    failed_dir = tmp_path / "failed"
    input_dir.mkdir()

    shutil.copy(
        FIXTURES_ROOT / "pipeline" / "mixed_basic" / "input" / "hdfc.xlsx",
        input_dir / "hdfc.xlsx",
    )
    (input_dir / "bad_axis.xlsx").write_text("not an excel file", encoding="utf-8")

    config = {
        "fipro": {"version": "0.1.0", "log_level": "INFO"},
        "paths": {
            "input": str(input_dir),
            "output": str(output_dir),
            "processed": str(processed_dir),
            "failed": str(failed_dir),
        },
        "processing": {
            "supported_extensions": ["xls", "xlsx"],
            "include_internal_transfers": True,
            "fail_on_file_error": True,
        },
        "banks": {
            "hdfc": {"patterns": ["*hdfc*"]},
            "sbi": {"patterns": ["*sbi*"]},
            "axis": {"patterns": ["*axis*"]},
        },
        "external_accounts": {
            "names": ["CREDIT_CARD"],
            "payment_keywords": ["CREDIT CARD", "CRED"],
        },
    }

    with pytest.raises(RuntimeError, match="failed to parse"):
        process_pipeline(config)

    assert (input_dir / "hdfc.xlsx").exists()
    assert not processed_dir.exists() or not list(processed_dir.iterdir())
    assert not output_dir.exists() or not list(output_dir.iterdir())
    assert (failed_dir / "bad_axis.xlsx").exists()
    assert (failed_dir / "bad_axis.xlsx.error.txt").exists()


def test_process_pipeline_continues_and_moves_bad_file_to_failed(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    processed_dir = tmp_path / "processed"
    failed_dir = tmp_path / "failed"
    input_dir.mkdir()

    shutil.copy(
        FIXTURES_ROOT / "pipeline" / "mixed_basic" / "input" / "hdfc.xlsx",
        input_dir / "hdfc.xlsx",
    )
    (input_dir / "bad_axis.xlsx").write_text("not an excel file", encoding="utf-8")

    config = {
        "fipro": {"version": "0.1.0", "log_level": "INFO"},
        "paths": {
            "input": str(input_dir),
            "output": str(output_dir),
            "processed": str(processed_dir),
            "failed": str(failed_dir),
        },
        "processing": {
            "supported_extensions": ["xls", "xlsx"],
            "include_internal_transfers": True,
            "fail_on_file_error": False,
        },
        "banks": {
            "hdfc": {"patterns": ["*hdfc*"]},
            "sbi": {"patterns": ["*sbi*"]},
            "axis": {"patterns": ["*axis*"]},
        },
        "external_accounts": {
            "names": ["CREDIT_CARD"],
            "payment_keywords": ["CREDIT CARD", "CRED"],
        },
    }

    run = process_pipeline(config)

    assert len(run.results) == 2
    assert sorted(path.name for path in processed_dir.iterdir()) == ["hdfc.xlsx"]
    assert (failed_dir / "bad_axis.xlsx").exists()
    assert (failed_dir / "bad_axis.xlsx.error.txt").exists()
    assert next(output_dir.glob("goodbudget_*.csv")).exists()
    assert not (processed_dir / "bad_axis.xlsx").exists()
