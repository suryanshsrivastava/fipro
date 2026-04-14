"""Regression tests for raw bank export extraction fixtures."""

from tests.test_extraction.helpers import (
    FIXTURES_ROOT,
    extract_case_dataframe,
    extract_single_input_dataframe,
    load_case_json,
    normalize_dataframe,
)


def test_hdfc_raw_monthly_export_fixture():
    case_dir = FIXTURES_ROOT / "parsers" / "hdfc" / "raw_monthly_export"
    expected = load_case_json(case_dir / "expected.json")
    actual = extract_single_input_dataframe(case_dir)
    assert normalize_dataframe(actual) == expected["transactions"]


def test_axis_raw_monthly_export_fixture():
    case_dir = FIXTURES_ROOT / "parsers" / "axis" / "raw_monthly_export"
    expected = load_case_json(case_dir / "expected.json")
    actual = extract_single_input_dataframe(case_dir)
    assert normalize_dataframe(actual) == expected["transactions"]


def test_sbi_raw_monthly_export_fixture():
    case_dir = FIXTURES_ROOT / "parsers" / "sbi" / "raw_monthly_export"
    expected = load_case_json(case_dir / "expected.json")
    actual = extract_single_input_dataframe(case_dir)
    assert normalize_dataframe(actual) == expected["transactions"]


def test_raw_monthly_exports_2025_08_27_combined_fixture():
    case_dir = FIXTURES_ROOT / "extraction" / "raw_monthly_exports_2025_08_27"
    expected = load_case_json(case_dir / "expected.json")
    actual = extract_case_dataframe(case_dir)
    assert normalize_dataframe(actual) == expected["transactions"]
