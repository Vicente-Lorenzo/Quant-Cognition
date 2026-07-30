import time
import threading

import pytest

from Library.Logging import LoggingAPI, StorageAPI, VerboseLevel

class FakeRecordAPI:

    def __init__(self):
        self.UID = "fake"
        self.Content = ""
        self.Records = 0
        self.Dropped = 0
        self.Truncated = False
        self.StoppedAt = None
        self.saves = 0

    def save(self, *args, **kwargs):
        self.saves += 1

@pytest.fixture
def storage():
    sink = StorageAPI()
    from Library.Logging import LoggerAPI
    LoggerAPI.refresh()
    yield sink
    sink.detach()
    from Library.Logging import LoggerAPI as registry
    if sink in registry.Registry: registry.Registry.remove(sink)
    registry.refresh()

def _attach_(sink, interval=0.05):
    sink._record_ = FakeRecordAPI()
    sink._db_ = object()
    sink.set_interval(interval)
    sink._signal_.clear()
    sink._thread_ = threading.Thread(target=sink._drain_, daemon=True)
    sink._thread_.start()
    return sink._record_

def test_level_is_capped_at_warning(storage):
    storage.set_level(VerboseLevel.Debug)
    assert storage.Level is VerboseLevel.Warning
    storage.set_level(VerboseLevel.Info)
    assert storage.Level is VerboseLevel.Warning
    storage.set_level(VerboseLevel.Alert)
    assert storage.Level is VerboseLevel.Warning

def test_level_below_the_cap_is_honored(storage):
    storage.set_level(VerboseLevel.Error)
    assert storage.Level is VerboseLevel.Error
    storage.set_level(VerboseLevel.Exception)
    assert storage.Level is VerboseLevel.Exception

def test_cap_means_routine_traffic_never_reaches_it(storage):
    storage.set_level(VerboseLevel.Debug)
    record = _attach_(storage)
    log = LoggingAPI("Capped")
    log.debug(lambda: "debug")
    log.info(lambda: "info")
    log.alert(lambda: "alert")
    log.warning(lambda: "warning")
    time.sleep(0.3)
    assert "warning" in record.Content
    assert "debug" not in record.Content
    assert "info" not in record.Content

def test_inert_until_attached(storage):
    storage.set_level(VerboseLevel.Warning)
    assert storage.Attached is False
    LoggingAPI("Detached").error(lambda: "goes nowhere")
    assert storage.Records == 0

def test_records_are_accumulated_and_flushed(storage):
    storage.set_level(VerboseLevel.Warning)
    record = _attach_(storage)
    log = LoggingAPI("Accumulate")
    for index in range(10): log.error(lambda: f"Record {index}")
    time.sleep(0.3)
    assert storage.Records == 10
    assert record.Content.count("\n") == 10

def test_flush_is_batched_not_per_record(storage):
    storage.set_level(VerboseLevel.Warning)
    record = _attach_(storage, interval=0.2)
    log = LoggingAPI("Batched")
    for index in range(50): log.error(lambda: f"Record {index}")
    time.sleep(0.5)
    assert storage.Records == 50
    assert record.saves < 50

def test_writes_do_not_block_the_caller(storage):
    storage.set_level(VerboseLevel.Warning)
    _attach_(storage, interval=5.0)
    log = LoggingAPI("NonBlocking")
    start = time.perf_counter()
    for index in range(1000): log.error(lambda: f"Record {index}")
    assert time.perf_counter() - start < 1.0

def test_queue_overflow_is_counted_not_raised(storage):
    storage.set_level(VerboseLevel.Warning)
    storage._record_ = FakeRecordAPI()
    storage._queue_.maxsize = 5
    log = LoggingAPI("Overflow")
    for index in range(50): log.error(lambda: f"Record {index}")
    assert storage.Dropped > 0

def test_content_limit_marks_truncated(storage):
    storage.set_level(VerboseLevel.Warning)
    storage.set_limit(200)
    record = _attach_(storage)
    log = LoggingAPI("Truncate")
    for index in range(50): log.error(lambda: f"Record {index} {'x' * 40}")
    time.sleep(0.3)
    assert storage.Truncated is True
    assert len(record.Content) < 2000

def test_records_counted_even_when_truncated(storage):
    storage.set_level(VerboseLevel.Warning)
    storage.set_limit(100)
    _attach_(storage)
    log = LoggingAPI("Truncate")
    for index in range(20): log.error(lambda: f"Record {index} {'x' * 40}")
    time.sleep(0.3)
    assert storage.Records == 20

def test_reentrancy_guard_drops_records_from_the_writer(storage):
    storage.set_level(VerboseLevel.Warning)
    storage._record_ = FakeRecordAPI()
    storage._guard_.busy = True
    try:
        LoggingAPI("Reentrant").error(lambda: "from the writer thread")
        assert storage._queue_.qsize() == 0
    finally:
        storage._guard_.busy = False

def test_detach_performs_a_final_flush(storage):
    storage.set_level(VerboseLevel.Warning)
    record = _attach_(storage, interval=10.0)
    LoggingAPI("Final").error(lambda: "last record")
    storage.detach()
    assert "last record" in record.Content
    assert record.StoppedAt is not None

def test_detach_is_idempotent(storage):
    storage.set_level(VerboseLevel.Warning)
    _attach_(storage)
    storage.detach()
    storage.detach()
    assert storage.Attached is False

def test_detach_clears_the_queue(storage):
    storage.set_level(VerboseLevel.Warning)
    storage._record_ = FakeRecordAPI()
    LoggingAPI("Leftover").error(lambda: "queued")
    storage.detach()
    assert storage._queue_.empty()

def test_failing_save_never_propagates(storage):
    storage.set_level(VerboseLevel.Warning)
    record = _attach_(storage)
    def explode(*args, **kwargs): raise RuntimeError("database gone")
    record.save = explode
    LoggingAPI("Broken").error(lambda: "should not raise")
    time.sleep(0.3)

def test_failing_save_does_not_kill_the_writer(storage):
    storage.set_level(VerboseLevel.Warning)
    record = _attach_(storage)
    def explode(*args, **kwargs): raise RuntimeError("database gone")
    record.save = explode
    LoggingAPI("Broken").error(lambda: "first")
    time.sleep(0.2)
    assert storage._thread_.is_alive()

def test_properties_mirror_attributes(storage):
    assert storage.Attached is (storage._record_ is not None)
    assert storage.Records == storage._records_
    assert storage.Dropped == storage._dropped_
    assert storage.Truncated is storage._truncated_
    assert storage.Interval == storage._interval_
    assert storage.Limit == storage._limit_

def test_interval_and_limit_setters(storage):
    storage.set_interval(1.5)
    storage.set_limit(4096)
    assert storage.Interval == 1.5
    assert storage.Limit == 4096

def test_interval_has_a_floor(storage):
    storage.set_interval(0.0)
    assert storage.Interval >= 0.1

def test_lock_blocks_the_setters(storage):
    storage.set_interval(1.0)
    storage.lock()
    storage.set_interval(9.0)
    storage.set_limit(1)
    assert storage.Interval == 1.0
    storage.unlock()

def test_identifier_tracks_the_record(storage):
    assert storage.Identifier is None
    record = _attach_(storage)
    assert storage.Identifier == record.UID

def test_format_matches_the_file_sink(storage):
    line = storage._format_(VerboseLevel.Error, "2026-07-30 12:00:00.000", "EURUSD - ", "Engine - ", "message")
    assert line == "2026-07-30 12:00:00.000 - EURUSD - Error - Engine - message\n"