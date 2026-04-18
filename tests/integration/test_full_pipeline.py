"""End-to-end integration test: parsers -> dedup -> transfer detection.

Runs the actual pipeline stages against the combined extraction fixture and asserts
each stage produces sensible output. Marked `integration` so it can be opted into or
out of with `uv run pytest -m integration` / `-m "not integration"`.
"""

import pytest

from src.core.deduplicator import deduplicate
from src.core.orchestrator import extract_raw_transactions
from src.core.transfer_detector import detect_transfers
from src.models.transactions import Transaction
from tests.test_extraction.helpers import FIXTURES_ROOT


@pytest.mark.integration
def test_full_pipeline_end_to_end():
    case_dir = FIXTURES_ROOT / "extraction" / "raw_monthly_exports_2025_08_27" / "input"
    filepaths = [str(p) for p in sorted(case_dir.iterdir()) if p.is_file()]

    transactions = extract_raw_transactions(filepaths)
    assert len(transactions) > 0, "extraction produced no transactions"
    assert all(isinstance(t, Transaction) for t in transactions)

    deduped, skipped = deduplicate(transactions)
    assert len(deduped) <= len(transactions)
    assert len(deduped) + skipped == len(transactions)

    flagged = detect_transfers(deduped)
    assert len(flagged) == len(deduped), "transfer detection must not drop transactions"
    assert all(isinstance(t, Transaction) for t in flagged)
