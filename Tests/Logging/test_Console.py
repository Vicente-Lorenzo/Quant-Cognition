import io
import sys

import pytest

from Library.Logging import LoggingAPI, VerboseLevel

def test_format_is_plain_without_color():
    LoggingAPI.console.set_color(False)
    line = LoggingAPI.console._format_(VerboseLevel.Warning, "2026-07-30 12:00:00.000", "EURUSD - ", "Engine - ", "message")
    assert line == "2026-07-30 12:00:00.000 - EURUSD - Warning - Engine - message\n"
    assert "\033" not in line

def test_format_colors_only_the_level():
    LoggingAPI.console.set_color(True)
    line = LoggingAPI.console._format_(VerboseLevel.Warning, "2026-07-30 12:00:00.000", "EURUSD - ", "Engine - ", "message")
    assert LoggingAPI.console._YELLOW_ in line
    assert line.count(LoggingAPI.console._RESET_) == 1
    assert "EURUSD" in line and "\033" not in line.split("EURUSD")[0]

@pytest.mark.parametrize("level,color", [
    (VerboseLevel.Debug, "_GREEN_"), (VerboseLevel.Info, "_BLUE_"), (VerboseLevel.Alert, "_ORANGE_"),
    (VerboseLevel.Warning, "_YELLOW_"), (VerboseLevel.Error, "_RED_"), (VerboseLevel.Exception, "_DARKRED_")])
def test_every_level_has_a_distinct_color(level, color):
    LoggingAPI.console.set_color(True)
    line = LoggingAPI.console._format_(level, "moment", "", "", "message")
    assert getattr(LoggingAPI.console, color) in line

def test_colors_are_distinct_across_levels():
    palette = {LoggingAPI.console._palette_[level] for level in LoggingAPI.console._palette_}
    assert len(palette) == len(LoggingAPI.console._palette_)

def test_color_is_disabled_when_not_a_tty(monkeypatch):
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    LoggingAPI.console.set_color(None)
    assert LoggingAPI.console._supports_() is False

def test_color_detection_survives_a_stream_without_isatty(monkeypatch):
    class Bare:

        def write(self, text): pass
    monkeypatch.setattr(sys, "stdout", Bare())
    assert LoggingAPI.console._supports_() is False

def test_color_detection_survives_a_none_stream(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    assert LoggingAPI.console._supports_() is False

def test_forced_color_overrides_detection():
    LoggingAPI.console.set_color(True)
    assert LoggingAPI.console.Color is True
    LoggingAPI.console.set_color(False)
    assert LoggingAPI.console.Color is False

def test_color_none_returns_to_detection():
    LoggingAPI.console.set_color(True)
    LoggingAPI.console.set_color(None)
    assert LoggingAPI.console.Color == LoggingAPI.console._supports_()

def test_lock_blocks_color_changes():
    LoggingAPI.console.set_color(False)
    LoggingAPI.console.lock()
    LoggingAPI.console.set_color(True)
    assert LoggingAPI.console.Color is False
    LoggingAPI.console.unlock()

def test_output_reaches_stdout(monkeypatch):
    stream = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stream)
    LoggingAPI.console.set_color(False)
    LoggingAPI.console.set_level(VerboseLevel.Debug)
    LoggingAPI("Screen").info(lambda: "Console Output: Delivered")
    assert "Console Output: Delivered" in stream.getvalue()

def test_output_is_resolved_lazily(monkeypatch):
    LoggingAPI.console.set_color(False)
    LoggingAPI.console.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Screen")
    first = io.StringIO()
    monkeypatch.setattr(sys, "stdout", first)
    log.info(lambda: "first stream")
    second = io.StringIO()
    monkeypatch.setattr(sys, "stdout", second)
    log.info(lambda: "second stream")
    assert "first stream" in first.getvalue()
    assert "second stream" in second.getvalue()
    assert "first stream" not in second.getvalue()

def test_unencodable_characters_do_not_raise(monkeypatch):
    class Narrow(io.StringIO):

        encoding = "cp1252"

        def write(self, text):
            text.encode("cp1252")
            return super().write(text)
    stream = Narrow()
    monkeypatch.setattr(sys, "stdout", stream)
    LoggingAPI.console.set_color(False)
    LoggingAPI.console.set_level(VerboseLevel.Debug)
    LoggingAPI("Narrow").info(lambda: "Phase Warmup: Completed · Done → ✔")
    assert "Phase Warmup" in stream.getvalue()

def test_write_to_a_broken_stream_never_raises(monkeypatch):
    class Broken:

        encoding = "utf-8"

        def isatty(self): return False

        def write(self, text): raise OSError("pipe closed")

        def flush(self): raise OSError("pipe closed")
    monkeypatch.setattr(sys, "stdout", Broken())
    LoggingAPI.console.set_level(VerboseLevel.Debug)
    LoggingAPI("Broken").info(lambda: "should not raise")
    LoggingAPI.console.flush()

def test_virtual_terminal_probe_never_raises():
    assert LoggingAPI.console._virtual_() in (True, False)

def test_supports_is_platform_aware(monkeypatch):
    class Tty(io.StringIO):

        def isatty(self): return True
    monkeypatch.setattr(sys, "stdout", Tty())
    monkeypatch.setattr(sys, "platform", "linux")
    assert LoggingAPI.console._supports_() is True