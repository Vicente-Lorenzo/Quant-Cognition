import logging
import threading

from Library.Logging import LoggingAPI, BridgeAPI, VerboseLevel

def test_facade_is_a_standard_logger():
    assert isinstance(LoggingAPI("Std"), logging.Logger)

def test_facade_exposes_standard_logger_attributes():
    log = LoggingAPI("Std")
    assert log.name == "test_Stdlib"
    assert log.handlers == []
    assert log.propagate is False

def test_facade_accepts_standard_handlers():
    log = LoggingAPI("Std")
    handler = logging.NullHandler()
    log.addHandler(handler)
    assert handler in log.handlers
    log.removeHandler(handler)

def test_standard_percent_formatting(recorder):
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI("Percent").info("value %s and %d", "text", 7)
    assert "value text and 7" in recorder.written[0]

def test_level_names_are_registered_with_standard_logging():
    for level in VerboseLevel:
        if level is VerboseLevel.Silent: continue
        assert logging.getLevelName(level.Standard) == level.name

def test_bridge_captures_third_party_records(recorder):
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI.install(LoggingAPI("Capture"), hooks=False, level=VerboseLevel.Warning)
    logging.getLogger("third.party").warning("external warning")
    assert any("third.party: external warning" in line for line in recorder.written)

def test_bridge_includes_the_traceback(recorder):
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI.install(LoggingAPI("Capture"), hooks=False, level=VerboseLevel.Warning)
    try: raise ValueError("external boom")
    except ValueError: logging.getLogger("third.party").exception("external crash")
    joined = "\n".join(recorder.written)
    assert "ValueError: external boom" in joined
    assert "Traceback" in joined

def test_bridge_maps_standard_levels(recorder):
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI.install(LoggingAPI("Capture"), hooks=False, level=VerboseLevel.Debug)
    third = logging.getLogger("third.party.levels")
    third.setLevel(logging.DEBUG)
    third.error("an error")
    third.critical("a critical")
    assert recorder.formatted[-2][0] is VerboseLevel.Error
    assert recorder.formatted[-1][0] is VerboseLevel.Exception

def test_bridge_respects_its_level(recorder):
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI.install(LoggingAPI("Capture"), hooks=False, level=VerboseLevel.Error)
    logging.getLogger("third.party.quiet").warning("filtered out")
    assert not any("filtered out" in line for line in recorder.written)

def test_install_is_idempotent(recorder):
    LoggingAPI.install(LoggingAPI("Capture"), hooks=False)
    LoggingAPI.install(LoggingAPI("Capture"), hooks=False)
    bridges = [handler for handler in logging.getLogger().handlers if isinstance(handler, BridgeAPI)]
    assert len(bridges) == 1

def test_install_returns_a_logger():
    assert isinstance(LoggingAPI.install(hooks=False, stdlib=False), LoggingAPI)

def test_bridge_never_raises_on_a_broken_record(recorder):
    recorder.set_level(VerboseLevel.Debug)
    bridge = BridgeAPI(LoggingAPI("Capture"), VerboseLevel.Debug)
    record = logging.LogRecord("n", logging.ERROR, "f.py", 1, "bad %s %s", ("only-one",), None)
    bridge.emit(record)

def test_standard_disable_silences_third_party(recorder):
    recorder.set_level(VerboseLevel.Debug)
    LoggingAPI.install(LoggingAPI("Capture"), hooks=False, level=VerboseLevel.Warning)
    logging.disable(logging.CRITICAL)
    try:
        logging.getLogger("third.party.disabled").error("suppressed")
    finally:
        logging.disable(logging.NOTSET)
    assert not any("suppressed" in line for line in recorder.written)

def test_excepthook_logs_and_delegates(recorder, monkeypatch):
    recorder.set_level(VerboseLevel.Debug)
    seen = []
    monkeypatch.setattr("sys.excepthook", lambda kind, value, trace: seen.append(kind))
    LoggingAPI.install(LoggingAPI("Capture"), stdlib=False, hooks=True)
    import sys
    try: raise KeyError("uncaught")
    except KeyError: sys.excepthook(*sys.exc_info())
    joined = "\n".join(recorder.written)
    assert "Runtime Exception: Uncaught" in joined
    assert "KeyError" in joined
    assert seen == [KeyError]

def test_thread_excepthook_logs_and_delegates(recorder, monkeypatch):
    recorder.set_level(VerboseLevel.Debug)
    seen = []
    monkeypatch.setattr(threading, "excepthook", lambda arguments: seen.append(arguments.exc_type))
    LoggingAPI.install(LoggingAPI("Capture"), stdlib=False, hooks=True)
    def failing(): raise RuntimeError("thread boom")
    thread = threading.Thread(target=failing)
    thread.start()
    thread.join(timeout=5)
    joined = "\n".join(recorder.written)
    assert "Thread Exception: Uncaught" in joined
    assert "RuntimeError: thread boom" in joined
    assert seen == [RuntimeError]

def test_standard_raise_exceptions_is_disabled():
    LoggingAPI.install(hooks=False, stdlib=True)
    assert logging.raiseExceptions is False