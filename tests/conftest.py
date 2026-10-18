from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.config import load_config


def _copy_fixture_files(source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for fixture in source_dir.iterdir():
        if fixture.is_file():
            shutil.copy2(fixture, target_dir / fixture.name)


@pytest.fixture
def fixture_input_loader():
    return _copy_fixture_files


@pytest.fixture
def pipeline_config_factory(tmp_path: Path):
    def _build(
        *,
        input_dir: Path,
        output_dir: Path | None = None,
        fail_on_file_error: bool = True,
        include_internal_transfers: bool = True,
    ) -> dict:
        config = load_config("config/config.toml")

        output_path = output_dir or (tmp_path / "output")

        config["paths"]["input"] = str(input_dir)
        config["paths"]["output"] = str(output_path)
        config["paths"]["dashboard_data"] = str(output_path / "dashboard_data.csv")
        config["processing"]["fail_on_file_error"] = fail_on_file_error
        config["processing"]["include_internal_transfers"] = include_internal_transfers
        return config

    return _build
