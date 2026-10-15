"""HDFC Bank statement layout.

HDFC statements have a ~15 row preamble (logo, address), then Date / Narration / Withdrawal Amt. /
Deposit Amt. / Closing Balance with DD/MM/YY or DD-MM-YYYY dates.
"""

from src.parsers.tabular import BankLayout
from src.utils.date_parser import parse_hdfc_date

HDFC_LAYOUT = BankLayout(
    bank_name="HDFC",
    filename_marker="hdfc",
    detect_signatures=(frozenset({"narration", "withdrawal amt.", "deposit amt."}),),
    column_mapping={
        "transaction_date": ("Date", "Value Dt"),
        "description": ("Narration",),
        "debit": ("Withdrawal Amt.", "Withdrawal"),
        "credit": ("Deposit Amt.", "Deposit"),
        "balance": ("Closing Balance",),
    },
    parse_date=parse_hdfc_date,
)
