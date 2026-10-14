"""Axis Bank statement parser.

Axis statements have a ~10-15 row preamble, then Tran Date / Particulars / Debit / Credit / Balance
(or the abbreviations DR / CR / BAL) with DD-MM-YYYY dates.
"""

from src.parsers.tabular import TabularStatementParser
from src.utils.date_parser import parse_axis_date


class AxisParser(TabularStatementParser):
    bank_name = "AXIS"
    filename_marker = "axis"
    detect_signatures = (
        frozenset({"tran date", "particulars", "debit", "credit"}),
        frozenset({"tran date", "particulars", "dr", "cr"}),
    )
    column_mapping = {
        "transaction_date": ["Tran Date", "Transaction Date"],
        "description": ["Particulars", "PARTICULARS"],
        "debit": ["Debit", "DR"],
        "credit": ["Credit", "CR"],
        "balance": ["Balance", "BAL"],
        "reference": ["Chq No", "Cheque No.", "CHQNO"],
    }
    parse_date = staticmethod(parse_axis_date)
