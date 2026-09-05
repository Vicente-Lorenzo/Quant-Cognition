import os
import sys
import time
from pathlib import Path

from Library.Logging import LoggingAPI, VerboseLevel
from Library.Logging.File import FileAPI
from Library.Utility.Path import inspect_temporary

def test_default_directory_is_the_temporary_tier(tmp_path):
    LoggingAPI.file.set_path(None)
    assert LoggingAPI.file.Directory == inspect_temporary("Logs")
    assert LoggingAPI.file.Temporary is True

def test_default_directory_carries_no_product_name():
    LoggingAPI.file.set_path(None)
    assert "Quant" not in str(LoggingAPI.file.Directory)

def test_default_directory_is_portable():
    assert FileAPI.folder().is_absolute()
    assert FileAPI.Folder == "Logs"

def test_explicit_path_persists_outside_temp(tmp_path):
    LoggingAPI.file.set_path(tmp_path)
    assert LoggingAPI.file.Directory == tmp_path
    assert LoggingAPI.file.Temporary is False

def test_path_can_return_to_temp(tmp_path):
    LoggingAPI.file.set_path(tmp_path)
    LoggingAPI.file.set_path(None)
    assert LoggingAPI.file.Temporary is True

def test_filename_is_industry_standard(tmp_path):
    LoggingAPI.file.set_name("Scheduler")
    assert LoggingAPI.file.Filename == "Scheduler.log"

def test_filename_has_no_path_or_host_decoration(tmp_path):
    LoggingAPI.file.set_name("Scheduler")
    assert "__" not in LoggingAPI.file.Filename
    assert os.sep not in LoggingAPI.file.Filename

def test_extension_is_configurable(tmp_path):
    LoggingAPI.file.set_name("Custom")
    LoggingAPI.file.set_extension("txt")
    assert LoggingAPI.file.Filename == "Custom.txt"
    LoggingAPI.file.set_extension(".log")
    assert LoggingAPI.file.Filename == "Custom.log"

def test_distinct_adds_the_process_id(tmp_path):
    LoggingAPI.file.set_name("Concurrent")
    LoggingAPI.file.set_distinct(True)
    assert LoggingAPI.file.Filename == f"Concurrent.{os.getpid()}.log"

def test_name_is_sanitized(tmp_path):
    LoggingAPI.file.set_name('bad:name/with\\chars ')
    assert all(character not in LoggingAPI.file.Filename for character in '<>:"/\\|?* ')

def test_origin_falls_back_for_interactive_argv(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["-c"])
    assert FileAPI._origin_() == FileAPI._FALLBACK_
    monkeypatch.setattr(sys, "argv", [""])
    assert FileAPI._origin_() == FileAPI._FALLBACK_
    monkeypatch.setattr(sys, "argv", [])
    assert FileAPI._origin_() == FileAPI._FALLBACK_

def test_origin_uses_the_entry_point_stem(monkeypatch):
    monkeypatch.setattr(sys, "argv", [str(Path("some") / "dir" / "Scheduler.py")])
    assert FileAPI._origin_() == "Scheduler"

def test_writes_land_in_the_file(tmp_path, lines):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Writer")
    log.info(lambda: "First Line: Written")
    assert any("First Line: Written" in line for line in lines())

def test_directory_is_created_on_demand(tmp_path):
    target = tmp_path / "nested" / "deeper"
    LoggingAPI.file.set_path(target)
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI("Maker").info(lambda: "created")
    LoggingAPI.file.flush()
    assert target.exists()

def test_file_is_utf8_and_survives_special_characters(tmp_path, lines):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI("Unicode").info(lambda: "Phase Warmup: Completed · 1.20s → Done · ✔")
    assert any("·" in line and "→" in line and "✔" in line for line in lines())

def test_file_uses_unix_newlines(tmp_path):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI("Newline").info(lambda: "line one")
    LoggingAPI("Newline").info(lambda: "line two")
    LoggingAPI.file.flush()
    raw = LoggingAPI.file.Path.read_bytes()
    assert b"\r\n" not in raw
    assert raw.count(b"\n") == 2

def test_appends_across_reopen(tmp_path, lines):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Append")
    log.info(lambda: "before")
    LoggingAPI.file.close()
    log.info(lambda: "after")
    assert len(lines()) == 2

def test_format_contains_all_fields(tmp_path):
    line = LoggingAPI.file._format_(VerboseLevel.Warning, "2026-07-30 12:00:00.000", "EURUSD - ", "Engine - ", "message")
    assert line == "2026-07-30 12:00:00.000 - EURUSD - Warning - Engine - message\n"

