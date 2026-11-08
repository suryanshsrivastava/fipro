"""Credit-card statement PDFs: text extraction and one row reader per card.

Each card lives in its own corpus folder (``data/hdfc_regalia/``...). That folder names the card, the
password key in ``corpus/state/statement_passwords.json`` and the ``source_bank`` of its transactions.
"""

import logging
import re
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.models.transactions import Transaction, TransactionType

logging.getLogger("pypdf").setLevel(logging.ERROR)  # warns about every embedded font it cannot decode

Row = tuple[date, str, Decimal, TransactionType, str]  # the last item is the time of day, "" when the card gives none

_HDFC_ROW = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\|\s*(\d{2}:\d{2})\s+(.*?)\s+(\+\s+)?C\s*([\d,]+\.\d{2})\b"
)  # "+" before the C marks a credit; "+ 15" inside the narration is reward points
_UNI_VISA_ROW = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.*?)\s+(CREDIT|DEBIT)\s+₹([\d,]+(?:\.\d+)?)\s*$")
_DATE = re.compile(r"\d{2}/\d{2}/\d{4}")
_REWARD_POINTS = re.compile(r"\s*\+\s*\d+$")


class PdfLockedError(ValueError):
    """The PDF is encrypted and the password is missing or wrong."""


def read_pdf_lines(filepath: str, password: str) -> list[str]:
    """The text lines of a statement PDF, decrypted in memory."""
    try:
        reader = PdfReader(filepath)
        if reader.is_encrypted and not reader.decrypt(password):
            raise PdfLockedError(f"wrong or missing password for {filepath}")
        return [line for page in reader.pages for line in page.extract_text().splitlines()]
    except PdfReadError as exc:
        raise ValueError(f"cannot read {filepath}: {exc}") from exc


def _money(text: str) -> Decimal:
    return Decimal(text.replace(",", ""))


def _day(text: str) -> date:
    return datetime.strptime(text, "%d/%m/%Y").date()


def _hdfc_rows(lines: list[str]) -> Iterator[Row]:
    for line in lines:
        if match := _HDFC_ROW.match(line.strip()):
            day, clock, narration, credit, amount = match.groups()
            kind = TransactionType.CREDIT if credit else TransactionType.DEBIT
            yield (
                _day(day),
                _REWARD_POINTS.sub("", narration),
                _money(amount),
                kind,
                "" if clock == "00:00" else clock,
            )  # 00:00 marks a posting, not a time


def _uni_visa_rows(lines: list[str]) -> Iterator[Row]:
    for line in lines:
        if match := _UNI_VISA_ROW.match(line.strip()):
            day, narration, kind, amount = match.groups()
            yield _day(day), narration, _money(amount), TransactionType[kind], ""


def _uni_rupay_rows(lines: list[str]) -> Iterator[Row]:
    """Each row is date, [reference], narration, INR, amount, amount, DR/CR, one per line."""
    cells = [line.strip() for line in lines if line.strip()]
    for i in range(len(cells) - 6):
        if not _DATE.fullmatch(cells[i]):
            continue
        j = i + 1 if cells[i + 2] == "INR" else i + 2  # payments carry no reference line
        if j + 4 < len(cells) and cells[j + 1] == "INR" and cells[j + 4] in {"DR", "CR"}:
            kind = TransactionType.DEBIT if cells[j + 4] == "DR" else TransactionType.CREDIT
            yield _day(cells[i]), cells[j], _money(cells[j + 2]), kind, ""


@dataclass(frozen=True, slots=True)
class CardLayout:
    bank: str  # source_bank and password key
    folder: str  # corpus folder holding this card's statements
    rows: Callable[[list[str]], Iterator[Row]]


CARD_LAYOUTS = (
    CardLayout("HDFC_REGALIA", "hdfc_regalia", _hdfc_rows),
    CardLayout("HDFC_SWIGGY", "hdfc_swiggy", _hdfc_rows),
    CardLayout("UNI_VISA", "uni_visa", _uni_visa_rows),
    CardLayout("UNI_RUPAY", "uni_rupay", _uni_rupay_rows),
)


def card_for_folder(name: str) -> CardLayout | None:
    return next((card for card in CARD_LAYOUTS if card.folder == name.lower()), None)


def card_for_bank(bank: str) -> CardLayout | None:
    return next((card for card in CARD_LAYOUTS if card.bank == bank.upper()), None)


def extract_card_transactions(card: CardLayout, filepath: str, password: str) -> list[Transaction]:
    """Read every transaction of one statement PDF.

    Rows are hashed without a balance, so identical same-day rows would collapse as duplicates:
    the second and later copies in a statement get " #n" appended to their narration.
    """
    seen: Counter[tuple] = Counter()
    transactions = []
    for day, narration, amount, kind, clock in card.rows(read_pdf_lines(filepath, password)):
        key = (day, narration, amount, kind)
        seen[key] += 1
        if seen[key] > 1:
            narration = f"{narration} #{seen[key]}"
        transactions.append(
            Transaction(day, narration, amount, kind, card.bank, filepath, raw_data={"time": clock} if clock else None)
        )
    return transactions
