"""Configuration loader tests."""

from pathlib import Path

import pytest

from src.config import DEFAULT_CONFIG_PATH, load_config, validate_config


def test_load_config_uses_repo_default_path():
    config = load_config()
    assert DEFAULT_CONFIG_PATH.exists()
    assert config["paths"]["input"] == "data/input"


def test_validate_config_rejects_missing_sections():
    with pytest.raises(ValueError, match="Required section 'external_accounts'"):
        validate_config(
            {
                "fipro": {},
                "paths": {},
                "processing": {"supported_extensions": ["xls"]},
                "banks": {},
            }
        )


def test_load_config_accepts_relative_path(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[fipro]
version = "0.1.0"
log_level = "INFO"

[paths]
input = "data/input"
output = "data/output"
processed = "data/processed"
failed = "data/failed"

[processing]
supported_extensions = ["xls", "xlsx"]

[banks.hdfc]
patterns = ["*hdfc*"]

[banks.sbi]
patterns = ["*sbi*"]

[banks.axis]
patterns = ["*axis*"]

[external_accounts]
names = ["CREDIT_CARD"]
payment_keywords = ["CREDIT CARD"]
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    config = load_config(Path("config.toml").as_posix())
    assert config["banks"]["axis"]["patterns"] == ["*axis*"]
