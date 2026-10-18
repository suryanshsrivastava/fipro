from dataclasses import replace
from pathlib import Path

import pytest

from src.config import GmailSettings, PathSettings, Settings, load_config, load_settings

SHIPPED_CONFIG = Path(__file__).resolve().parents[1] / "config" / "config.toml"


def test_settings_reads_config_then_falls_back_to_defaults():
    settings = Settings.from_config(
        {"paths": {"input": "in", "output": "custom/out"}, "export": {"goodbudget": {"default_status": "pending"}}}
    )

    assert settings.paths.input == "in"
    assert settings.paths.output == "custom/out"
    assert settings.paths.password_hints == "corpus/password_hints.json"
    assert settings.goodbudget.default_status == "pending"
    assert settings.goodbudget.default_envelope == "Unallocated"
    assert settings.gmail.queries == {}
    assert settings.log_level == "INFO"


def test_input_path_is_required():
    with pytest.raises(ValueError, match="paths.input"):
        Settings.from_config({"paths": {"output": "out"}})


def test_empty_extension_list_means_unset():
    config = {"paths": {"input": "in"}, "processing": {"supported_extensions": []}}

    assert Settings.from_config(config).processing.supported_extensions == ("xls", "xlsx")


def test_internal_transfer_flags_resolve_to_one_value():
    def export(processing: dict) -> bool:
        return Settings.from_config(
            {"paths": {"input": "in"}, "processing": processing}
        ).processing.export_internal_transfers

    assert export({}) is True
    assert export({"include_internal_transfers": False}) is False
    assert export({"skip_internal_transfers": True}) is False
    assert export({"skip_internal_transfers": False}) is True
    # An explicit include flag wins over the legacy skip flag.
    assert export({"include_internal_transfers": True, "skip_internal_transfers": True}) is True


def test_reads_external_accounts():
    settings = Settings.from_config(
        {"paths": {"input": "in"}, "external_accounts": {"names": ["CC"], "payment_keywords": ["CRED"]}}
    )

    assert settings.external_accounts.names == ("CC",)
    assert settings.external_accounts.payment_keywords == ("CRED",)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("gmail", "max_messages", "10"),
        ("gmail", "max_messages", True),
        ("processing", "fail_on_file_error", "yes"),
        ("processing", "supported_extensions", "xls"),
        ("external_accounts", "names", [1]),
    ],
)
def test_wrongly_typed_values_are_rejected_with_their_key(section, key, value):
    with pytest.raises(ValueError, match=f"{section}.{key}"):
        Settings.from_config({"paths": {"input": "in"}, section: {key: value}})


def test_defaults_match_shipped_config_toml():
    shipped = load_settings(str(SHIPPED_CONFIG))
    defaults = Settings(PathSettings(input=shipped.paths.input))

    # The shipped file only adds values that have no sensible built-in default.
    assert shipped.paths == defaults.paths
    assert shipped.processing == defaults.processing
    assert shipped.goodbudget == defaults.goodbudget
    assert shipped.log_level == defaults.log_level
    assert replace(shipped.gmail, queries={}) == GmailSettings()


def test_queries_are_a_read_only_copy_of_the_config_table():
    table = {"SBI": "from:sbi.co.in password"}
    settings = Settings.from_config({"paths": {"input": "in"}, "gmail": {"queries": table}})

    table["AXIS"] = "from:axisbank.com"

    assert dict(settings.gmail.queries) == {"SBI": "from:sbi.co.in password"}
    with pytest.raises(TypeError):
        settings.gmail.queries["X"] = "y"  # type: ignore[index]


def test_queries_values_must_be_strings():
    with pytest.raises(ValueError, match="gmail.queries"):
        Settings.from_config({"paths": {"input": "in"}, "gmail": {"queries": {"SBI": 5}}})


def test_load_config_still_returns_the_raw_dict():
    assert load_config(str(SHIPPED_CONFIG))["paths"]["input"] == load_settings(str(SHIPPED_CONFIG)).paths.input
