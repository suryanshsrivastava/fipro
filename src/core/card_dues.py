"""When each credit card's latest bill is due, how much, and whether a payment since the statement covers it.

Read from the newest statement PDF in each card folder (``data/<card>/``); payments are the card-side credits
in the export that look like a bill payment. Cashback and refunds do not count as payment.
"""

import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from src.config import Settings
from src.parsers.card_pdf import CARD_LAYOUTS, read_pdf_lines

_LONG_DATE = re.compile(r"(\d{1,2} [A-Z][a-z]{2}), (\d{4})")
_PAYMENT = re.compile(r"PYMT|PMT|PAYMENT", re.IGNORECASE)
_cache: dict[tuple[str, float], dict | None] = {}


def _money(text: str) -> Decimal:
    return Decimal(re.sub(r"[^\d.]", "", text))


def _day(text: str) -> date:
    return datetime.strptime(text, "%d %b, %Y").date()


def _summary(lines: list[str]) -> dict | None:
    """statement date, due date and total due from one statement's text, or None when it is not recognised."""
    cells = [line.strip() for line in lines if line.strip()]
    text = "\n".join(cells)
    if "TOTAL AMOUNT DUE" in cells:  # HDFC
        at = cells.index("TOTAL AMOUNT DUE")
        due = cells[cells.index("DUE DATE") + 1] if "DUE DATE" in cells else ""
        hdfc_stmt = re.search(r"As on\s*:\s*(\d{1,2} [A-Z][a-z]{2}, \d{4})", text)
        if hdfc_stmt and _LONG_DATE.fullmatch(due):
            return {"statement": _day(hdfc_stmt[1]), "due": _day(due), "total": _money(cells[at + 1])}
        return None
    visa_stmt, visa_due = (
        re.search(r"Statement Date (\d{1,2} [A-Z][a-z]{2}, \d{4})", text),
        re.search(r"^Due Date (\d{1,2} [A-Z][a-z]{2}, \d{4})", text, re.M),
    )
    if visa_stmt and visa_due:  # Uni Visa: closing balance from its summary lines
        parts = {
            k: re.search(rf"^{k}\s*[+-]\s*₹([\d,]+(?:\.\d+)?)", text, re.M)
            for k in ("Opening Balance", "Payment / Credits", "Purchases / Debits", "Finance Charges")
        }
        if all(parts.values()):
            v = {k: _money(m[1]) for k, m in parts.items() if m}
            return {
                "statement": _day(visa_stmt[1]),
                "due": _day(visa_due[1]),
                "total": v["Opening Balance"] - v["Payment / Credits"] + v["Purchases / Debits"] + v["Finance Charges"],
            }
        return None
    rs, rd, rt = (
        re.search(r"Statement Date :\s*(\d{2})/(\d{2})/(\d{4})", text),
        re.search(r"(\d{2})/(\d{2})/(\d{4})\nPay Now", text),
        re.search(r"([\d,]+\.\d{2})DR", text),
    )
    if rs and rd and rt:  # Uni RuPay
        return {
            "statement": date(int(rs[3]), int(rs[2]), int(rs[1])),
            "due": date(int(rd[3]), int(rd[2]), int(rd[1])),
            "total": _money(rt[1]),
        }
    return None


def card_dues(settings: Settings, rows: list[dict], today: date | None = None) -> list[dict]:
    """One entry per card with a recognised statement: bank, due date, total due, days left and whether it is paid."""
    today = today or date.today()
    try:
        passwords = json.loads(Path(settings.paths.statement_passwords).read_text())
    except FileNotFoundError, ValueError:
        passwords = {}
    out = []
    for card in CARD_LAYOUTS:
        newest = None
        for pdf in Path(settings.paths.input, card.folder).glob("*.pdf"):
            key = (str(pdf), pdf.stat().st_mtime)
            if key not in _cache:
                try:
                    _cache[key] = _summary(read_pdf_lines(str(pdf), passwords.get(card.bank, "")))
                except ValueError:
                    _cache[key] = None
            found = _cache[key]
            if found and (newest is None or found["statement"] > newest["statement"]):
                newest = found
        if not newest:
            continue
        paid = sum(
            (
                Decimal(r["amount"])
                for r in rows
                if r["source_bank"] == card.bank
                and r["transaction_date"] >= newest["statement"].isoformat()
                and Decimal(r["amount"]) > 0
                and _PAYMENT.search(r["description"])
            ),
            Decimal(0),
        )
        out.append(
            {
                "bank": card.bank,
                "due": newest["due"].isoformat(),
                "total": float(newest["total"]),
                "days": (newest["due"] - today).days,
                "paid": paid >= newest["total"] - 1,
                "paid_amount": float(paid),
            }
        )
    return out
