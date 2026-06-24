"""Fixture-based functional tests for the full processing pipeline."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.core.orchestrator import process_pipeline

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def test_raw_monthly_exports_pipeline(tmp_path):
    case_dir = FIXTURES_ROOT / "extraction" / "raw_monthly_exports_2025_08_27"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    processed_dir = tmp_path / "processed"
    failed_dir = tmp_path / "failed"

    shutil.copytree(case_dir / "input", input_dir)

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
            "seen_hashes_path": str(tmp_path / ".seen_hashes"),
        },
        "banks": {
            "hdfc": {"patterns": ["*hdfc*"]},
            "sbi": {"patterns": ["*sbi*"]},
            "axis": {"patterns": ["*axis*"]},
        },
        "external_accounts": {
            "names": ["CREDIT_CARD"],
            "payment_keywords": ["CREDIT CARD", "CC PAYMENT", "CARD PAYMENT", "CRED"],
        },
    }

    run = process_pipeline(config)

    assert len(run.results) == 3
    assert sorted(path.name for path in processed_dir.iterdir()) == [
        "axis.xls",
        "hdfc.xls",
        "sbi.xls",
    ]
    assert not failed_dir.exists() or not list(failed_dir.iterdir())

    assert (output_dir / "goodbudget_export.csv").exists()
    assert (output_dir / "processing_report.json").exists()
    assert (output_dir / "hub_summary.csv").exists()

    report = json.loads((output_dir / "processing_report.json").read_text(encoding="utf-8"))
    assert report["summary"]["total_files"] == 3
    assert report["cash_flow"]["net_cash_flow"] is not None
    assert report["date_range"]["earliest"] is not None
    assert run.hub_summary.cash_flow is not None
