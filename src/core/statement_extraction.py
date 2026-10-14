import logging
import os
from dataclasses import dataclass, field
from typing import Protocol

from src.core.parser_registry import ExtractedStatement, StatementLockedError
from src.models.account import CrawledFile
from src.models.result import ProcessingResult
from src.models.transactions import Transaction

logger = logging.getLogger("fipro.extraction")


@dataclass(slots=True)
class ExtractionBatch:
    all_transactions: list[Transaction]
    processed_files: list[str]
    failures: list[tuple[str, str]]
    results: list[ProcessingResult]
    locked_files: list[str] = field(default_factory=list)


class StatementParserRegistry(Protocol):
    def extract_transactions(
        self,
        filepath: str,
        *,
        bank_hint: str | None = None,
        passwords: dict[str, str] | None = None,
        route_name: str | None = None,
    ) -> ExtractedStatement: ...


def extract_from_crawled_files(
    crawled_files: list[CrawledFile],
    *,
    parser_registry: StatementParserRegistry,
    input_path: str | None = None,
    passwords: dict[str, str] | None = None,
) -> ExtractionBatch:
    all_transactions: list[Transaction] = []
    processed_files: list[str] = []
    failures: list[tuple[str, str]] = []
    results: list[ProcessingResult] = []
    locked_files: list[str] = []

    for crawled in crawled_files:
        try:
            bank_hint = str(crawled.metadata.get("bank", "")).strip() or None
            route_name = os.path.relpath(crawled.filepath, input_path) if input_path else None
            extracted = parser_registry.extract_transactions(
                crawled.filepath, bank_hint=bank_hint, passwords=passwords, route_name=route_name
            )
            txns = extracted.transactions
            all_transactions.extend(txns)
            processed_files.append(crawled.filepath)
            results.append(
                ProcessingResult(
                    source_file=crawled.filepath,
                    bank=extracted.parser.bank_name,
                    total_transactions=len(txns),
                    successful=len(txns),
                    failed=0,
                    duplicates_skipped=0,
                    transactions=txns,
                    errors=[],
                    warnings=[],
                )
            )
        except StatementLockedError as e:
            logger.warning("Skipping %s: %s", crawled.filepath, e)
            locked_files.append(crawled.filepath)
            results.append(
                ProcessingResult(
                    source_file=crawled.filepath,
                    bank=crawled.metadata.get("bank", "UNKNOWN"),
                    total_transactions=0,
                    successful=0,
                    failed=0,
                    duplicates_skipped=0,
                    transactions=[],
                    errors=[],
                    warnings=[str(e)],
                )
            )
        except Exception as e:
            error = str(e)
            logger.error("Failed processing %s: %s", crawled.filepath, error)
            failures.append((crawled.filepath, error))
            results.append(
                ProcessingResult(
                    source_file=crawled.filepath,
                    bank=crawled.metadata.get("bank", "UNKNOWN"),
                    total_transactions=0,
                    successful=0,
                    failed=1,
                    duplicates_skipped=0,
                    transactions=[],
                    errors=[error],
                    warnings=[],
                )
            )

    return ExtractionBatch(
        all_transactions=all_transactions,
        processed_files=processed_files,
        failures=failures,
        results=results,
        locked_files=locked_files,
    )
