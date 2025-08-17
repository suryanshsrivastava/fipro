"""
Tests for the repository's .gitignore ensuring critical patterns (from the PR diff)
remain intact and behave as expected.
Test framework: pytest
"""

from __future__ import annotations

from pathlib import Path
import re
import pytest


ROOT = Path(__file__).resolve().parents[1]
GITIGNORE = ROOT / ".gitignore"


def _read_gitignore_text() -> str:
    assert GITIGNORE.exists(), "Expected .gitignore to exist at the repository root"
    text = GITIGNORE.read_text(encoding="utf-8")
    return text


def _read_gitignore_lines() -> list[str]:
    return _read_gitignore_text().splitlines()


def _active_lines() -> list[str]:
    lines = _read_gitignore_lines()
    active = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        active.append(s)
    return active


def test_gitignore_exists_at_repo_root():
    assert GITIGNORE.exists(), "Missing .gitignore at repository root"


def test_gitignore_first_section_header_is_project_specific():
    # Ensure the first non-empty line is the project-specific header
    for ln in _read_gitignore_lines():
        if ln.strip():
            assert "Custom project-specific ignores" in ln, (
                "Expected first non-empty line to be a project-specific header comment"
            )
            break


def test_gitignore_has_no_trailing_whitespace_and_unix_newlines():
    text = _read_gitignore_text()
    # Must end with newline
    assert text.endswith("\n"), "Expected .gitignore to end with a newline"
    # No Windows CRLF carriage returns
    assert "\r" not in text, "Expected UNIX newlines only (no CR characters)"

    # No trailing spaces on any line
    for i, ln in enumerate(text.splitlines(), start=1):
        assert not re.search(r"[ \t]+$", ln), f"Trailing whitespace on line {i}"


def test_gitignore_required_project_specific_patterns_present_and_active():
    expected_active = {
        "fipro-env/",
        ".data",
        "data/",
        "v0-logs/",
    }
    active = set(_active_lines())
    missing = sorted(expected_active - active)
    assert not missing, f"Missing required project-specific patterns: {missing}"


def test_gitignore_core_python_and_tooling_patterns_present_and_active():
    expected_active = {
        # Byte-compiled / optimized / DLL files
        "__pycache__/",
        "*.py[cod]",
        "*$py.class",

        # C extensions
        "*.so",

        # Distribution / packaging
        ".Python",
        "build/",
        "develop-eggs/",
        "dist/",
        "downloads/",
        "eggs/",
        ".eggs/",
        "lib/",
        "lib64/",
        "parts/",
        "sdist/",
        "var/",
        "wheels/",
        "share/python-wheels/",
        "*.egg-info/",
        ".installed.cfg",
        "*.egg",
        "MANIFEST",

        # PyInstaller
        "*.manifest",
        "*.spec",

        # Installer logs
        "pip-log.txt",
        "pip-delete-this-directory.txt",

        # Unit test / coverage reports
        "htmlcov/",
        ".tox/",
        ".nox/",
        ".coverage",
        ".coverage.*",
        ".cache",
        "nosetests.xml",
        "coverage.xml",
        "*.cover",
        "*.py,cover",
        ".hypothesis/",
        ".pytest_cache/",
        "cover/",

        # Translations
        "*.mo",
        "*.pot",

        # Django stuff:
        "*.log",
        "local_settings.py",
        "db.sqlite3",
        "db.sqlite3-journal",

        # Flask stuff:
        "instance/",
        ".webassets-cache",

        # Scrapy stuff:
        ".scrapy",

        # Sphinx documentation
        "docs/_build/",

        # PyBuilder
        ".pybuilder/",
        "target/",

        # Jupyter Notebook
        ".ipynb_checkpoints",

        # IPython
        "profile_default/",
        "ipython_config.py",

        # PEP 582
        "__pypackages__/",

        # Celery stuff
        "celerybeat-schedule",
        "celerybeat.pid",

        # SageMath parsed files
        "*.sage.py",

        # Environments
        ".env",
        ".venv",
        "env/",
        "venv/",
        "ENV/",
        "env.bak/",
        "venv.bak/",

        # Spyder project settings
        ".spyderproject",
        ".spyproject",

        # Rope project settings
        ".ropeproject",

        # mkdocs documentation
        "/site",

        # mypy
        ".mypy_cache/",
        ".dmypy.json",
        "dmypy.json",

        # Pyre type checker
        ".pyre/",

        # pytype static type analyzer
        ".pytype/",

        # Cython debug symbols
        "cython_debug/",

        # Ruff
        ".ruff_cache/",

        # PyPI configuration file
        ".pypirc",
    }

    active = set(_active_lines())
    missing = sorted(expected_active - active)
    assert not missing, f"Missing required core/tooling patterns: {missing}"


