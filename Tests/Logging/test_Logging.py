import pytest

from Library.Logging import LoggingAPI, LoggerAPI, VerboseLevel

def test_lambda_is_not_called_when_gated(recorder):
    calls = []
    recorder.set_level(VerboseLevel.Warning)
    LoggingAPI.console.set_level(VerboseLevel.Silent)
    LoggingAPI.file.set_level(VerboseLevel.Silent)
    log = LoggingAPI("Lazy")
    log.debug(lambda: calls.append(1) or "never built")
    log.info(lambda: calls.append(1) or "never built")
    log.alert(lambda: calls.append(1) or "never built")
    assert calls == []

def test_lambda_is_called_when_accepted(recorder):
    calls = []
    recorder.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Lazy")
    log.debug(lambda: calls.append(1) or "built")
    assert calls == [1]

def test_lambda_is_called_exactly_once_for_many_sinks(recorder):
    calls = []
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI.console.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Once")
    log.debug(lambda: calls.append(1) or "built")
    assert calls == [1]
    assert len(recorder.matching("built")) == 1

def test_plain_string_content_is_accepted(recorder):
    recorder.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Plain")
    log.info("Plain Message: Delivered")
    assert recorder.matching("Plain Message: Delivered")

@pytest.mark.parametrize("method,level", [
    ("debug", VerboseLevel.Debug), ("info", VerboseLevel.Info), ("alert", VerboseLevel.Alert),
    ("warning", VerboseLevel.Warning), ("error", VerboseLevel.Error), ("exception", VerboseLevel.Exception)])
def test_every_level_method_emits_its_level(recorder, method, level):
    recorder.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Levels")
    getattr(log, method)(lambda: "message")
    mine = [entry for entry in recorder.formatted if entry[4] == "message"]
    assert mine and mine[0][0] is level

def test_gating_is_per_level(recorder):
    recorder.set_level(VerboseLevel.Warning)
    log = LoggingAPI("Gate")
    log.debug(lambda: "dropped")
    log.info(lambda: "dropped")
    log.alert(lambda: "dropped")
    log.warning(lambda: "kept")
    log.error(lambda: "kept")
    log.exception(lambda: "kept")
    assert len(recorder.matching("kept")) == 3
    assert recorder.matching("dropped") == []

def test_silent_sink_receives_nothing(recorder):
    recorder.set_level(VerboseLevel.Silent)
    log = LoggingAPI("Silent")
    for method in ("debug", "info", "alert", "warning", "error", "exception"):
        getattr(log, method)(lambda: "message")
    assert recorder.written == []

def test_per_sink_levels_route_independently(recorder, lines):
    LoggingAPI.console.set_level(VerboseLevel.Silent)
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    recorder.set_level(VerboseLevel.Error)
    log = LoggingAPI("Routing")
    log.debug(lambda: "debug only to file")
    log.error(lambda: "error to both")
    assert len(recorder.matching("error to both")) == 1
    assert recorder.matching("debug only to file") == []
    assert len(lines()) == 2

def test_writing_to_a_single_sink_directly(recorder):
    recorder.set_level(VerboseLevel.Debug)
    recorder.write(VerboseLevel.Info, "moment", "", "", "direct")
    assert "moment - Info - direct" in recorder.written

def test_shared_tags_appear_before_level(recorder):
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI.set_shared_tags("EURUSD", "H1")
    log = LoggingAPI("Tagged")
    log.info(lambda: "message")
    assert recorder.matching(" - EURUSD - H1 - Info - test_Logging - Tagged - message")

def test_shared_tags_are_shared_across_instances(recorder):
    recorder.set_level(VerboseLevel.Debug)
    first = LoggingAPI("First")
    LoggingAPI.set_shared_tags("SHARED")
    second = LoggingAPI("Second")
    first.info(lambda: "a")
    second.info(lambda: "b")
    tagged = recorder.matching("First") + recorder.matching("Second")
    assert len(tagged) == 2 and all("SHARED" in line for line in tagged)

def test_clear_shared_tags(recorder):
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI.set_shared_tags("GONE")
    LoggingAPI.clear_shared_tags()
    log = LoggingAPI("Cleared")
    log.info(lambda: "message")
    assert recorder.matching("Cleared") and recorder.matching("GONE") == []

def test_set_shared_tags_ignores_empty_call(recorder):
    LoggingAPI.set_shared_tags("KEPT")
    LoggingAPI.set_shared_tags()
    assert LoggingAPI._shared_tags_ == ("KEPT",)

def test_instance_tags_appear_after_level(recorder):
    recorder.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Engine", "Backtesting")
    log.info(lambda: "message")
    assert recorder.matching(" - Info - test_Logging - Engine - Backtesting - message")

def test_instance_tags_are_independent(recorder):
    recorder.set_level(VerboseLevel.Debug)
    first = LoggingAPI("Alpha")
    second = LoggingAPI("Beta")
    first.info(lambda: "a")
    second.info(lambda: "b")
    alpha, beta = recorder.matching("Alpha"), recorder.matching("Beta")
    assert len(alpha) == 1 and "Beta" not in alpha[0]
    assert len(beta) == 1 and "Alpha" not in beta[0]

def test_given_tags_follow_the_derived_owner(recorder):
    log = LoggingAPI("Explicit", "Purpose")
    assert log.InstanceTags == ("test_Logging", "Explicit", "Purpose")

