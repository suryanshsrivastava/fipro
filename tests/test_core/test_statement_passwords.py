import json

import pytest

from src.core.statement_passwords import load_statement_passwords


def test_missing_file_means_no_saved_passwords(tmp_path):
    assert load_statement_passwords(str(tmp_path / "absent.json")) == {}


def test_banks_are_upper_cased_and_blank_values_dropped(tmp_path):
    path = tmp_path / "statement_passwords.json"
    path.write_text(json.dumps({"sbi": "secret", "AXIS": "", "HDFC": "other"}))

    assert load_statement_passwords(str(path)) == {"SBI": "secret", "HDFC": "other"}


def test_non_object_file_is_rejected_with_its_path(tmp_path):
    path = tmp_path / "statement_passwords.json"
    path.write_text('["sbi"]')

    with pytest.raises(ValueError, match="must be a JSON object"):
        load_statement_passwords(str(path))
