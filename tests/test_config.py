from dataclasses import asdict
from pathlib import Path

from src.config import Settings, load_config


def test_settings_reads_config_then_falls_back_to_defaults():
    config = {"paths": {"output": "custom/out"}, "export": {"goodbudget": {"default_status": "pending"}}}

    settings = Settings.from_config(config)

    assert settings.output == "custom/out"
    assert settings.failed == "data/failed"
    assert settings.default_status == "pending"
    assert settings.default_envelope == "Unallocated"
    assert settings.gmail_queries == {}


def test_settings_treats_empty_extension_list_as_unset():
    assert Settings.from_config({"processing": {"supported_extensions": []}}).supported_extensions == ("xls", "xlsx")


def test_settings_defaults_match_shipped_config_toml():
    config = load_config(str(Path(__file__).resolve().parents[1] / "config" / "config.toml"))

    shipped, defaults = asdict(Settings.from_config(config)), asdict(Settings())

    # The shipped config only adds Gmail search queries on top of the defaults.
    assert {k: v for k, v in shipped.items() if k != "gmail_queries"} == {
        k: v for k, v in defaults.items() if k != "gmail_queries"
    }


def test_settings_rejects_wrongly_typed_values():
    import pytest

    with pytest.raises(ValueError, match="gmail.max_messages"):
        Settings.from_config({"gmail": {"max_messages": "10"}})
    with pytest.raises(ValueError, match="processing.fail_on_file_error"):
        Settings.from_config({"processing": {"fail_on_file_error": "yes"}})
    with pytest.raises(ValueError, match="gmail.max_messages"):
        Settings.from_config({"gmail": {"max_messages": True}})
