import pytest

from Library.Logging import LoggerAPI, LoggingAPI, VerboseLevel

def test_registry_contains_the_shared_sinks():
    assert LoggingAPI.console in LoggerAPI.Registry
    assert LoggingAPI.file in LoggerAPI.Registry

def test_set_level_changes_level(recorder):
    recorder.set_level(VerboseLevel.Warning)
    assert recorder.Level is VerboseLevel.Warning

def test_set_level_accepts_name_and_integer(recorder):
    recorder.set_level("Error")
    assert recorder.Level is VerboseLevel.Error
    recorder.set_level(20)
    assert recorder.Level is VerboseLevel.Info

def test_set_level_is_skipped_when_already_set(recorder):
    recorder.set_level(VerboseLevel.Info)
    before = list(LoggerAPI.Targets[VerboseLevel.Info.value])
    recorder.set_level(VerboseLevel.Info)
    assert LoggerAPI.Targets[VerboseLevel.Info.value] == before

def test_default_level_is_recorded_and_reset(recorder):
    recorder.set_level(VerboseLevel.Warning, default=True)
    recorder.set_level(VerboseLevel.Debug)
    assert recorder.Level is VerboseLevel.Debug
    recorder.reset_level()
    assert recorder.Level is VerboseLevel.Warning

def test_set_default_level_alone_does_not_change_current(recorder):
    recorder.set_level(VerboseLevel.Debug)
    recorder.set_default_level(VerboseLevel.Error)
    assert recorder.Level is VerboseLevel.Debug
    assert recorder.Default is VerboseLevel.Error

def test_temporary_restores_previous_level(recorder):
    recorder.set_level(VerboseLevel.Warning)
    with recorder.temporary(VerboseLevel.Debug):
        assert recorder.Level is VerboseLevel.Debug
    assert recorder.Level is VerboseLevel.Warning

def test_temporary_restores_on_exception(recorder):
    recorder.set_level(VerboseLevel.Warning)
    with pytest.raises(RuntimeError):
        with recorder.temporary(VerboseLevel.Debug):
            raise RuntimeError("boom")
    assert recorder.Level is VerboseLevel.Warning

def test_temporary_restores_previous_not_default(recorder):
    recorder.set_level(VerboseLevel.Error, default=True)
    recorder.set_level(VerboseLevel.Info)
    with recorder.temporary(VerboseLevel.Debug):
        pass
    assert recorder.Level is VerboseLevel.Info

def test_lock_blocks_level_changes(recorder):
    recorder.set_level(VerboseLevel.Info)
    recorder.lock()
    recorder.set_level(VerboseLevel.Debug)
    assert recorder.Level is VerboseLevel.Info

def test_unlock_restores_level_changes(recorder):
    recorder.set_level(VerboseLevel.Info)
    recorder.lock()
    recorder.unlock()
    recorder.set_level(VerboseLevel.Debug)
    assert recorder.Level is VerboseLevel.Debug

def test_temporary_bypasses_the_lock(recorder):
    recorder.set_level(VerboseLevel.Info)
    recorder.lock()
    with recorder.temporary(VerboseLevel.Debug):
        assert recorder.Level is VerboseLevel.Debug
    assert recorder.Level is VerboseLevel.Info

def test_lock_blocks_enable_and_disable(recorder):
    recorder.lock()
    recorder.disable()
    assert recorder.Enabled is True

def test_disable_removes_sink_from_targets(recorder):
    recorder.set_level(VerboseLevel.Debug)
    assert recorder in LoggerAPI.Targets[VerboseLevel.Debug.value]
    recorder.disable()
    assert recorder not in LoggerAPI.Targets[VerboseLevel.Debug.value]

def test_enable_restores_sink_to_targets(recorder):
    recorder.set_level(VerboseLevel.Debug)
    recorder.disable()
    recorder.enable()
    assert recorder in LoggerAPI.Targets[VerboseLevel.Debug.value]

def test_gate_is_the_most_verbose_enabled_sink(recorder):
    LoggingAPI.console.set_level(VerboseLevel.Silent)
    LoggingAPI.file.set_level(VerboseLevel.Silent)
    recorder.set_level(VerboseLevel.Warning)
    assert LoggerAPI.Gate == VerboseLevel.Warning.value
    LoggingAPI.console.set_level(VerboseLevel.Debug)
    assert LoggerAPI.Gate == VerboseLevel.Debug.value

def test_gate_ignores_disabled_sinks(recorder):
    LoggingAPI.console.set_level(VerboseLevel.Silent)
    LoggingAPI.file.set_level(VerboseLevel.Silent)
    recorder.set_level(VerboseLevel.Debug)
    recorder.disable()
    assert LoggerAPI.Gate == VerboseLevel.Silent.value

def test_targets_are_monotonic(recorder):
    recorder.set_level(VerboseLevel.Info)
    for value in range(1, 7):
        assert set(LoggerAPI.Targets[value]).issubset(set(LoggerAPI.Targets[value - 1]))

def test_accepts_matches_targets(recorder):
    recorder.set_level(VerboseLevel.Warning)
    assert recorder.accepts(VerboseLevel.Exception) is True
    assert recorder.accepts(VerboseLevel.Warning) is True
    assert recorder.accepts(VerboseLevel.Alert) is False
    assert recorder.accepts(VerboseLevel.Debug) is False

def test_silent_sink_accepts_nothing(recorder):
    recorder.set_level(VerboseLevel.Silent)
    for level in VerboseLevel:
        if level is VerboseLevel.Silent: continue
        assert recorder.accepts(level) is False

def test_open_is_idempotent(recorder):
    recorder.open()
    recorder.open()
    assert recorder._opened_ is True

def test_close_is_idempotent(recorder):
    recorder.open()
    recorder.close()
    recorder.close()
    assert recorder._opened_ is False

def test_flush_on_closed_sink_is_safe(recorder):
    recorder.flush()

def test_write_opens_lazily(recorder):
    assert recorder._opened_ is False
    recorder.write(VerboseLevel.Info, "moment", "", "", "message")
    assert recorder._opened_ is True
    assert recorder.written

def test_write_failure_never_propagates(recorder, capsys):
    def explode(line): raise OSError("disk on fire")
    recorder._write_ = explode
    recorder.write(VerboseLevel.Info, "moment", "", "", "message")

def test_format_failure_never_propagates(recorder):
    def explode(*args): raise ValueError("bad format")
    recorder._format_ = explode
    recorder.write(VerboseLevel.Info, "moment", "", "", "message")

def test_stamp_is_millisecond_precise():
    assert LoggerAPI.stamp(1_700_000_000.0).endswith(".000")
    assert LoggerAPI.stamp(1_700_000_000.123).endswith(".123")
    assert LoggerAPI.stamp(1_700_000_000.999).endswith(".999")

def test_stamp_never_overflows_milliseconds():
    for fraction in (0.0, 0.4999, 0.9999, 0.99999999):
        assert len(LoggerAPI.stamp(1_700_000_000 + fraction).split(".")[-1]) == 3

def test_stamp_advances_across_seconds():
    first = LoggerAPI.stamp(1_700_000_000.5)
    second = LoggerAPI.stamp(1_700_000_001.5)
    assert first != second
    assert first.split(".")[0] != second.split(".")[0]