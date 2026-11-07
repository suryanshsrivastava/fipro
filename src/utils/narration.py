"""Read a payment mode and counterparty out of a bank narration (HDFC, SBI and Axis each format it differently)."""

import re

# Order matters: "POS ATM PURCH" is a card purchase, not an ATM withdrawal.
_MODES = (
    ("UPI", re.compile(r"\bUPI\b", re.I)),
    ("IMPS", re.compile(r"\bIMPS", re.I)),
    ("NETBANKING", re.compile(r"\bINB\b")),
    ("NEFT", re.compile(r"\bNEFT\b", re.I)),
    ("RTGS", re.compile(r"\bRTGS\b", re.I)),
    ("ECOM", re.compile(r"\bECOM\b", re.I)),
    ("POS", re.compile(r"\bPOS\b", re.I)),
    ("ATM", re.compile(r"\bATM\b", re.I)),
    ("INTEREST", re.compile(r"\bINT(?:ERES|\.PD|\.COLL|EREST)", re.I)),
    ("CHEQUE", re.compile(r"\bCHQ\b", re.I)),
)

_COUNTERPARTY = (
    re.compile(r"UPI/(?:DR|CR|P2[AM])/\d+/([^/]+)/", re.I),  # SBI and Axis
    re.compile(r"^UPI-([^-]+)-", re.I),  # HDFC
    re.compile(r"^IMPS-\d+-([^-]+)-", re.I),  # HDFC
    re.compile(r"^(?:ECOM PUR|POS)/([^/]+)/", re.I),  # Axis card purchases
    re.compile(r"\bINB ([A-Za-z][^/]*?) (?:t )?\d{8,}"),  # SBI net-banking transfers
)


def payment_mode(description: str) -> str:
    for mode, pattern in _MODES:
        if pattern.search(description):
            return mode
    return "OTHER"


def counterparty(description: str) -> str:
    """The other party, upper-cased with whitespace collapsed; empty when the narration names none."""
    text = " ".join(description.split())
    for pattern in _COUNTERPARTY:
        if match := pattern.search(text):
            return " ".join(match.group(1).split()).upper()
    return ""
