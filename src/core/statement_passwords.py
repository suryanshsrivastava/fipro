"""Statement passwords saved on disk, keyed by bank, so locked statements need no re-entry.

The file holds the passwords themselves (unlike ``paths.password_hints``, which holds only the
sentence a bank's email uses to describe its password rule), so it lives under the gitignored
``corpus/`` directory by default.
"""

import json
from pathlib import Path


def load_statement_passwords(path: str) -> dict[str, str]:
    """Return bank -> statement password, or {} when no file has been saved yet.

    Keys are upper-cased to match the ``passwords`` mapping the pipeline expects (e.g. "SBI").
    Blank values are dropped so an empty entry means "not saved".
    """
    try:
        stored = json.loads(Path(path).read_text())
    except FileNotFoundError:
        return {}
    if not isinstance(stored, dict):
        raise ValueError(f"Statement passwords file must be a JSON object of bank -> password: {path}")
    return {str(bank).upper(): str(password) for bank, password in stored.items() if password}
