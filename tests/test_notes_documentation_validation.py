# pytest-based validation tests for the documentation-like file tests/test_notes.py
# Testing library and framework: pytest
#
# These tests validate structure and content expectations for the notes file.
# They are designed to provide meaningful coverage for a non-code artifact by:
# - Verifying presence and order of sections
# - Validating bullet list integrity
# - Checking for formatting issues (trailing whitespace, tabs)
# - Ensuring references to repository files exist (e.g., README.md)
# - Guarding against accidental introduction of secrets or TODOs
#
# We deliberately do not import tests/test_notes.py as Python code,
# because its content is prose/Markdown-like text. Instead, we read it as plain text.

import re
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTES_PATH = REPO_ROOT / "tests" / "test_notes.py"

def read_lines() -> List[str]:
    assert NOTES_PATH.exists(), f"Expected notes file at {NOTES_PATH} to exist."
    text = NOTES_PATH.read_text(encoding="utf-8", errors="replace")
    # Normalize newlines to avoid platform-specific issues
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

def read_text() -> str:
    return "\n".join(read_lines())

def section_indices(lines: List[str], header: str) -> List[int]:
    # Match lines like "# Project Notes" or "## Program Overview" (case-insensitive)
    pattern = re.compile(rf'^\s*#+\s*{re.escape(header)}\s*$', re.IGNORECASE)
    return [i for i, line in enumerate(lines) if pattern.match(line)]

def slice_section(lines: List[str], header: str, next_header: str = None) -> List[str]:
    starts = section_indices(lines, header)
    assert starts, f"Section header '{header}' not found."
    start = starts[0] + 1
    if next_header:
        ends = section_indices(lines, next_header)
        assert ends, f"Next section header '{next_header}' not found."
        end = ends[0]
        return lines[start:end]
    else:
        return lines[start:]

def extract_bullets(lines: List[str]) -> List[str]:
    # Capture top-level and indented bullets: "- " or "  - "
    return [ln for ln in lines if re.match(r'^\s{0,2}-\s+\S', ln)]

def test_notes_file_exists_and_is_text():
    assert NOTES_PATH.exists(), "Notes file should exist."
    # Ensure we can read text without decoding errors
    _ = read_text()

def test_expected_sections_present_and_in_order():
    lines = read_lines()
    expected = ["Project Notes", "Program Overview", "Bank Account Flow", "Future Considerations", "Notes"]
    found_positions = []
    for header in expected:
        idxs = section_indices(lines, header)
        assert idxs, f"Expected section '{header}' missing."
        found_positions.append(idxs[0])
    # Ensure sections are in ascending order
    assert found_positions == sorted(found_positions), (
        f"Sections out of order: expected {expected} "
        f"but found indices {found_positions}"
    )

def test_frequency_line_present_and_well_formed():
    text = read_text()
    # Match a markdown bold key then colon and value, e.g., **Frequency**: Monthly
    m = re.search(r'^\s*\*\*Frequency\*\*\s*:\s*(?P<val>.+?)\s*$', text, flags=re.MULTILINE)
    assert m, "Frequency line with '**Frequency**: <Value>' should be present."
    value = m.group("val").strip()
    assert value, "Frequency value must not be empty."
    # Accept typical values; at minimum should be a word
    assert re.match(r'^[A-Za-z][A-Za-z\s-]*$', value), f"Unexpected frequency value format: {value!r}"

def test_bank_account_flow_contains_expected_bullets_and_subbullets():
    lines = read_lines()
    section_lines = slice_section(lines, "Bank Account Flow", next_header="Future Considerations")
    bullets = extract_bullets(section_lines)
    assert bullets, "Expected bullet list under 'Bank Account Flow'."

    # Ensure primary flow bullet about downloading from 3 banks exists
    assert any(re.search(r'\bDownload transaction history from all\s+3\s+banks\b', b, flags=re.IGNORECASE) for b in bullets), \
        "Expected bullet about downloading transaction history from all 3 banks."

    # Ensure Axis Bank lead, and HDFC/SBI as sub-bullets are mentioned
    banks_required = ["Axis Bank", "HDFC Bank", "SBI Bank"]
    for bank in banks_required:
        assert any(bank.lower() in b.lower() for b in bullets), f"Expected mention of '{bank}' in bullets."

    # Check indentation rules for sub-bullets (allow up to 2 spaces)
    for b in bullets:
        assert re.match(r'^\s{0,2}-\s+\S', b), f"Bullet formatting should be '- ' with up to two leading spaces: {b!r}"

def test_future_considerations_contains_actionable_items():
    lines = read_lines()
    section_lines = slice_section(lines, "Future Considerations", next_header="Notes")
    bullets = extract_bullets(section_lines)
    assert bullets, "Expected bullets under 'Future Considerations'."
    # Ensure at least one item about DFS or PDF annotation or Budgeting exists
    keywords = ["DFS", "Digital Financial Services", "PDF", "credit card", "Budget"]
    assert any(any(kw.lower() in b.lower() for kw in keywords) for b in bullets), \
        "Expected actionable future considerations (DFS/PDF/Budgeting)."

def test_reference_to_readme_exists_in_repo():
    # The text references README; ensure README.md exists at repo root
    readme = REPO_ROOT / "README.md"
    assert readme.exists(), f"README.md not found at repository root: {readme}"

def test_no_trailing_whitespace_and_no_tabs():
    lines = read_lines()
    trailing = [i for i, ln in enumerate(lines, 1) if re.search(r'[ \t]+$', ln)]
    assert not trailing, f"Trailing whitespace found on lines: {trailing}"
    tabs = [i for i, ln in enumerate(lines, 1) if "\t" in ln]
    assert not tabs, f"Tab characters found on lines: {tabs}"

def test_no_unfinished_todos_or_fixmes():
    text = read_text()
    offenders = re.findall(r'\b(TODO|FIXME|XXX)\b', text, flags=re.IGNORECASE)
    assert not offenders, f"Found unfinished markers: {offenders}"

def test_no_obvious_secrets_or_tokens_present():
    text = read_text()
    # Very light heuristic checks
    forbidden_terms = [
        r'\bpassword\b', r'\bpasswd\b', r'\bsecret\b', r'\bapi[_-]?key\b', r'\btoken\b',
        r'AKIA[0-9A-Z]{16}',                      # AWS Access Key ID
        r'AIza[0-9A-Za-z\-_]{35}',                # Google API Key
        r'ghp_[0-9A-Za-z]{36,}',                  # GitHub token pattern
    ]
    for pat in forbidden_terms:
        assert not re.search(pat, text, flags=re.IGNORECASE), f"Potential secret detected by pattern: {pat}"

def test_lines_are_reasonably_short_to_maintain_readability():
    lines = read_lines()
    long_lines = [ (i, len(ln)) for i, ln in enumerate(lines, 1) if len(ln) > 200 ]
    assert not long_lines, f"Found lines exceeding 200 characters (readability): {long_lines}"

def test_markdown_headings_are_properly_prefixed():
    lines = read_lines()
    headings = [ln for ln in lines if re.match(r'^\s*#+\s+\S', ln)]
    # Ensure at least 3 heading lines exist and begin with '#' or '##'
    assert len(headings) >= 3, "Expected multiple Markdown headings."
    for h in headings:
        # Validate spacing after hashes
        assert re.match(r'^\s*#{1,6}\s+\S', h), f"Heading should have space after #: {h!r}"