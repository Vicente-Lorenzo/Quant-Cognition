import threading
from concurrent.futures import ThreadPoolExecutor

from Library.Logging import LoggingAPI, VerboseLevel

def test_every_record_from_every_thread_is_written(tmp_path, lines):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=0)
    threads, records = 8, 250
    def worker(index):
        log = LoggingAPI(f"Worker{index}")
        for step in range(records): log.info(lambda: f"Worker {index} Record {step}")
    with ThreadPoolExecutor(max_workers=threads) as pool:
        list(pool.map(worker, range(threads)))
    LoggingAPI.file.flush()
    assert len(lines()) == threads * records

def test_no_line_is_torn_under_concurrency(tmp_path, lines):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=0)
    def worker(index):
        log = LoggingAPI(f"Worker{index}")
        for step in range(200): log.info(lambda: f"BEGIN-{index}-{step}-{'x' * 120}-END")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(worker, range(8)))
    LoggingAPI.file.flush()
    for line in lines():
        assert line.count("BEGIN-") == 1
        assert line.endswith("-END")

def test_concurrent_level_changes_never_corrupt_state(tmp_path):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    stop = threading.Event()
    def flipper():
        while not stop.is_set():
            LoggingAPI.console.set_level(VerboseLevel.Debug)
            LoggingAPI.console.set_level(VerboseLevel.Silent)
    def writer():
        log = LoggingAPI("Writer")
        for step in range(2000): log.info(lambda: f"Record {step}")
    flip = threading.Thread(target=flipper, daemon=True)
    flip.start()
    try:
        writer()
    finally:
        stop.set()
        flip.join(timeout=5)
    assert LoggingAPI.console.Level in (VerboseLevel.Debug, VerboseLevel.Silent)

def test_concurrent_rotation_is_safe(tmp_path, lines):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=2048, count=3)
    def worker(index):
        log = LoggingAPI(f"Worker{index}")
        for step in range(300): log.info(lambda: f"Worker {index} Record {step} {'y' * 60}")
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(worker, range(6)))
    LoggingAPI.file.flush()
    assert LoggingAPI.file.Path.exists()

def test_concurrent_instances_keep_their_own_tags(tmp_path, lines):
    LoggingAPI.file.set_level(VerboseLevel.Debug)
    LoggingAPI.file.set_rotation(size=0)
    def worker(index):
        log = LoggingAPI(f"Tag{index}")
        for _ in range(100): log.info(lambda: "message")
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(worker, range(6)))
    LoggingAPI.file.flush()
    for index in range(6):
        assert sum(1 for line in lines() if f"test_Concurrency - Tag{index} - message" in line) == 100

def test_shared_sink_state_is_visible_across_threads(tmp_path):
    LoggingAPI.file.set_level(VerboseLevel.Silent)
    seen = []
    def reader():
        seen.append(LoggingAPI.file.Level)
    LoggingAPI.file.set_level(VerboseLevel.Error)
    thread = threading.Thread(target=reader)
    thread.start()
    thread.join()
    assert seen == [VerboseLevel.Error]

def test_temporary_level_in_one_thread_is_global(tmp_path):
    LoggingAPI.file.set_level(VerboseLevel.Warning)
    observed = []
    def reader(barrier):
        barrier.wait(timeout=5)
        observed.append(LoggingAPI.file.Level)
        barrier.wait(timeout=5)
    barrier = threading.Barrier(2)
    thread = threading.Thread(target=reader, args=(barrier,))
    thread.start()
    with LoggingAPI.file.temporary(VerboseLevel.Debug):
        barrier.wait(timeout=5)
        barrier.wait(timeout=5)
    thread.join(timeout=5)
    assert observed == [VerboseLevel.Debug]
    assert LoggingAPI.file.Level is VerboseLevel.Warning