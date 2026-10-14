def test_setting_reads_config_then_falls_back_to_defaults():
    from src.config import setting

    config = {"paths": {"output": "custom/out"}, "export": {"goodbudget": {"default_status": "pending"}}}

    assert setting(config, "paths.output") == "custom/out"
    assert setting(config, "paths.failed") == "data/failed"
    assert setting(config, "export.goodbudget.default_status") == "pending"
    assert setting(config, "export.goodbudget.default_envelope") == "Unallocated"
    assert setting({}, "gmail.queries") == {}
