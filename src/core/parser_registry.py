import io
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import msoffcrypto
import pandas as pd
from msoffcrypto.exceptions import DecryptionError, FileFormatError, InvalidKeyError
from msoffcrypto.format.ooxml import OOXMLFile

from src.models.transactions import Transaction
from src.parsers.axis import AXIS_LAYOUT
from src.parsers.base import BankParser
from src.parsers.hdfc import HDFC_LAYOUT
from src.parsers.sbi import SBI_LAYOUT, load_sbi_file
from src.parsers.tabular import BankLayout, TabularStatementParser

_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_DEFAULT_PASSWORD_ENV_VAR = "FIPRO_STATEMENT_PASSWORD"


class StatementLockedError(ValueError):
    """A password-protected statement had no usable password; the file is left in the input folder."""


def is_encrypted_statement(filepath: str) -> bool:
    """Password-protected .xls/.xlsx files are OLE containers flagged as encrypted."""
    with open(filepath, "rb") as f:
        if f.read(len(_OLE_MAGIC)) != _OLE_MAGIC:
            return False
        f.seek(0)
        try:
            return bool(msoffcrypto.OfficeFile(f).is_encrypted())
        except FileFormatError:
            return False


def _decrypt_statement(filepath: str, bank: str, passwords: dict[str, str]) -> io.BytesIO:
    """Decrypt a password-protected statement in memory; the decrypted bytes never touch disk.

    The password comes from ``passwords[bank]`` (entered in the dashboard), else the
    ``FIPRO_<BANK>_STATEMENT_PASSWORD`` / ``FIPRO_STATEMENT_PASSWORD`` environment variables.
    """
    name = Path(filepath).name
    bank_env_var = f"FIPRO_{bank}_STATEMENT_PASSWORD"
    if passwords.get(bank):
        source, password = "the password entered for " + bank, passwords[bank]
    else:
        source = bank_env_var if os.environ.get(bank_env_var) else _DEFAULT_PASSWORD_ENV_VAR
        password = os.environ.get(source, "")
    if not password:
        raise StatementLockedError(
            f"{name} is password-protected; unlock it in `fipro dashboard` or set {bank_env_var} or {_DEFAULT_PASSWORD_ENV_VAR}"
        )

    decrypted = io.BytesIO()
    with open(filepath, "rb") as f:
        try:
            office_file = msoffcrypto.OfficeFile(f)
            # Only OOXML's load_key accepts verify_password; legacy .xls verifies on its own.
            kwargs = {"verify_password": True} if isinstance(office_file, OOXMLFile) else {}
            office_file.load_key(password=password, **kwargs)
            office_file.decrypt(decrypted)
        except (InvalidKeyError, DecryptionError) as exc:
            raise StatementLockedError(f"Could not decrypt {name}: wrong password in {source}") from exc
    decrypted.seek(0)
    return decrypted


def _load_excel_statement(filepath: str) -> pd.DataFrame:
    suffix = Path(filepath).suffix.lower()
    if suffix not in {".xls", ".xlsx"}:
        raise ValueError(f"Unsupported format: {filepath}")
    engine = "xlrd" if suffix == ".xls" else "openpyxl"
    return pd.read_excel(filepath, engine=engine, header=None)


def _load_sbi_statement(filepath: str) -> pd.DataFrame:
    dataframe = load_sbi_file(filepath)
    if dataframe is None:
        raise ValueError(f"Unable to load SBI statement: {filepath}")
    return dataframe


@dataclass(frozen=True, slots=True)
class ParserAdapter:
    parser: BankParser
    filename_markers: tuple[str, ...]
    loader: Callable[[str], pd.DataFrame]

    def matches_filename(self, filename: str) -> bool:
        lower_name = filename.lower()
        return any(marker in lower_name for marker in self.filename_markers)


def _adapter(layout: BankLayout, loader: Callable[[str], pd.DataFrame]) -> ParserAdapter:
    return ParserAdapter(
        parser=TabularStatementParser(layout), filename_markers=(layout.filename_marker,), loader=loader
    )


@dataclass(slots=True)
class ExtractedStatement:
    parser: BankParser
    dataframe: pd.DataFrame
    transactions: list[Transaction]


class ParserRegistry:
    def __init__(self, adapters: list[ParserAdapter] | None = None) -> None:
        self._adapters = adapters or [
            _adapter(HDFC_LAYOUT, _load_excel_statement),
            _adapter(SBI_LAYOUT, _load_sbi_statement),
            _adapter(AXIS_LAYOUT, _load_excel_statement),
        ]

    def parsers(self) -> list[BankParser]:
        return [adapter.parser for adapter in self._adapters]

    def infer_bank_from_filename(self, filename: str) -> str:
        for adapter in self._adapters:
            if adapter.matches_filename(filename):
                return adapter.parser.bank_name
        return "UNKNOWN"

    def parser_for_bank(self, bank: str) -> BankParser:
        bank_name = bank.upper()
        for adapter in self._adapters:
            if adapter.parser.bank_name == bank_name:
                return adapter.parser
        raise ValueError(f"No parser registered for bank: {bank}")

    def load_dataframe(
        self, filepath: str, *, bank_hint: str | None = None, passwords: dict[str, str] | None = None
    ) -> pd.DataFrame:
        if is_encrypted_statement(filepath):
            decrypted = _decrypt_statement(filepath, bank_hint or "UNKNOWN", passwords or {})
            return pd.read_excel(decrypted, header=None)
        if bank_hint:
            bank_name = self.parser_for_bank(bank_hint).bank_name
            loader_adapter = next(a for a in self._adapters if a.parser.bank_name == bank_name)
            return loader_adapter.loader(filepath)
        for adapter in self._adapters:
            if adapter.matches_filename(Path(filepath).name):
                return adapter.loader(filepath)
        return _load_excel_statement(filepath)

    def route_parser(
        self, filename: str, dataframe: pd.DataFrame, parsers: list[BankParser] | None = None
    ) -> BankParser:
        available_parsers = parsers or self.parsers()
        for parser in available_parsers:
            if parser.can_parse(filename, dataframe):
                return parser
        raise ValueError(f"No parser available for {filename}")

    def extract_transactions(
        self,
        filepath: str,
        *,
        bank_hint: str | None = None,
        passwords: dict[str, str] | None = None,
        route_name: str | None = None,
    ) -> ExtractedStatement:
        """Load, decrypt if needed, route and parse one statement.

        ``route_name`` overrides the filename used for parser routing (e.g. an input-relative
        path so a bank folder counts as a hint). Raises StatementLockedError when locked.
        """
        dataframe = self.load_dataframe(filepath, bank_hint=bank_hint, passwords=passwords)
        parser = self.route_parser(route_name or Path(filepath).name, dataframe)
        transactions = parser.extract_transactions(dataframe, filepath)
        return ExtractedStatement(parser=parser, dataframe=dataframe, transactions=transactions)


def get_default_parser_registry() -> ParserRegistry:
    return ParserRegistry()
