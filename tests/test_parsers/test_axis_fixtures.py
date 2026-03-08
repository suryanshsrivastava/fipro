"""Axis parser regression fixtures."""

from tests.test_parsers.helpers import FIXTURES_ROOT, load_case_json, normalize_transactions, parse_axis_case


def test_axis_full_headers_fixture():
    case_dir = FIXTURES_ROOT / "parsers" / "axis" / "full_headers"
    expected = load_case_json(case_dir / "expected.json")
    transactions = parse_axis_case("full_headers")
    assert normalize_transactions(transactions) == expected["transactions"]


def test_axis_abbrev_headers_fixture():
    case_dir = FIXTURES_ROOT / "parsers" / "axis" / "abbrev_headers"
    expected = load_case_json(case_dir / "expected.json")
    transactions = parse_axis_case("abbrev_headers")
    assert normalize_transactions(transactions) == expected["transactions"]


def test_axis_empty_statement_fixture():
    case_dir = FIXTURES_ROOT / "parsers" / "axis" / "empty_statement"
    expected = load_case_json(case_dir / "expected.json")
    transactions = parse_axis_case("empty_statement")
    assert normalize_transactions(transactions) == expected["transactions"]
