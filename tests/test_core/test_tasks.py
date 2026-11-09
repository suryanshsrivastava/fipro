from datetime import date

from src.core.tasks import add_task, all_tasks, insight_tasks, set_task

TODAY = date(2026, 11, 10)
DUE = {"bank": "HDFC_REGALIA", "due": "2026-11-09", "total": 2378.0, "days": -1, "paid": False, "paid_amount": 0.0}


def _row(day, amount, bank="SBI", **extra):
    return {
        "transaction_date": day,
        "amount": str(amount),
        "source_bank": bank,
        "category": "",
        "status": "pending",
        "description": "x",
        **extra,
    }


def test_unpaid_bills_late_fees_and_old_statements_become_tasks_and_paid_bills_do_not():
    paid = {**DUE, "bank": "UNI_VISA", "paid": True}
    fee = _row("2026-10-13", -900, "HDFC_REGALIA", description="LATE FEE (Ref# 1)")
    titles = [t["title"] for t in insight_tasks([_row("2026-10-01", -10), fee], [DUE, paid], [], TODAY)]
    assert any("Pay the HDFC_REGALIA bill" in t for t in titles) and not any("UNI_VISA" in t for t in titles)
    assert any("late fees" in t for t in titles) and any("Download the SBI statement" in t for t in titles)


def test_work_claims_exclude_income_and_filed_rows_and_agent_tasks_carry_a_prompt():
    rows = [
        _row("2026-10-02", -500, category="Work/Travel"),
        _row("2026-10-03", 9000, category="Work/Income"),
        _row("2026-10-04", -300, category="Work/Stay", reimbursement="filed"),
    ]
    work = next(t for t in insight_tasks(rows, [], [], TODAY) if t["id"].startswith("work:"))
    assert work["id"] == "work:1" and work["owner"] == "agent" and "Do not file anything" in work["prompt"]


def test_status_and_notes_persist_per_task_id_and_manual_tasks_are_added(tmp_path):
    path = str(tmp_path / "tasks.csv")
    set_task(path, "bill:HDFC_REGALIA:2026-11-09", status="done", note="paid via CRED")
    mine = add_task(path, "Call HDFC about the EMI", "", "you", 1)
    tasks = {t["id"]: t for t in all_tasks([], [DUE], [], TODAY, path)}
    assert (
        tasks["bill:HDFC_REGALIA:2026-11-09"]["status"] == "done"
        and tasks["bill:HDFC_REGALIA:2026-11-09"]["note"] == "paid via CRED"
    )
    assert tasks[mine]["manual"] and tasks[mine]["status"] == "open"
    assert list(tasks)[-1] == "bill:HDFC_REGALIA:2026-11-09"  # finished tasks sink to the bottom
    try:
        set_task(path, mine, status="paused")
    except ValueError:
        return
    raise AssertionError("an unknown status must be refused")


def test_a_subscription_that_stopped_charging_is_flagged_but_an_active_one_is_not():
    rows = [_row(f"2026-0{m}-05", -199, category="Tech/Subscriptions", counterparty="NETFLIX") for m in (4, 5, 6)]
    rows += [_row(f"2026-0{m}-07", -99, category="Tech/Subscriptions", counterparty="SPOTIFY") for m in (4, 5, 6, 9)]
    rows.append(_row("2026-10-20", -10))  # the data runs to 20 Oct
    titles = [t["title"] for t in insight_tasks(rows, [], [], TODAY) if t["id"].startswith("stopped:")]
    assert titles == ["NETFLIX hasn't charged since 2026-06-05 (₹199)"]


def test_a_big_payment_to_a_new_payee_is_a_one_off_but_regulars_and_settlements_are_not():
    rows = [
        _row("2026-09-02", -20000, counterparty="LANDLORD"),
        _row("2026-10-02", -20000, counterparty="LANDLORD"),  # paid before: regular
        _row("2026-10-09", -8000, counterparty="NEW SHOP", hash="abc"),
        _row("2026-10-10", -9000, counterparty="A FRIEND", category="Settlements/Friends"),
        _row("2026-10-11", -300, counterparty="TEA"),
    ]
    found = [t for t in insight_tasks(rows, [], [], TODAY) if t["id"].startswith("oneoff:")]
    assert (
        [t["id"] for t in found] == ["oneoff:abc"]
        and found[0]["owner"] == "agent"
        and "Do not change" in found[0]["prompt"]
    )
