"""SBI Bank statement layout and loader.

SBI statements come in two flavours. Text exports are tab-separated text with an .xls extension and
"DD MMM YYYY" dates. The Excel exports downloaded from the portal are password-protected workbooks with
"Date"/"Details" columns and "DD/MM/YYYY" dates. Both share the Debit/Credit/Balance columns.
"""

import zipfile

import pandas as pd
import xlrd
from openpyxl.utils.exceptions import InvalidFileException

from src.parsers.tabular import BankLayout
from src.utils.date_parser import parse_sbi_date

# Reader failures that only mean "this isn't that format"; they are collected, not swallowed.
_NOT_TEXT_STATEMENT = (UnicodeDecodeError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError)
_NOT_THIS_EXCEL_FORMAT = (xlrd.XLRDError, zipfile.BadZipFile, InvalidFileException, ValueError)

SBI_LAYOUT = BankLayout(
    bank_name="SBI",
    filename_marker="sbi",
    detect_signatures=(
        frozenset({"txn date", "description", "debit", "credit"}),
        frozenset({"date", "details", "debit", "credit"}),
    ),
    column_mapping={
        "transaction_date": ("Txn Date", "Transaction Date", "Value Date", "Date"),
        "description": ("Description", "Particulars", "Details"),
        "debit": ("Debit",),
        "credit": ("Credit",),
        "balance": ("Balance",),
    },
    parse_date=parse_sbi_date,
)


def load_sbi_file(filepath: str) -> pd.DataFrame:
    """
    Load an SBI statement, which is either tab-separated text (often named .xls) or a real Excel file.

    Text is tried first; "not text" and "not that Excel format" are expected and fall through. Anything
    else (I/O errors, unexpected failures) propagates. If no reader accepts the file, the ValueError lists
    each reader's reason.
    """
    reasons: list[str] = []

    try:
        return _read_tab_separated(filepath)
    except _NOT_TEXT_STATEMENT as exc:
        reasons.append(f"text: {exc}")

    for engine in ("xlrd", "openpyxl"):
        try:
            return pd.read_excel(filepath, engine=engine)
        except _NOT_THIS_EXCEL_FORMAT as exc:
            reasons.append(f"{engine}: {exc}")

    raise ValueError(f"Unable to load SBI statement: {filepath} ({'; '.join(reasons)})")


def _read_tab_separated(filepath: str) -> pd.DataFrame:
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()
    header_line_idx = next((i for i, line in enumerate(lines) if "Txn Date" in line and "Debit" in line), None)
    if header_line_idx is None:
        raise ValueError("no 'Txn Date'/'Debit' header line")
    df = pd.read_csv(filepath, sep="\t", encoding="utf-8", skiprows=header_line_idx, on_bad_lines="skip")
    if len(df.columns) <= 3:
        raise ValueError(f"only {len(df.columns)} columns after the header line")
    return df
