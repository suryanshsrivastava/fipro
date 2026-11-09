from datetime import date
from decimal import Decimal

from src.core.card_dues import _summary


def test_hdfc_statement_text_gives_due_date_total_and_statement_date():
    lines = [
        "TOTAL AMOUNT DUE",
        "C2,378.00",
        "MINIMUM DUE",
        "C433.00",
        "DUE DATE",
        "09 Nov, 2026",
        "x",
        "Your Card Control Setting    As on :  20 Oct, 2026",
    ]
    assert _summary(lines) == {"statement": date(2026, 10, 20), "due": date(2026, 11, 9), "total": 2378}


def test_uni_visa_total_is_the_closing_balance_of_its_summary_lines():
    lines = [
        "Statement Date 14 Oct, 2026",
        "Opening Balance + ₹128.59",
        "Payment / Credits - ₹128.59",
        "Purchases / Debits + ₹36,270.78",
        "Finance Charges + ₹0",
        "Due Date 30 Oct, 2026",
    ]
    assert _summary(lines) == {"statement": date(2026, 10, 14), "due": date(2026, 10, 30), "total": Decimal("36270.78")}


def test_unrecognised_text_gives_nothing():
    assert _summary(["a bank letter"]) is None
