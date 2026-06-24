from pathlib import Path

from src.core.pipeline_lifecycle import move_file_to_processed, move_processed_files, persist_failed_files


def test_move_processed_files_uses_injected_mover():
    moved: list[tuple[str, str]] = []
    move_processed_files(
        ["a.xls", "b.xls"],
        "processed",
        mover=lambda src, dest: moved.append((src, dest)) or src,
    )
    assert moved == [("a.xls", "processed"), ("b.xls", "processed")]


def test_persist_failed_files_uses_injected_mover():
    moved: list[tuple[str, str, str]] = []
    persist_failed_files(
        [("bad.xls", "parse failed")],
        "failed",
        mover=lambda src, dest, err: moved.append((src, dest, err)) or src,
    )
    assert moved == [("bad.xls", "failed", "parse failed")]


def test_move_file_to_processed_avoids_overwrite(tmp_path: Path):
    source = tmp_path / "input" / "hdfc.xls"
    source.parent.mkdir(parents=True)
    source.write_text("new statement")
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "hdfc.xls").write_text("old statement")

    destination = move_file_to_processed(str(source), str(processed))

    assert destination == str(processed / "hdfc_1.xls")
    assert (processed / "hdfc.xls").read_text() == "old statement"
    assert (processed / "hdfc_1.xls").read_text() == "new statement"
