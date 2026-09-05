import os
import time
from pathlib import Path

from Setup.Retention import prune_files, _DAYS_

def _age_(path: Path, days: float) -> None:
    moment = time.time() - days * 86400
    os.utime(path, (moment, moment))

def test_prunes_expired_log_files(tmp_path):
    stale = tmp_path / "Ancient.log"
    stale.write_text("old", encoding="utf-8")
    _age_(stale, 40)
    removed, reclaimed = prune_files(folders=(tmp_path,), days=30)
    assert removed == 1
    assert reclaimed == 3
    assert not stale.exists()

def test_keeps_recent_log_files(tmp_path):
    recent = tmp_path / "Recent.log"
    recent.write_text("new", encoding="utf-8")
    removed, _ = prune_files(folders=(tmp_path,), days=30)
    assert removed == 0
    assert recent.exists()

def test_prunes_rotated_backups(tmp_path):
    for suffix in ("log", "log.1", "log.2"):
        candidate = tmp_path / f"Rotated.{suffix}"
        candidate.write_text("old", encoding="utf-8")
        _age_(candidate, 90)
    removed, _ = prune_files(folders=(tmp_path,), days=30)
    assert removed == 3

def test_prunes_every_extension_the_framework_writes(tmp_path):
    for name in ("Report.csv", "Plot.html", "Trace.pstat", "Run.log"):
        candidate = tmp_path / name
        candidate.write_text("data", encoding="utf-8")
        _age_(candidate, 400)
    removed, _ = prune_files(folders=(tmp_path,), days=30)
    assert removed == 4
    assert not any(tmp_path.iterdir())

def test_prunes_stale_export_subfolders(tmp_path):
    nested = tmp_path / "2020-01-01 run"
    nested.mkdir()
    (nested / "trades.csv").write_text("data", encoding="utf-8")
    _age_(nested / "trades.csv", 400)
    _age_(nested, 400)
    removed, _ = prune_files(folders=(tmp_path,), days=30)
    assert removed == 1
    assert not nested.exists()

def test_keeps_a_folder_with_fresh_content(tmp_path):
    nested = tmp_path / "active run"
    nested.mkdir()
    (nested / "trades.csv").write_text("data", encoding="utf-8")
    _age_(nested, 400)
    removed, _ = prune_files(folders=(tmp_path,), days=30)
    assert removed == 0
    assert nested.exists()

def test_missing_folder_is_skipped(tmp_path):
    removed, reclaimed = prune_files(folders=(tmp_path / "absent",), days=30)
    assert (removed, reclaimed) == (0, 0)

def test_multiple_folders_are_swept(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir(), second.mkdir()
    for folder in (first, second):
        candidate = folder / "Ancient.log"
        candidate.write_text("old", encoding="utf-8")
        _age_(candidate, 90)
    removed, _ = prune_files(folders=(first, second), days=30)
    assert removed == 2

def test_zero_days_prunes_everything(tmp_path):
    candidate = tmp_path / "Fresh.log"
    candidate.write_text("new", encoding="utf-8")
    _age_(candidate, 0.001)
    removed, _ = prune_files(folders=(tmp_path,), days=0)
    assert removed == 1

def test_default_horizon_is_declared():
    assert _DAYS_ == 30

def test_reclaimed_bytes_are_reported(tmp_path):
    candidate = tmp_path / "Ancient.log"
    candidate.write_text("x" * 5000, encoding="utf-8")
    _age_(candidate, 90)
    _, reclaimed = prune_files(folders=(tmp_path,), days=30)
    assert reclaimed == 5000