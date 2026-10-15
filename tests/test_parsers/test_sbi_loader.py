import pytest

from src.parsers.sbi import load_sbi_file

TEXT_STATEMENT = (
    "Account Name\tTest\n"
    "\n"
    "Txn Date\tValue Date\tDescription\tRef No./Cheque No.\tDebit\tCredit\tBalance\n"
    "15 Nov 2025\t15 Nov 2025\tATM WDL\t123\t500.00\t\t9,500.00\n"
)


def test_loads_tab_separated_text_statement(tmp_path):
    statement = tmp_path / "sbi.xls"
    statement.write_text(TEXT_STATEMENT, encoding="utf-8")

    df = load_sbi_file(str(statement))

    assert list(df.columns)[:3] == ["Txn Date", "Value Date", "Description"]
    assert len(df) == 1


def test_unreadable_file_reports_each_reader_reason(tmp_path):
    statement = tmp_path / "sbi.xls"
    statement.write_bytes(b"\x00\x01 definitely not a statement")

    with pytest.raises(ValueError, match=r"Unable to load SBI statement: .*text: .*xlrd: .*openpyxl: "):
        load_sbi_file(str(statement))


def test_missing_file_is_not_swallowed(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_sbi_file(str(tmp_path / "missing.xls"))
