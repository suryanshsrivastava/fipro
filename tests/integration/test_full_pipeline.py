"""End-to-end integration test against the production pipeline seam."""

import pytest

from src.config import Settings
from src.core.orchestrator import process_pipeline
from src.models.transactions import Transaction
from tests.test_extraction.helpers import FIXTURES_ROOT


@pytest.mark.integration
def test_full_pipeline_end_to_end(tmp_path, fixture_input_loader, pipeline_config_factory):
    fixture_input = FIXTURES_ROOT / "extraction" / "raw_monthly_exports_2025_08_27" / "input"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"

    fixture_input_loader(fixture_input, input_dir)
    config = pipeline_config_factory(input_dir=input_dir, output_dir=output_dir)

    run = process_pipeline(Settings.from_config(config))

    assert len(run.results) == 3
    assert run.exported_count == len(run.export_transactions)
    assert run.exported_count <= len(run.deduplicated_transactions)
    assert all(isinstance(t, Transaction) for t in run.deduplicated_transactions)
    assert (output_dir / "goodbudget_export.csv").exists()
    # Statements stay put: input is the archive, so a run never moves them anywhere.
    assert sorted(p.name for p in input_dir.iterdir() if p.name != "audit_log.csv") == [
        "axis.xls",
        "hdfc.xls",
        "sbi.xls",
    ]


@pytest.mark.integration
def test_running_twice_produces_the_same_export(tmp_path, fixture_input_loader, pipeline_config_factory):
    """The pipeline is idempotent: re-running rebuilds the same export instead of emptying it."""
    fixture_input = FIXTURES_ROOT / "extraction" / "raw_monthly_exports_2025_08_27" / "input"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"

    fixture_input_loader(fixture_input, input_dir)
    config = pipeline_config_factory(input_dir=input_dir, output_dir=output_dir)
    settings = Settings.from_config(config)

    first = process_pipeline(settings)
    first_csv = (output_dir / "goodbudget_export.csv").read_text()
    second = process_pipeline(settings)

    assert second.exported_count == first.exported_count
    assert (output_dir / "goodbudget_export.csv").read_text() == first_csv
    assert sorted(p.name for p in input_dir.iterdir() if p.name != "audit_log.csv") == [
        "axis.xls",
        "hdfc.xls",
        "sbi.xls",
    ]
