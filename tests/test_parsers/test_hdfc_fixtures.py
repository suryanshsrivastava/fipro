"""HDFC parser regression fixtures."""

from tests.test_parsers.helpers import FIXTURES_ROOT, load_case_json, normalize_transactions, parse_hdfc_case


def test_hdfc_basic_credit_debit_fixture():
    case_dir = FIXTURES_ROOT / "parsers" / "hdfc" / "basic_credit_debit"
    expected = load_case_json(case_dir / "expected.json")
    transactions = parse_hdfc_case("basic_credit_debit")
    assert normalize_transactions(transactions) == expected["transactions"]


def test_hdfc_empty_statement_fixture():
    case_dir = FIXTURES_ROOT / "parsers" / "hdfc" / "empty_statement"
    expected = load_case_json(case_dir / "expected.json")
    transactions = parse_hdfc_case("empty_statement")
    assert normalize_transactions(transactions) == expected["transactions"]
