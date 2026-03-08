"""SBI parser regression fixtures."""

from tests.test_parsers.helpers import FIXTURES_ROOT, load_case_json, normalize_transactions, parse_sbi_case


def test_sbi_excel_basic_fixture():
    case_dir = FIXTURES_ROOT / "parsers" / "sbi" / "excel_basic"
    expected = load_case_json(case_dir / "expected.json")
    transactions = parse_sbi_case("excel_basic", "xlsx")
    assert normalize_transactions(transactions) == expected["transactions"]


def test_sbi_tabsep_basic_fixture():
    case_dir = FIXTURES_ROOT / "parsers" / "sbi" / "tabsep_basic"
    expected = load_case_json(case_dir / "expected.json")
    transactions = parse_sbi_case("tabsep_basic", "xls")
    assert normalize_transactions(transactions) == expected["transactions"]


def test_sbi_empty_statement_fixture():
    case_dir = FIXTURES_ROOT / "parsers" / "sbi" / "empty_statement"
    expected = load_case_json(case_dir / "expected.json")
    transactions = parse_sbi_case("empty_statement", "xlsx")
    assert normalize_transactions(transactions) == expected["transactions"]
