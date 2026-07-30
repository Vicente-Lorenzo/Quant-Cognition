import time

import pytest

from Library.Logging import LoggingAPI, VerboseLevel
from Library.Logging.Logger import stamp

_RUNS_: int = 20000

def _measure_(operation) -> float:
    operation()
    start = time.perf_counter()
    for _ in range(_RUNS_): operation()
    return (time.perf_counter() - start) / _RUNS_ * 1e9

def test_gated_records_are_cheap(tmp_path):
    LoggingAPI.console.set_level(VerboseLevel.Silent)
    LoggingAPI.file.set_level(VerboseLevel.Silent)
    log = LoggingAPI(Class="Bench")
    assert _measure_(lambda: log.debug(lambda: "Phase Warmup: Completed")) < 1200

def test_emitted_records_are_cheap(tmp_path):
    LoggingAPI.console.set_level(VerboseLevel.Silent)
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=0)
    log = LoggingAPI(Class="Bench")
    assert _measure_(lambda: log.debug(lambda: "Phase Warmup: Completed")) < 8000

def test_timestamp_is_cheap():
    moment = time.time()
    assert _measure_(lambda: stamp(moment)) < 2000

def test_gated_is_faster_than_emitted(tmp_path):
    log = LoggingAPI(Class="Bench")
    LoggingAPI.console.set_level(VerboseLevel.Silent)
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=0)
    emitted = _measure_(lambda: log.debug(lambda: "Phase Warmup: Completed"))
    LoggingAPI.file.set_level(VerboseLevel.Silent)
    gated = _measure_(lambda: log.debug(lambda: "Phase Warmup: Completed"))
    assert gated < emitted

def test_timestamp_cache_is_reused():
    from Library.Logging import Logger
    moment = 1_700_000_000.5
    stamp(moment)
    before = Logger._PREFIX_
    stamp(moment + 0.100)
    assert Logger._PREFIX_ is before