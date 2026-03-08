"""Fixture-based functional tests for the full processing pipeline."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from src.core.orchestrator import process_pipeline


FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def test_mixed_basic_pipeline_fixture(tmp_path):
    case_dir = FIXTURES_ROOT / "pipeline" / "mixed_basic"
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

    results = process_pipeline(config)

    assert len(results) == 3
    assert sorted(path.name for path in processed_dir.iterdir()) == [
        "axis.xlsx",
        "hdfc.xlsx",
        "sbi.xls",
    ]
    assert not failed_dir.exists() or not list(failed_dir.iterdir())

    csv_path = next(output_dir.glob("goodbudget_*.csv"))
    report_path = next(output_dir.glob("processing_report_*.json"))

    expected_csv = (case_dir / "expected_goodbudget.csv").read_text(encoding="utf-8")
    actual_csv = csv_path.read_text(encoding="utf-8")
    assert _normalize_csv(actual_csv) == _normalize_csv(expected_csv)

    actual_report = json.loads(report_path.read_text(encoding="utf-8"))
    expected_report = json.loads(
        (case_dir / "expected_report.json").read_text(encoding="utf-8")
    )
    assert _stable_report(actual_report) == expected_report


def _normalize_csv(contents: str) -> list[list[str]]:
    return list(csv.reader(contents.strip().splitlines()))


def _stable_report(report: dict) -> dict:
    return {
        "summary": report["summary"],
        "by_bank": report["by_bank"],
        "files": [
            {
                "source_file": item["source_file"],
                "bank": item["bank"],
                "total_transactions": item["total_transactions"],
                "successful": item["successful"],
                "failed": item["failed"],
                "duplicates_skipped": item["duplicates_skipped"],
            }
            for item in report["files"]
        ],
    }
