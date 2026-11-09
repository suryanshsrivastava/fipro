from datetime import date
from decimal import Decimal

from src.core.rides import load_rides, match_rides, parse_receipt, save_rides
from src.models.transactions import Transaction, TransactionType

RAPIDO = (
    "Driver name REVANNA V Vehicle Number KA53 Time of Ride Nov 1st 2026, 2:08 PM Selected Price ₹ 66 Near, B Block"
)
UBER = "Nov 5, 2026 9:39 am Total ₹848.03 Booking fee ₹4.99 Suggested fare ₹640.04 Payments Cash ₹848.03 You rode with HARENDRA 4.97 Say thanks"
UBER_SEPT = "Sept 29, 2026 , 7:20 pm Thanks Total ₹312.50 Payments Visa ₹312.50 You rode with ASHA"


def _txn(day, amount, text):
    return Transaction(day, text, Decimal(amount), TransactionType.DEBIT, "HDFC", "f")


def test_receipts_parse_fare_time_driver_and_odd_month_spelling():
    assert parse_receipt("rapido", RAPIDO) == {
        "provider": "rapido",
        "day": "2026-11-01",
        "time": "14:08",
        "fare": "66",
        "fare_alt": "",
        "driver": "REVANNA V",
        "paid_with": "",
    }
    uber = parse_receipt("uber", UBER)
    assert uber and (uber["day"], uber["time"], uber["fare"], uber["fare_alt"], uber["driver"], uber["paid_with"]) == (
        "2026-11-05",
        "09:39",
        "848.03",
        "640.04",
        "HARENDRA",
        "Cash",
    )
    assert parse_receipt("uber", UBER_SEPT)["day"] == "2026-09-29"
    assert parse_receipt("uber", "Your verification code is 1234") is None


def test_rapido_needs_the_captains_name_and_a_close_fare_on_the_day():
    rides = [parse_receipt("rapido", RAPIDO)]
    hit = _txn(date(2026, 11, 1), "70", "UPI-REVANNA V-x@ybl-1-UPI")  # a tip of 4
    wrong_name = _txn(date(2026, 11, 1), "66", "UPI-SOMEONE ELSE-x@ybl-1-UPI")
    wrong_day = _txn(date(2026, 11, 4), "66", "UPI-REVANNA V-x@ybl-1-UPI")
    matched, unmatched = match_rides([wrong_name, wrong_day, hit], rides)
    assert (matched, unmatched) == (1, [])
    assert hit.category == "City/Cab" and "Rapido ride" in (hit.notes or "")
    assert wrong_name.category is None and wrong_day.category is None


def test_uber_matches_either_fare_but_only_with_a_driver_or_uber_in_the_narration():
    rides = [parse_receipt("uber", UBER)]
    base_fare = _txn(date(2026, 11, 5), "640.04", "UPI-HARENDRA SINGH-x@ybl-1-UPI")
    unrelated = _txn(date(2026, 11, 5), "848.03", "UPI-GROCER-x@ybl-1-UPI")
    assert match_rides([unrelated, base_fare], rides)[0] == 1
    assert base_fare.category == "City/Cab" and unrelated.category is None


def test_a_trip_nobody_paid_for_is_reported_unmatched_and_a_row_is_used_once(tmp_path):
    rides = [parse_receipt("rapido", RAPIDO), parse_receipt("rapido", RAPIDO.replace("Nov 1st", "Nov 2nd"))]
    one_payment = _txn(date(2026, 11, 1), "66", "UPI-REVANNA V-x@ybl-1-UPI")
    matched, unmatched = match_rides([one_payment], rides)
    assert matched == 1 and len(unmatched) == 1 and unmatched[0]["day"] == "2026-11-02"
    path = str(tmp_path / "rides.csv")
    assert save_rides(rides, path) == 2 and save_rides(rides, path) == 0
    assert len(load_rides(path)) == 2


def test_rapido_invoice_without_a_driver_parses_but_never_matches():
    invoice = "Time of Ride Nov 5th 2026, 6:57 PM Total ₹ 73.00 4.17 kms"
    ride = parse_receipt("rapido", invoice)
    assert ride and (ride["fare"], ride["driver"]) == ("73.00", "")
    assert match_rides([_txn(date(2026, 11, 5), "73", "UPI-ANYONE-x@ybl-1-UPI")], [ride])[0] == 0


def test_uber_paid_direct_to_the_named_driver_allows_a_rounded_up_fare_but_an_uber_charge_must_be_exact():
    rides = [parse_receipt("uber", UBER)]  # driver HARENDRA, fare 848.03 / 640.04
    rounded = _txn(date(2026, 11, 5), "650", "UPI-HARENDRA SINGH-x@ybl-1-UPI")
    far = _txn(date(2026, 11, 5), "700", "UPI-HARENDRA SINGH-x@ybl-1-UPI")
    uber_off = _txn(date(2026, 11, 5), "845", "UBER INDIA SYSTEMS")
    assert match_rides([far, uber_off, rounded], rides)[0] == 1 and rounded.category == "City/Cab"
    assert far.category is None and uber_off.category is None


def test_a_matched_ride_does_not_set_the_payment_time_but_names_the_trip_start():
    ride = parse_receipt("rapido", RAPIDO)
    paid = _txn(date(2026, 11, 1), "66", "UPI-REVANNA V-x@ybl-1-UPI")
    match_rides([paid], [ride])
    assert paid.time == "" and "14:08" in (paid.notes or "")
