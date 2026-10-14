from pathlib import Path

from src.core.pipeline_lifecycle import move_file_to_processed, move_processed_files, persist_failed_files


def test_move_processed_files_moves_each_file(tmp_path: Path):
    sources = [tmp_path / "a.xls", tmp_path / "b.xls"]
    for source in sources:
        source.write_text(source.name)

    move_processed_files([str(s) for s in sources], str(tmp_path / "processed"))

    assert sorted(p.name for p in (tmp_path / "processed").iterdir()) == ["a.xls", "b.xls"]
    assert not any(s.exists() for s in sources)


def test_persist_failed_files_writes_error_log(tmp_path: Path):
    bad = tmp_path / "bad.xls"
    bad.write_text("x")

    persist_failed_files([(str(bad), "parse failed")], str(tmp_path / "failed"))

    assert (tmp_path / "failed" / "bad.xls").exists()
    assert (tmp_path / "failed" / "bad.xls.error.txt").read_text() == "parse failed"


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
