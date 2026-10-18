from __future__ import annotations

import pandas as pd

from src.models.transactions import TransactionType
from src.parsers.axis import AXIS_LAYOUT
from src.parsers.hdfc import HDFC_LAYOUT
from src.parsers.sbi import SBI_LAYOUT
from src.parsers.tabular import TabularStatementParser


def test_axis_parses_abbreviated_headers_after_preamble():
    df = pd.DataFrame(
        [
            ["Axis Bank", None, None, None, None],
            ["Tran Date", "Particulars", "DR", "CR", "BAL"],
            ["01-02-2026", "UPI/shop", "150.00", None, "850.00"],
            ["02-02-2026", "Salary", None, "1,000.00", "1,850.00"],
        ]
    )
    parser = TabularStatementParser(AXIS_LAYOUT)

    assert parser.can_parse("axis_feb.xls", df)
    assert not parser.can_parse("statement.xls", df)

    debit, credit = parser.extract_transactions(df, "axis_feb.xls")
    assert (debit.transaction_type, str(debit.amount), str(debit.balance)) == (
        TransactionType.DEBIT,
        "150.00",
        "850.00",
    )
    assert (credit.transaction_type, str(credit.amount)) == (TransactionType.CREDIT, "1000.00")


def test_sbi_uses_columns_as_header_when_already_parsed():
    df = pd.DataFrame(
        {
            "Txn Date": ["15 Nov 2025"],
            "Description": ["ATM WDL"],
            "Debit": ["500.00"],
            "Credit": [None],
            "Balance": ["9,500.00"],
        }
    )
    parser = TabularStatementParser(SBI_LAYOUT)

    [txn] = parser.extract_transactions(df, "sbi.xls")
    assert (txn.description, str(txn.amount), txn.transaction_type) == ("ATM WDL", "500.00", TransactionType.DEBIT)


def test_sbi_parses_portal_excel_export_with_date_and_details_headers():
    """The password-protected portal download uses Date/Details and DD/MM/YYYY, plus footer rows."""
    df = pd.DataFrame(
        [
            ["Mr. SURYANSH SRIVASTAVA", None, None, None, None, None],
            ["Statement From : 28-06-2017 to 15-07-2026", None, None, None, None, None],
            ["Date", "Details", "Ref No/Cheque No", "Debit", "Credit", "Balance"],
            ["07/07/2017", " CASH DEPOSIT SELF \n AT 16120 KAKROLA MOR", None, None, "2,000.00", "2,000.00"],
            ["08/07/2017", "TO TRANSFER-UPI/DR/1/shop", "TRANSFER TO 1", "500.00", None, "1,500.00"],
            ["Statement Summary : 01-01-2017 To 15-07-2026", None, None, None, None, None],
            ["Please do not share your ATM, Debit/Credit Card number", None, None, None, None, None],
        ]
    )
    parser = TabularStatementParser(SBI_LAYOUT)

    assert parser.can_parse("SBI/AccountStatement_15072026_004021.xlsx", df)

    credit, debit = parser.extract_transactions(df, "AccountStatement_15072026_004021.xlsx")
    assert (credit.transaction_date.isoformat(), credit.transaction_type, str(credit.amount)) == (
        "2017-07-07",
        TransactionType.CREDIT,
        "2000.00",
    )
    assert (debit.transaction_date.isoformat(), debit.transaction_type, str(debit.amount), str(debit.balance)) == (
        "2017-07-08",
        TransactionType.DEBIT,
        "500.00",
        "1500.00",
    )


def test_hdfc_detection_requires_all_amount_columns():
    df = pd.DataFrame([["Date", "Narration", "Withdrawal Amt."], ["01/02/26", "x", "1"]])

    assert not TabularStatementParser(HDFC_LAYOUT).can_parse("hdfc.xls", df)