def test_class_is_derived_when_omitted(recorder):
    log = LoggingAPI()
    assert log.InstanceTags == ("test_Logging", "Tests")

def test_identify_can_be_disabled(recorder):
    log = LoggingAPI(identify=False)
    assert log.InstanceTags == ()

def test_identify_disabled_still_honors_explicit_tags(recorder):
    log = LoggingAPI("Manual", "Purpose", identify=False)
    assert log.InstanceTags == ("Manual", "Purpose")

def test_given_tags_replace_the_derived_subsystem(recorder):
    assert LoggingAPI().InstanceTags == ("test_Logging", "Tests")
    assert LoggingAPI("Override").InstanceTags == ("test_Logging", "Override")

def test_many_tags_are_kept_in_order(recorder):
    log = LoggingAPI("C", "S", "Extra", "EU")
    assert log.InstanceTags == ("test_Logging", "C", "S", "Extra", "EU")

def test_set_instance_tags_replaces_tags(recorder):
    log = LoggingAPI("Old")
    log.set_instance_tags("New", "Fresh")
    assert log.InstanceTags == ("New", "Fresh")

def test_empty_tags_are_dropped(recorder):
    log = LoggingAPI("Only", "", identify=False)
    assert log.InstanceTags == ("Only",)

def test_none_tags_are_dropped(recorder):
    log = LoggingAPI("Only", None)
    assert log.InstanceTags == ("test_Logging", "Only")

def test_facade_set_level_applies_to_both_shared_sinks():
    log = LoggingAPI("Both")
    log.set_level(VerboseLevel.Alert)
    assert LoggingAPI.console.Level is VerboseLevel.Alert
    assert LoggingAPI.file.Level is VerboseLevel.Alert

def test_facade_reset_level(recorder):
    LoggingAPI.console.set_level(VerboseLevel.Warning, default=True)
    LoggingAPI.file.set_level(VerboseLevel.Error, default=True)
    log = LoggingAPI("Reset")
    log.set_level(VerboseLevel.Debug)
    log.reset_level()
    assert LoggingAPI.console.Level is VerboseLevel.Warning
    assert LoggingAPI.file.Level is VerboseLevel.Error

def test_configuration_survives_new_instances(recorder):
    LoggingAPI("Setup").set_level(VerboseLevel.Alert)
    assert LoggingAPI("Later").console.Level is VerboseLevel.Alert

def test_with_statement_locks_configuration(recorder):
    log = LoggingAPI("Master")
    log.set_level(VerboseLevel.Warning)
    with log:
        nested = LoggingAPI("Nested")
        nested.set_level(VerboseLevel.Debug)
        assert LoggingAPI.console.Level is VerboseLevel.Warning
        assert LoggingAPI.file.Level is VerboseLevel.Warning

def test_with_statement_unlocks_on_exit(recorder):
    log = LoggingAPI("Master")
    with log:
        pass
    log.set_level(VerboseLevel.Debug)
    assert LoggingAPI.console.Level is VerboseLevel.Debug

def test_nested_with_only_outermost_governs(recorder):
    log = LoggingAPI("Master")
    log.set_level(VerboseLevel.Warning)
    with log:
        with LoggingAPI("Inner"):
            pass
        assert LoggingAPI.console.Locked is True
    assert LoggingAPI.console.Locked is False

def test_with_statement_does_not_suppress_exceptions(recorder):
    log = LoggingAPI("Raises")
    with pytest.raises(ValueError):
        with log:
            raise ValueError("must propagate")

def test_with_statement_returns_self(recorder):
    log = LoggingAPI("Self")
    with log as entered:
        assert entered is log

def test_guard_logs_and_reraises(recorder):
    recorder.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Guard")
    @log.guard
    def failing():
        raise RuntimeError("inner failure")
    with pytest.raises(RuntimeError):
        failing()
    joined = "\n".join(recorder.written)
    assert "Failed @ failing" in joined
    assert "RuntimeError: inner failure" in joined

def test_guard_returns_value_on_success(recorder):
    log = LoggingAPI("Guard")
    @log.guard
    def working():
        return 42
    assert working() == 42

def test_guard_preserves_function_metadata(recorder):
    log = LoggingAPI("Guard")
    @log.guard
    def named():
        return None
    assert named.__name__ == "named"

def test_log_method_with_explicit_level(recorder):
    recorder.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Explicit")
    log.log(VerboseLevel.Warning, lambda: "explicit level")
    mine = [entry for entry in recorder.formatted if entry[4] == "explicit level"]
    assert mine and mine[0][0] is VerboseLevel.Warning

def test_log_method_with_silent_is_dropped(recorder):
    recorder.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Explicit")
    log.log(VerboseLevel.Silent, lambda: "dropped")
    assert recorder.written == []

def test_critical_maps_to_exception(recorder):
    recorder.set_level(VerboseLevel.Debug)
    log = LoggingAPI("Critical")
    log.critical(lambda: "critical")
    mine = [entry for entry in recorder.formatted if entry[4] == "critical"]
    assert mine and mine[0][0] is VerboseLevel.Exception

def test_flush_and_close_are_safe_without_open(recorder):
    log = LoggingAPI("Lifecycle")
    log.flush()
    log.close()

def test_open_opens_every_sink(recorder):
    log = LoggingAPI("Lifecycle")
    log.open()
    assert recorder._opened_ is True