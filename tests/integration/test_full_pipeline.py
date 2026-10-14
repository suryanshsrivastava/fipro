"""End-to-end integration test against the production pipeline seam."""

import pytest

from src.core.orchestrator import process_pipeline
from src.models.transactions import Transaction
from tests.test_extraction.helpers import FIXTURES_ROOT


@pytest.mark.integration
def test_full_pipeline_end_to_end(tmp_path, fixture_input_loader, pipeline_config_factory):
    fixture_input = FIXTURES_ROOT / "extraction" / "raw_monthly_exports_2025_08_27" / "input"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    processed_dir = tmp_path / "processed"

    fixture_input_loader(fixture_input, input_dir)
    config = pipeline_config_factory(input_dir=input_dir, output_dir=output_dir, processed_dir=processed_dir)

    run = process_pipeline(config)

    assert len(run.results) == 3
    assert run.exported_count == len(run.export_transactions)
    assert run.exported_count <= len(run.deduplicated_transactions)
    assert all(isinstance(t, Transaction) for t in run.deduplicated_transactions)
    assert (output_dir / "goodbudget_export.csv").exists()
    assert sorted(p.name for p in processed_dir.iterdir()) == ["axis.xls", "hdfc.xls", "sbi.xls"]
