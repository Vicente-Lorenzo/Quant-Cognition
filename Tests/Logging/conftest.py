import logging

import pytest

from Library.Logging import LoggingAPI, LoggerAPI, VerboseLevel

@pytest.fixture(autouse=True)
def isolate(tmp_path):
    registry = list(LoggerAPI.Registry)
    sinks = [(sink, sink._level_, sink._default_, sink._enabled_, sink._locked_) for sink in registry]
    tags, head = LoggingAPI._class_tags_, LoggingAPI._class_head_
    depth = LoggingAPI._depth_
    shape = (LoggingAPI.file._directory_, LoggingAPI.file._name_, LoggingAPI.file._extension_, LoggingAPI.file._size_, LoggingAPI.file._count_, LoggingAPI.file._days_, LoggingAPI.file._distinct_)
    forced = LoggingAPI.console._forced_
    root = list(logging.getLogger().handlers)
    level = logging.getLogger().level
    for sink in registry: sink.unlock()
    LoggingAPI.file.close()
    LoggingAPI.file.set_path(tmp_path)
    LoggingAPI.file.set_name("Test")
    LoggingAPI.console.set_level(VerboseLevel.Silent)
    LoggingAPI.file.set_level(VerboseLevel.Silent)
    LoggingAPI.clear_class_tags()
    LoggingAPI._depth_ = 0
    yield
    for sink in registry: sink.unlock()
    LoggingAPI.file.close()
    for sink, sink_level, sink_default, sink_enabled, sink_locked in sinks:
        sink._level_, sink._default_, sink._enabled_, sink._locked_ = sink_level, sink_default, sink_enabled, sink_locked
    LoggerAPI.Registry[:] = registry
    LoggerAPI.refresh()
    LoggingAPI.file._directory_, LoggingAPI.file._name_, LoggingAPI.file._extension_, LoggingAPI.file._size_, LoggingAPI.file._count_, LoggingAPI.file._days_, LoggingAPI.file._distinct_ = shape
    LoggingAPI.console._forced_ = forced
    LoggingAPI._class_tags_, LoggingAPI._class_head_ = tags, head
    LoggingAPI._depth_ = depth
    logging.getLogger().handlers[:] = root
    logging.getLogger().setLevel(level)

@pytest.fixture
def lines(tmp_path):
    def read():
        LoggingAPI.file.flush()
        path = LoggingAPI.file.Path
        if not path.exists(): return []
        return [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    return read

class RecorderAPI(LoggerAPI):

    Name = "Recorder"

    def __init__(self, level=VerboseLevel.Debug):
        super().__init__(level=level)
        self.written = []
        self.formatted = []

    def _format_(self, level, moment, head, tail, message):
        line = f"{moment} - {head}{level.name} - {tail}{message}"
        self.formatted.append((level, moment, head, tail, message))
        return line

    def _write_(self, line):
        self.written.append(line)

@pytest.fixture
def recorder():
    sink = RecorderAPI()
    LoggerAPI.refresh()
    yield sink
    if sink in LoggerAPI.Registry: LoggerAPI.Registry.remove(sink)
    LoggerAPI.refresh()