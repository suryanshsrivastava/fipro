"""SBI Bank statement parser.

SBI statements are often tab-separated text with an .xls extension, with a variable-position header
(Txn Date / Description / Debit / Credit / Balance) and "DD MMM YYYY" dates.
"""

import pandas as pd

from src.parsers.tabular import TabularStatementParser
from src.utils.date_parser import parse_sbi_date


class SBIParser(TabularStatementParser):
    bank_name = "SBI"
    filename_marker = "sbi"
    detect_signatures = (frozenset({"txn date", "description", "debit", "credit"}),)
    column_mapping = {
        "transaction_date": ["Txn Date", "Transaction Date", "Value Date"],
        "description": ["Description", "Particulars"],
        "debit": ["Debit"],
        "credit": ["Credit"],
        "balance": ["Balance"],
        "reference": ["Ref No./Cheque No.", "Ref No."],
    }
    parse_date = staticmethod(parse_sbi_date)

    @staticmethod
    def load_sbi_file(filepath: str) -> pd.DataFrame | None:
        """
        Load SBI statement file, handling both Excel and tab-separated formats.

        SBI often exports .xls files that are actually tab-separated text with
        metadata rows at the top. This method finds and loads from the header row.
        """
        # Try reading as tab-separated text first (common SBI format)
        try:
            # First, find the header row by scanning for "Txn Date"
            with open(filepath, encoding="utf-8") as f:
                lines = f.readlines()

            header_line_idx = None
            for idx, line in enumerate(lines):
                if "Txn Date" in line and "Debit" in line:
                    header_line_idx = idx
                    break

            if header_line_idx is not None:
                # Read from header row onwards
                df = pd.read_csv(filepath, sep="\t", encoding="utf-8", skiprows=header_line_idx, on_bad_lines="skip")
                if len(df.columns) > 3:
                    return df
        except Exception:
            pass

        # Try Excel formats
        for engine in ["xlrd", "openpyxl"]:
            try:
                df = pd.read_excel(filepath, engine=engine)
                return df
            except Exception:
                continue

        return None
