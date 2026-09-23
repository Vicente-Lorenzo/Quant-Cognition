import shutil

import pytest

from Library.Utility.IO import remove, tail_text

def test_remove_deletes_files_and_folders(tmp_path):
    folder = tmp_path / "Folder"
    (folder / "Nested").mkdir(parents=True)
    (folder / "Nested" / "File.txt").write_text("x")
    single = tmp_path / "Single.txt"
    single.write_text("x")
    assert remove(single) is True
    assert remove(folder, safe=False) is True
    assert not single.exists() and not folder.exists()

def test_tail_text_reads_only_the_last_bytes(tmp_path):
    path = tmp_path / "Run.log"
    path.write_bytes("first line\nsecond line · done\n".encode("utf-8"))
    assert tail_text(path, 1000) == "first line\nsecond line · done\n"
    assert tail_text(path, 5) == "done\n"
    assert tail_text(tmp_path / "Missing.log", 5) == ""

def test_remove_of_a_missing_path_succeeds(tmp_path):
    assert remove(tmp_path / "Absent", safe=False) is True

def test_remove_reports_a_folder_that_survives(tmp_path, monkeypatch):
    folder = tmp_path / "Locked"
    folder.mkdir()
    monkeypatch.setattr(shutil, "rmtree", lambda path, onerror=None: None)
    assert remove(folder) is False
    with pytest.raises(OSError, match="Failed to remove"):
        remove(folder, safe=False)
    assert folder.exists()