"""Card statement row readers, on synthetic text lines (no real statements)."""

from datetime import date
from decimal import Decimal

from src.models.transactions import TransactionType
from src.parsers.card_pdf import CARD_LAYOUTS, card_for_folder, extract_card_transactions

D, C = TransactionType.DEBIT, TransactionType.CREDIT


def _rows(folder: str, lines: list[str]) -> list[tuple]:
    card = card_for_folder(folder)
    assert card
    return list(card.rows(lines))


def test_hdfc_marks_credit_by_plus_before_the_rupee_and_drops_reward_points():
    rows = _rows(
        "hdfc_swiggy",
        [
            "01/10/2026| 04:50 RAZ*SHOP MUMBAI + 15  C 710.63 l",
            "15/10/2026| 08:52 BPPY PYMT X (Ref# 390160555012606) +  C 10,170.00 l",
            "Page 1 of 3",
        ],
    )
    assert rows == [
        (date(2026, 10, 1), "RAZ*SHOP MUMBAI", Decimal("710.63"), D, "04:50"),
        (date(2026, 10, 15), "BPPY PYMT X (Ref# 390160555012606)", Decimal("10170.00"), C, "08:52"),
    ]


def test_uni_visa_reads_one_line_rows():
    rows = _rows(
        "uni_visa",
        ["16/09/2026 RAZORPAY PMT UNI MOBILEAPP- API CREDIT ₹128.59", "01/10/2026 AMP CODE CA* DEBIT ₹1,919.9"],
    )
    assert rows == [
        (date(2026, 9, 16), "RAZORPAY PMT UNI MOBILEAPP- API", Decimal("128.59"), C, ""),
        (date(2026, 10, 1), "AMP CODE CA*", Decimal("1919.9"), D, ""),
    ]


def test_uni_rupay_reads_rows_with_and_without_a_reference_line():
    lines = ["25/09/2026", "R3168Z", "UPI-AMAZON INDIA", "INR", "292.00", "292.00 ", "DR"]
    lines += ["16/09/2026", "RAZORPAY PMT", "INR", "40,453.76", "40,453.76", "CR", "Transaction Details"]
    lines += ["13/10/2026", "|   Statement Period :", "14 Sep, 2026 to 13 Oct, 2026"]  # header date, not a row
    assert _rows("uni_rupay", lines) == [
        (date(2026, 9, 25), "UPI-AMAZON INDIA", Decimal("292.00"), D, ""),
        (date(2026, 9, 16), "RAZORPAY PMT", Decimal("40453.76"), C, ""),
    ]


def test_identical_same_day_rows_stay_distinct_after_hashing(monkeypatch):
    card = card_for_folder("uni_visa")
    assert card
    monkeypatch.setattr(
        "src.parsers.card_pdf.read_pdf_lines",
        lambda *_: ["27/09/2026 CAS*X IN DEBIT ₹500", "27/09/2026 CAS*X IN DEBIT ₹500"],
    )
    txns = extract_card_transactions(card, "f.pdf", "")
    assert len({t.hash for t in txns}) == 2


def test_every_card_has_its_own_folder():
    assert len({c.folder for c in CARD_LAYOUTS}) == len(CARD_LAYOUTS)


def test_card_rows_get_a_payee_and_fees_share_one():
    from src.utils.narration import CARD_BANKS, card_merchant

    assert {c.bank for c in CARD_LAYOUTS} == CARD_BANKS
    assert card_merchant("Swiggy InstamartBANGALORE") == "SWIGGY INSTAMARTBANGALORE"
    assert card_merchant("UPI-ZEPTO #2") == "ZEPTO"
    for fee in (
        "LATE FEE (Ref# 19999999981013999211830)",
        "IGST-VPS2726470743900-RATE 18.0 -07",
        "FINANCE CHARGES (Ref# 1)",
    ):
        assert card_merchant(fee) == "CARD CHARGES"