def test_gitignore_lock_files_are_present_but_commented_out():
    """
    These lines are intentionally documented but disabled by default:
      - Pipfile.lock
      - uv.lock
      - poetry.lock
      - pdm.lock
      - .idea/
    Verify they exist as commented-out lines and are not active patterns.
    """
    lines = _read_gitignore_lines()
    active = set(_active_lines())

    commented_exact = [
        "Pipfile.lock",
        "uv.lock",
        "poetry.lock",
        "pdm.lock",
        ".idea/",
    ]

    for item in commented_exact:
        # Present as a comment line
        assert any(
            re.fullmatch(r"\s*#\s*" + re.escape(item) + r"\s*", ln)
            for ln in lines
        ), f'Expected commented line for "{item}" in .gitignore'
        # Not present as an active pattern
        assert item not in active, f'Pattern "{item}" should be commented out, not active'


def test_gitignore_has_section_headers_in_expected_order():
    """
    Sanity check that major section headers from the PR diff exist and
    appear in a sensible order. This guards against accidental reshuffling.
    """
    text = _read_gitignore_text()
    # Use substrings that appear at the start of section comments in the diff.
    headers = [
        "Custom project-specific ignores",
        "Byte-compiled / optimized / DLL files",
        "C extensions",
        "Distribution / packaging",
        "PyInstaller",
        "Installer logs",
        "Unit test / coverage reports",
        "Translations",
        "Django stuff:",
        "Flask stuff:",
        "Scrapy stuff:",
        "Sphinx documentation",
        "PyBuilder",
        "Jupyter Notebook",
        "IPython",
        "pyenv",
        "pipenv",
        "UV",
        "poetry",
        "pdm",
        "PEP 582; used by e.g. github.com/David-OConnor/pyflow and github.com/pdm-project/pdm",
        "Celery stuff",
        "SageMath parsed files",
        "Environments",
        "Spyder project settings",
        "Rope project settings",
        "mkdocs documentation",
        "mypy",
        "Pyre type checker",
        "pytype static type analyzer",
        "Cython debug symbols",
        "PyCharm",
        "Ruff stuff:",
        "PyPI configuration file",
    ]

    positions = []
    for h in headers:
        idx = text.find(h)
        assert idx != -1, f'Missing expected section header containing "{h}"'
        positions.append(idx)

    # Ensure headers appear in ascending order
    assert positions == sorted(positions), "Section headers appear out of order"


def test_gitignore_has_no_duplicate_active_patterns():
    active = _active_lines()
    seen = {}
    dups = set()
    for ln in active:
        seen[ln] = seen.get(ln, 0) + 1
        if seen[ln] > 1:
            dups.add(ln)
    assert not dups, f"Duplicate active ignore patterns found: {sorted(dups)}"


def test_gitignore_semantics_with_pathspec_if_available():
    """
    If the optional 'pathspec' package is available, validate a few matching behaviors.
    This test is skipped automatically if pathspec is not installed.
    """
    pathspec = pytest.importorskip("pathspec", reason="Install pathspec to run semantic matching tests")

    # Build a spec from active (non-comment) lines
    active = _active_lines()
    spec = pathspec.PathSpec.from_lines("gitwildmatch", active)

    # Positive matches (should be ignored)
    assert spec.match_file("data/example.csv")
    assert spec.match_file("nested/data/table.parquet")
    assert spec.match_file("__pycache__/module.cpython-311.pyc")
    assert spec.match_file("docs/_build/html/index.html")
    assert spec.match_file("venv/bin/activate")
    assert spec.match_file("lib/some_module.py")
    assert spec.match_file("cython_debug/some_debug_file")

    # Anchored root-only ignore (/site)
    assert spec.match_file("site/index.html")
    assert not spec.match_file("docs/site/index.html"), "Anchored '/site' should not match nested directories"

    # Commented lock files should not match
    assert not spec.match_file("poetry.lock")
    assert not spec.match_file("uv.lock")
    assert not spec.match_file("Pipfile.lock")
    assert not spec.match_file("pdm.lock")

    # Ensure '.data' matches file or folder named exactly '.data'
    assert spec.match_file(".data")
    assert not spec.match_file("data.txt"), "'.data' should not match 'data.txt'"
