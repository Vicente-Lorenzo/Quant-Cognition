import sys

import pytest

from Library.Logging import LoggingAPI, LoggerAPI, VerboseLevel

def test_raising_lambda_never_propagates(recorder):
    recorder.set_level(VerboseLevel.Debug)
    log = LoggingAPI(Class="Raiser")
    def explode(): raise ValueError("message build failed")
    log.info(explode)

def test_raising_lambda_does_not_stop_later_records(recorder):
    recorder.set_level(VerboseLevel.Debug)
    log = LoggingAPI(Class="Raiser")
    def explode(): raise ValueError("boom")
    log.info(explode)
    log.info(lambda: "still working")
    assert any("still working" in line for line in recorder.written)

def test_content_with_broken_repr_never_propagates(recorder):
    recorder.set_level(VerboseLevel.Debug)
    class Hostile:
        def __str__(self): raise RuntimeError("no string for you")
    log = LoggingAPI(Class="Hostile")
    log.info(lambda: Hostile())

def test_percent_formatting_mismatch_never_propagates(recorder):
    recorder.set_level(VerboseLevel.Debug)
    log = LoggingAPI(Class="Percent")
    log.info("only %s here", "one", "two")

def test_unwritable_directory_never_propagates(tmp_path):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.close()
    LoggingAPI.file.set_path(tmp_path / "file.txt")
    (tmp_path / "file.txt").write_text("not a directory", encoding="utf-8")
    LoggingAPI(Class="Blocked").info(lambda: "should not raise")

def test_sink_that_raises_on_open_never_propagates(recorder):
    def explode(): raise OSError("cannot open")
    recorder._open_ = explode
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI(Class="Opener").info(lambda: "should not raise")

def test_sink_that_raises_on_write_never_propagates(recorder):
    def explode(line): raise OSError("cannot write")
    recorder._write_ = explode
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI(Class="Writer").info(lambda: "should not raise")

def test_a_broken_sink_does_not_block_a_healthy_one(recorder, lines):
    def explode(line): raise OSError("cannot write")
    recorder._write_ = explode
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI(Class="Mixed").info(lambda: "reaches the file")
    assert any("reaches the file" in line for line in lines())

def test_sink_that_raises_on_flush_never_propagates(recorder):
    def explode(): raise OSError("cannot flush")
    recorder.open()
    recorder._flush_ = explode
    recorder.flush()

def test_sink_that_raises_on_close_leaves_it_closed(recorder):
    def explode(): raise OSError("cannot close")
    recorder.open()
    recorder._close_ = explode
    with pytest.raises(OSError):
        recorder.close()
    assert recorder._opened_ is False

def test_fallback_survives_a_missing_stderr(monkeypatch, recorder):
    monkeypatch.setattr(sys, "__stderr__", None)
    def explode(line): raise OSError("cannot write")
    recorder._write_ = explode
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI(Class="NoStderr").info(lambda: "should not raise")

def test_fallback_survives_a_broken_stderr(monkeypatch, recorder):
    class Broken:
        def write(self, text): raise OSError("stderr gone")
    monkeypatch.setattr(sys, "__stderr__", Broken())
    def explode(line): raise OSError("cannot write")
    recorder._write_ = explode
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI(Class="BrokenStderr").info(lambda: "should not raise")

def test_guard_still_closes_after_failure(recorder):
    log = LoggingAPI(Class="Guard")
    @log.guard
    def failing(): raise RuntimeError("inner")
    with pytest.raises(RuntimeError):
        failing()
    assert LoggingAPI._depth_ == 0

def test_unbalanced_exit_cannot_drive_depth_negative(recorder):
    log = LoggingAPI(Class="Unbalanced")
    log.__exit__(None, None, None)
    log.__exit__(None, None, None)
    assert LoggingAPI._depth_ == 0

def test_logging_before_any_configuration_never_raises():
    LoggingAPI(Class="Fresh").debug(lambda: "no configuration yet")

def test_very_long_message_is_written(tmp_path, lines):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=0)
    payload = "z" * 200000
    LoggingAPI(Class="Long").info(lambda: payload)
    assert any(len(line) > 199999 for line in lines())

def test_message_with_embedded_newlines_is_written(tmp_path, lines):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI(Class="Multi").info(lambda: "first\nsecond\nthird")
    assert len(lines()) == 3

def test_none_message_never_raises(recorder):
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI(Class="Nil").info(None)

def test_non_string_message_is_rendered(recorder):
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI(Class="Number").info(lambda: 42)
    assert "42" in recorder.written[0]