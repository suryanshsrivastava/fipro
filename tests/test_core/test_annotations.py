from datetime import date
from decimal import Decimal

from src.core.annotations import apply_annotations, write_table
from src.models.transactions import Transaction, TransactionType


def _txn(description="UPI-RAVI KUMAR-ravi@ybl-HDFC0001-1-NA", amount="100"):
    return Transaction(date(2025, 1, 2), description, Decimal(amount), TransactionType.DEBIT, "HDFC", "a.xls")


def test_own_annotation_beats_counterparty_rule_and_rule_fills_the_rest(tmp_path):
    labelled, by_rule, unknown = _txn(amount="100"), _txn(amount="200"), _txn("UPI-SOMEONE ELSE-x@ybl-H-1-NA")
    annotations, rules = str(tmp_path / "annotations.csv"), str(tmp_path / "rules.csv")
    write_table(
        annotations,
        "hash",
        ("review_status", "category", "need_want", "frequency", "splitwise", "notes"),
        {
            labelled.hash: {
                "review_status": "reconciled",
                "category": "Family/Rent",
                "splitwise": "yes",
                "notes": "march",
            }
        },
    )
    write_table(
        rules,
        "counterparty",
        ("category", "need_want", "frequency"),
        {"ravi kumar": {"category": "City/Cab", "need_want": "Need", "frequency": "Monthly"}},  # matched upper-cased
    )

    apply_annotations([labelled, by_rule, unknown], annotations, rules)

    assert (labelled.category, labelled.need_want, labelled.frequency) == ("Family/Rent", "Need", "Monthly")
    assert (labelled.review_status, labelled.splitwise, labelled.notes) == ("reconciled", True, "march")
    assert (by_rule.category, by_rule.review_status, by_rule.splitwise) == ("City/Cab", "", False)
    assert (unknown.category, unknown.need_want) == (None, "")


def test_missing_label_files_leave_everything_unlabelled(tmp_path):
    txn = _txn()
    apply_annotations([txn], str(tmp_path / "none.csv"), str(tmp_path / "none2.csv"))
    assert txn.category is None and txn.review_status == ""


HASH = "0123456789abcdef"


def test_set_label_validates_and_clearing_the_last_label_removes_the_row(tmp_path):
    import pytest

    from src.core.annotations import read_table, set_label

    path = str(tmp_path / "annotations.csv")
    set_label(path, HASH, "review_status", "cleared")
    set_label(path, HASH, "notes", "  march rent  ")
    saved = {k: v for k, v in read_table(path, "hash")[HASH].items() if v}
    assert saved == {"hash": HASH, "review_status": "cleared", "notes": "march rent"}

    for field, value in [("review_status", "done"), ("need_want", "need"), ("nope", "x"), ("notes", "x" * 501)]:
        with pytest.raises(ValueError):
            set_label(path, HASH, field, value)
    with pytest.raises(ValueError):
        set_label(path, "not-a-hash", "notes", "x")

    set_label(path, HASH, "review_status", "")
    set_label(path, HASH, "notes", "")
    assert read_table(path, "hash") == {}


def _server(tmp_path):
    import threading

    from src.config import Settings
    from src.ui.dashboard import build_server

    csv_path = tmp_path / "dashboard_data.csv"
    csv_path.write_text(
        "hash,transaction_date,description,amount,transaction_type,source_bank,source_file,status,notes,balance,"
        "payment_mode,counterparty,category,review_status,need_want,frequency,splitwise\n"
        f"{HASH},2025-01-02,UPI-RAVI-x,-100,debit,HDFC,a.xls,pending,,5,UPI,RAVI,,,,,\n"
    )
    settings = Settings.from_config(
        {"paths": {"input": str(tmp_path), "annotations": str(tmp_path / "annotations.csv")}}
    )
    server = build_server(str(csv_path), 0, settings)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _post(server, body, headers=None):
    import json
    import urllib.error
    import urllib.request

    url = f"http://127.0.0.1:{server.server_address[1]}/annotate"
    request = urllib.request.Request(
        url, json.dumps(body).encode(), {"Content-Type": "application/json", **(headers or {})}, method="POST"
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def test_annotate_endpoint_saves_a_label_that_shows_on_reload_and_refuses_bad_requests(tmp_path):
    import json
    import urllib.request

    from src.core.annotations import read_table

    server = _server(tmp_path)
    try:
        assert _post(server, {"hash": HASH, "field": "category", "value": "City/Cab"}) == 200
        assert _post(server, {"hash": HASH, "field": "review_status", "value": "bogus"}) == 400
        assert _post(server, {"hash": HASH, "field": "category"}) == 400  # no value
        assert (
            _post(server, {"hash": HASH, "field": "category", "value": "x"}, {"Origin": "http://evil.example"}) == 403
        )

        assert read_table(str(tmp_path / "annotations.csv"), "hash")[HASH]["category"] == "City/Cab"
        data = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}/data").read())
        assert data[0]["category"] == "City/Cab"  # shown without re-running the pipeline
    finally:
        server.shutdown()
