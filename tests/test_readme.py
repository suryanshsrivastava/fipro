"""
README documentation validation tests.

Testing framework: unittest (Python standard library).
Note: These tests validate the documentation content introduced/changed in the PR diff.
They assert the presence of key sections, examples, and guarantees described in the README.
"""

from pathlib import Path
import re
import unittest


def find_repo_root() -> Path:
    # tests/test_readme.py => repo root is parents[1]
    return Path(__file__).resolve().parents[1]


def find_readme_path(root: Path) -> Path:
    # Prefer common README filenames at the repository root
    candidates = [
        "README.md",
        "Readme.md",
        "readme.md",
        "README.MD",
        "README.rst",
        "README.txt",
        "README",
    ]
    for name in candidates:
        p = root / name
        if p.is_file():
            return p
    # Fallback: first README* file at root
    for p in sorted(root.glob("README*")):
        if p.is_file():
            return p
    raise FileNotFoundError("README file not found at repository root")


class TestReadmeDocumentation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = find_repo_root()
        cls.readme_path = find_readme_path(cls.root)
        cls.readme_text = cls.readme_path.read_text(encoding="utf-8", errors="ignore")

    # Helpers
    def _assert_contains_all(self, items, label):
        missing = [it for it in items if it not in self.readme_text]
        self.assertFalse(missing, f"Missing {label}: {missing}")

    def _assert_regex_all(self, patterns, label):
        missing = [pat for pat in patterns if re.search(pat, self.readme_text, flags=re.MULTILINE) is None]
        self.assertFalse(missing, f"Missing (regex) {label}: {missing}")

    # Existence and title
    def test_readme_exists_and_title_present(self):
        self.assertTrue(self.readme_path.exists(), "README file must exist at repository root")
        self.assertRegex(
            self.readme_text,
            r"(?m)^\s*#\s*Bank Statement Transaction Processor\s*$",
            "README should start with the expected top-level title",
        )

    # Required sections and sub-sections
    def test_required_sections_present(self):
        required_sections = [
            "## Features",
            "## Data Model",
            "### Transaction Fields",
            "## Components",
            "### 1. Transaction Line Grouping",
            "### 2. Transaction Parser",
            "### 3. Main Processing Pipeline",
            "## Validation",
            "## Error Handling",
            "## File Formats",
            "### Input",
            "### Output",
            "## Technical Details",
            "### Key Regular Expressions",
            "### Technical Constraints",
            "## Extension Points",
        ]
        self._assert_contains_all(required_sections, "sections/subsections")

    # Features list contents
    def test_features_list_contains_key_items(self):
        features = [
            "- Extracts transactions from bank statement text files",
            "- Handles multi-line transaction entries",
            "- Validates branch codes (Init.Br)",
            "- Correctly identifies debit/credit amounts",
            "- Maintains running balance accuracy",
            "- Outputs structured CSV format",
        ]
        self._assert_contains_all(features, "feature bullet points")

    # Transaction fields
    def test_transaction_fields_list_present(self):
        fields = [
            "- `Tran Date`",
            "- `Chq No`",
            "- `Particulars`",
            "- `Debit`",
            "- `Credit`",
            "- `Balance`",
            "- `Init. Br`",
        ]
        self._assert_contains_all(fields, "transaction fields")

    # Component function names are documented
    def test_component_function_names_listed(self):
        functions = [
            "`group_transaction_lines()`",
            "`parse_transaction()`",
            "`extract_transactions()`",
        ]
        self._assert_contains_all(functions, "component function names")

    # Steps in the Main Processing Pipeline
    def test_main_processing_pipeline_steps(self):
        steps_header = "Steps:"
        steps = [
            "1. Read input file",
            "2. Group transaction lines",
            "3. Parse transactions",
            "4. Write to CSV",
            "5. Validate output",
        ]
        self.assertIn(steps_header, self.readme_text, "Expected 'Steps:' header in the Components section")
        self._assert_contains_all(steps, "main processing steps")

    # Validation bullet points
    def test_validation_items_present(self):
        validation_items = [
            "- Number of transactions validation",
            "- First/Last transaction verification",
            "- Init. Br code validation (2177, 248, 100)",
            "- Balance calculation validation",
            "- Credit/Debit amount validation",
        ]
        self._assert_contains_all(validation_items, "validation bullet points")

    # Error handling bullet points
    def test_error_handling_items_present(self):
        error_items = [
            "- Graceful degradation for parsing errors",
            "- Data validation at each step",
            "- Balance consistency checks",
            "- Proper exception handling",
        ]
        self._assert_contains_all(error_items, "error handling bullet points")

    # Technical constraints and branch codes
    def test_technical_constraints_and_branch_codes(self):
        self.assertIn(
            "### Technical Constraints",
            self.readme_text,
            "Technical Constraints section should be present",
        )
        # Branch codes should be explicitly documented
        self.assertIn(
            "Supports three branch codes (2177, 248, 100)",
            self.readme_text,
            "Expected explicit mention of supported branch codes",
        )
        # The branch code token should appear with/without space after dot
        self.assertTrue(
            ("Init. Br" in self.readme_text) or ("Init.Br" in self.readme_text),
            "Expected 'Init. Br' or 'Init.Br' mention in README",
        )

    # Key regular expressions are present (as literal strings within code formatting)
    def test_key_regular_expressions_documented(self):
        regex_literals = [
            r"\d{2}-\d{2}-\d{4}",
            r"(\d+\.\d{2})\s+(\d+\.\d{2})?\s+(\d+\.\d{2})\s+",
        ]
        # Since README contains these as code snippets, assert literal presence
        self._assert_contains_all(regex_literals, "key regular expression literals")

    # Code blocks and python example presence
    def test_code_fences_and_python_block_present(self):
        # Count code fences (```), expect at least three blocks overall
        fences = re.findall(r"(?m)^\s*```", self.readme_text)
        self.assertGreaterEqual(
            len(fences), 3, f"Expected at least 3 code fences, found {len(fences)}"
        )
        # Ensure at least one python-annotated code block exists
        self.assertRegex(
            self.readme_text,
            r"(?m)^\s*```python\s*$",
            "Expected a python-annotated code block (```python)",
        )

    # Decimal/currency handling guidance
    def test_currency_precision_guidance_present(self):
        must_have = [
            "Currency Handling",
            "from decimal import Decimal, ROUND_HALF_UP",
            "Avoid floating-point arithmetic",
        ]
        self._assert_contains_all(must_have, "currency/Decimal guidance")
        # Ensure reference to 2-decimal precision exists
        self.assertRegex(
            self.readme_text,
            r"2[- ]?decimal",
            "Expected mention of 2-decimal precision for currency handling",
        )

    # Output CSV header format is documented
    def test_output_csv_header_documented(self):
        self.assertIn(
            "Tran Date,Chq No,Particulars,Debit,Credit,Balance,Init.Br",
            self.readme_text,
            "Expected CSV header line in Output section",
        )

    # Link to docs/NOTES.md is present and the file exists
    def test_docs_notes_link_exists_and_target_present(self):
        self.assertIn(
            "docs/NOTES.md",
            self.readme_text,
            "Expected a reference/link to docs/NOTES.md in README",
        )
        notes = self.root / "docs" / "NOTES.md"
        self.assertTrue(
            notes.exists(),
            f"Broken link: expected file does not exist: {notes}",
        )


if __name__ == "__main__":
    unittest.main()