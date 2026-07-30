import io
import pstats
import cProfile

from typing import Callable
from functools import wraps
from datetime import datetime
from time import perf_counter
from dataclasses import dataclass, field

from Library.Utility.Datetime import datetime_to_string, seconds_to_string

@dataclass(kw_only=True)
class Timer:
    _start_: float = field(default=None, init=True, repr=False)
    _stop_: float = field(default=None, init=True, repr=False)

    def start(self):
        self._start_ = perf_counter()

    def stop(self):
        self._stop_ = perf_counter()

    def delta(self):
        return self._stop_ - self._start_

    def result(self):
        return seconds_to_string(self.delta())

def timer(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        from Library.Logging import LoggingAPI
        log = LoggingAPI()
        t = Timer()
        t.start()
        result = func(*args, **kwargs)
        t.stop()
        log.debug(lambda: f"Time @ {func.__name__}: {t.result()}")
        return result
    return wrapper

def profiler(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        from Library.Logging import LoggingAPI
        log = LoggingAPI()
        timestamp = datetime_to_string(datetime.now(), "%Y%m%d-%H%M%S")
        with cProfile.Profile() as pr:
            result = func(*args, **kwargs)
        ps = pstats.Stats(pr, stream=io.StringIO())
        snapshot_path = f"profile-{timestamp}.pstat"
        ps.dump_stats(snapshot_path)
        log.warning(lambda: f"Profile @ {func.__name__}: Snapshot {snapshot_path}")
        return result
    return wrapper