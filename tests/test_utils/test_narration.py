import pytest

from src.utils.narration import counterparty, payment_mode


@pytest.mark.parametrize(
    ("narration", "mode", "party"),
    [
        # SBI
        ("WDL TFR UPI/DR/921901619942/UBER IND/UTIB/uber @axisb/char 0097693162097", "UPI", "UBER IND"),
        ("DEP TFR UPI/CR/202906196077/PRIYANK /SBIN/832 8145692/NA 0093593162093", "UPI", "PRIYANK"),
        (
            "WDL TFR INB Bundl technologies Pvt L t 0099785162094 AT 16120 KAKROLA MOR",
            "NETBANKING",
            "BUNDL TECHNOLOGIES PVT L",
        ),
        ("DEP TFR INB IMPS906913351044/9999999999/XX2 374/m exp 0097963162095", "IMPS", ""),
        ("ATM WDL ATM CASH 5653 +DW ARK", "ATM", ""),
        ("INTERES T CREDIT", "INTEREST", ""),
        # HDFC: a hyphen follows the name, and names may contain spaces
        ("UPI-ADD MONEY TO WALLET-ADD-MONEY@PAYTM-PYTM0123456-311462049291-OID2023", "UPI", "ADD MONEY TO WALLET"),
        ("IMPS-200517945269-MR SURYANSH SRIVAS-SBIN-XXXXXXXXXXXXX1643-INETIMPS001", "IMPS", "MR SURYANSH SRIVAS"),
        # Axis
        ("UPI/P2M/530013618408/Bikaner sweets and ba/UPI/YES BANK LIMITED YBS", "UPI", "BIKANER SWEETS AND BA"),
        ("ECOM PUR/Bookmyshow/400049/040624/07:40/415607866153", "ECOM", "BOOKMYSHOW"),
        # A card purchase through an ATM-network terminal is a POS purchase, not a cash withdrawal.
        ("POS ATM PURCH OTHPG 72251364 9999", "POS", ""),
        ("CASH DEPOSIT SELF AT 16120 KAKROLA", "OTHER", ""),
    ],
)
def test_payment_mode_and_counterparty(narration, mode, party):
    assert payment_mode(narration) == mode
    assert counterparty(narration) == party