def test_file_format_has_no_ansi(tmp_path, lines):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI("Plain").error(lambda: "no colors here")
    assert all("\033" not in line for line in lines())

def test_rotation_creates_backups(tmp_path):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=512, count=3)
    log = LoggingAPI("Rotate")
    for index in range(200): log.info(lambda: f"Rotation Line {index}: {'x' * 40}")
    LoggingAPI.file.flush()
    assert Path(f"{LoggingAPI.file.Path}.1").exists()

def test_rotation_respects_the_backup_count(tmp_path):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=256, count=2)
    log = LoggingAPI("Rotate")
    for index in range(400): log.info(lambda: f"Rotation Line {index}: {'x' * 40}")
    LoggingAPI.file.flush()
    assert not Path(f"{LoggingAPI.file.Path}.3").exists()

def test_rotation_zero_count_truncates(tmp_path):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=256, count=0)
    log = LoggingAPI("Truncate")
    for index in range(200): log.info(lambda: f"Line {index}: {'x' * 40}")
    LoggingAPI.file.flush()
    assert not Path(f"{LoggingAPI.file.Path}.1").exists()
    assert LoggingAPI.file.Path.stat().st_size < 4096

def test_rotation_disabled_when_size_is_zero(tmp_path):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=0)
    log = LoggingAPI("NoRotate")
    for index in range(200): log.info(lambda: f"Line {index}: {'x' * 40}")
    LoggingAPI.file.flush()
    assert not Path(f"{LoggingAPI.file.Path}.1").exists()

def test_size_tracking_resets_after_rotation(tmp_path):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=512, count=2)
    log = LoggingAPI("Rotate")
    for index in range(200): log.info(lambda: f"Line {index}: {'x' * 40}")
    LoggingAPI.file.flush()
    assert LoggingAPI.file.Size < 512 + 200

def test_retention_prunes_old_files(tmp_path):
    LoggingAPI.file.set_path(tmp_path)
    stale = tmp_path / "Ancient.log"
    stale.write_text("old", encoding="utf-8")
    ancient = time.time() - 40 * 86400
    os.utime(stale, (ancient, ancient))
    LoggingAPI.file.set_retention(days=30)
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI("Prune").info(lambda: "trigger open")
    LoggingAPI.file.flush()
    assert not stale.exists()

def test_retention_keeps_recent_files(tmp_path):
    LoggingAPI.file.set_path(tmp_path)
    recent = tmp_path / "Recent.log"
    recent.write_text("new", encoding="utf-8")
    LoggingAPI.file.set_retention(days=30)
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI("Prune").info(lambda: "trigger open")
    LoggingAPI.file.flush()
    assert recent.exists()

def test_retention_zero_disables_pruning(tmp_path):
    LoggingAPI.file.set_path(tmp_path)
    stale = tmp_path / "Ancient.log"
    stale.write_text("old", encoding="utf-8")
    ancient = time.time() - 400 * 86400
    os.utime(stale, (ancient, ancient))
    LoggingAPI.file.set_retention(days=0)
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI("Keep").info(lambda: "trigger open")
    LoggingAPI.file.flush()
    assert stale.exists()

def test_retention_ignores_foreign_extensions(tmp_path):
    LoggingAPI.file.set_path(tmp_path)
    other = tmp_path / "Report.csv"
    other.write_text("data", encoding="utf-8")
    ancient = time.time() - 400 * 86400
    os.utime(other, (ancient, ancient))
    LoggingAPI.file.set_retention(days=1)
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI("Keep").info(lambda: "trigger open")
    LoggingAPI.file.flush()
    assert other.exists()

def test_lock_blocks_destination_changes(tmp_path):
    LoggingAPI.file.set_path(tmp_path)
    LoggingAPI.file.lock()
    LoggingAPI.file.set_path(tmp_path / "elsewhere")
    LoggingAPI.file.set_name("Other")
    LoggingAPI.file.set_rotation(size=1)
    LoggingAPI.file.set_retention(days=1)
    assert LoggingAPI.file.Directory == tmp_path
    LoggingAPI.file.unlock()

def test_changing_path_reopens_on_the_new_target(tmp_path, lines):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Move")
    log.info(lambda: "first location")
    moved = tmp_path / "moved"
    LoggingAPI.file.set_path(moved)
    log.info(lambda: "second location")
    LoggingAPI.file.flush()
    assert (moved / LoggingAPI.file.Filename).exists()