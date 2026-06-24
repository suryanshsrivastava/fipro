import shutil
from collections.abc import Callable
from pathlib import Path


def _unique_destination(path: Path) -> Path:
    candidate = path
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        counter += 1
    return candidate


def move_file_to_processed(source_path: str, dest_dir: str) -> str:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    dst = _unique_destination(dest / Path(source_path).name)
    shutil.move(source_path, dst)
    return str(dst)


def move_file_to_failed(source_path: str, dest_dir: str, error: str) -> str:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    dst = _unique_destination(dest / Path(source_path).name)
    shutil.move(source_path, dst)
    error_log = dst.with_name(dst.name + ".error.txt")
    error_log.write_text(error)
    return str(dst)


def move_processed_files(
    processed_files: list[str],
    processed_dir: str,
    *,
    mover: Callable[[str, str], str] = move_file_to_processed,
) -> None:
    for filepath in processed_files:
        mover(filepath, processed_dir)


def persist_failed_files(
    failures: list[tuple[str, str]],
    failed_dir: str,
    *,
    mover: Callable[[str, str, str], str] = move_file_to_failed,
) -> None:
    for filepath, error in failures:
        mover(filepath, failed_dir, error)
