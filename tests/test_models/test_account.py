"""Unit tests for Account and CrawledFile models."""

import os
import tempfile

import pytest

from src.models.account import Account, CrawledFile


class TestAccount:
    @pytest.fixture
    def savings_account(self):
        return Account(
            bank="HDFC",
            account_number="1234",
            nickname="Salary Account",
            account_type="savings",
        )

    @pytest.fixture
    def current_account(self):
        return Account(
            bank="AXIS",
            account_number="5678",
            nickname="Business Account",
            account_type="current",
            is_active=False,
        )

    def test_required_fields(self, savings_account):
        assert savings_account.bank == "HDFC"
        assert savings_account.account_number == "1234"
        assert savings_account.nickname == "Salary Account"
        assert savings_account.account_type == "savings"

    def test_default_is_active(self, savings_account):
        assert savings_account.is_active is True

    def test_is_active_can_be_set_false(self, current_account):
        assert current_account.is_active is False

    def test_different_account_types(self, savings_account, current_account):
        assert savings_account.account_type == "savings"
        assert current_account.account_type == "current"

    def test_different_banks(self, savings_account, current_account):
        assert savings_account.bank == "HDFC"
        assert current_account.bank == "AXIS"


class TestCrawledFile:
    @pytest.fixture
    def excel_file(self):
        return CrawledFile(
            filepath="/data/input/hdfc_jan_2025.xls",
            extension="xls",
            size=102400,
            crawl_date="2025-01-15T10:30:00",
        )

    @pytest.fixture
    def xlsx_file_with_metadata(self):
        return CrawledFile(
            filepath="/data/input/sbi_statement.xlsx",
            extension="xlsx",
            size=204800,
            crawl_date="2025-01-16T09:00:00",
            metadata={"account_number": "1234", "statement_period": "Jan 2025"},
        )

    def test_required_fields(self, excel_file):
        assert excel_file.filepath == "/data/input/hdfc_jan_2025.xls"
        assert excel_file.extension == "xls"
        assert excel_file.size == 102400
        assert excel_file.crawl_date == "2025-01-15T10:30:00"

    def test_default_metadata(self, excel_file):
        assert excel_file.metadata == {}

    def test_custom_metadata(self, xlsx_file_with_metadata):
        assert xlsx_file_with_metadata.metadata["account_number"] == "1234"
        assert xlsx_file_with_metadata.metadata["statement_period"] == "Jan 2025"

    def test_filename_property(self, excel_file):
        assert excel_file.filename == "hdfc_jan_2025.xls"

    def test_filename_property_nested_path(self):
        crawled = CrawledFile(
            filepath="/home/user/data/input/nested/folder/statement.xlsx",
            extension="xlsx",
            size=1024,
            crawl_date="2025-01-15T10:00:00",
        )
        assert crawled.filename == "statement.xlsx"

    def test_is_readable_with_existing_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xls") as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name

        try:
            crawled = CrawledFile(
                filepath=tmp_path,
                extension="xls",
                size=12,
                crawl_date="2025-01-15T10:00:00",
            )
            assert crawled.is_readable is True
        finally:
            os.unlink(tmp_path)

    def test_is_readable_with_nonexistent_file(self):
        crawled = CrawledFile(
            filepath="/nonexistent/path/file.xls",
            extension="xls",
            size=1024,
            crawl_date="2025-01-15T10:00:00",
        )
        assert crawled.is_readable is False

    def test_different_extensions(self):
        xls = CrawledFile(
            filepath="/data/file.xls",
            extension="xls",
            size=1024,
            crawl_date="2025-01-15T10:00:00",
        )
        xlsx = CrawledFile(
            filepath="/data/file.xlsx",
            extension="xlsx",
            size=2048,
            crawl_date="2025-01-15T10:00:00",
        )
        csv = CrawledFile(
            filepath="/data/file.csv",
            extension="csv",
            size=512,
            crawl_date="2025-01-15T10:00:00",
        )
        assert xls.extension == "xls"
        assert xlsx.extension == "xlsx"
        assert csv.extension == "csv"
