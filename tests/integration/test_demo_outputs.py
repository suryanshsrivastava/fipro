import csv
from pathlib import Path

import pytest

from src.config import load_config
from src.core.orchestrator import process_pipeline
from tests.test_extraction.helpers import FIXTURES_ROOT


@pytest.mark.integration
def test_process_pipeline_writes_demo_outputs(tmp_path):
    fixture_input = FIXTURES_ROOT / "extraction" / "raw_monthly_exports_2025_08_27" / "input"
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    processed_dir = tmp_path / "processed"
    failed_dir = tmp_path / "failed"
    input_dir.mkdir()
    for fixture in fixture_input.iterdir():
        if fixture.is_file():
            (input_dir / fixture.name).write_bytes(fixture.read_bytes())

    config = load_config("config/config.toml")
    config["paths"]["input"] = str(input_dir)
    config["paths"]["output"] = str(output_dir)
    config["paths"]["processed"] = str(processed_dir)
    config["paths"]["failed"] = str(failed_dir)
    config["paths"]["dashboard_data"] = str(output_dir / "dashboard_data.csv")
    config["processing"]["seen_hashes_path"] = str(tmp_path / "state" / ".seen_hashes")

    run = process_pipeline(config)

    assert len(run.results) == 3
    assert (output_dir / "goodbudget_export.csv").exists()
    assert (output_dir / "dashboard_data.csv").exists()
    assert (output_dir / "processing_report.json").exists()
    assert sorted(p.name for p in processed_dir.iterdir()) == ["axis.xls", "hdfc.xls", "sbi.xls"]
    with (output_dir / "goodbudget_export.csv").open(newline="") as handle:
        goodbudget_rows = list(csv.DictReader(handle))
    with (output_dir / "dashboard_data.csv").open(newline="") as handle:
        dashboard_rows = list(csv.DictReader(handle))
    assert goodbudget_rows
    assert dashboard_rows
    assert list(goodbudget_rows[0].keys()) == ["Date", "Envelope", "Account", "Name", "Notes", "Amount", "Status"]
    assert "source_bank" not in goodbudget_rows[0]
    assert Path(dashboard_rows[0]["source_file"]).name == dashboard_rows[0]["source_file"]
    assert (tmp_path / "state" / ".seen_hashes").exists()
