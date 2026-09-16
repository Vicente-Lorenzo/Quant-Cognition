from __future__ import annotations

import os
import queue
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from Library.Utility.Datetime import utc_now
from Library.Utility.Runtime import find_user
from Library.Utility.Typing import MISSING, Missing
from Library.Logging.Level import VerboseLevel
from Library.Logging.Logger import LoggerAPI
from Library.Logging.File import FileAPI

if TYPE_CHECKING:
    from Library.Database.Database import DatabaseAPI
    from Library.Logging.Log import LogAPI

class StorageAPI(LoggerAPI):
    """
    Durable database sink writing one row per log rather than one row per record.

    Unlike the console and file sinks this one talks to a remote service, so a single insert costs
    orders of magnitude more than a local append. Three properties keep that affordable. Records are
    handed to a bounded queue and written by a background thread, so a caller never waits on the
    database. The level defaults to Warning, so routine Debug and Info traffic does not reach it unless
    it is asked for explicitly. Content accumulates in memory and is flushed on a cadence, so a busy log costs a
    periodic update instead of an insert per line.

    The sink is inert until attach() is called and reverts to inert on detach().
    """

    _DEFAULT_: VerboseLevel = VerboseLevel.Warning
    _LIMIT_: int = 8 * 1024 * 1024
    _INTERVAL_: float = 2.0
    _CAPACITY_: int = 100000

    Name: str = "Storage"

    def __init__(self, level: VerboseLevel = VerboseLevel.Silent) -> None:
        super().__init__(level=level)
        self._db_: "DatabaseAPI | None" = None
        self._record_: "LogAPI | None" = None
        self._queue_: queue.Queue = queue.Queue(maxsize=self._CAPACITY_)
        self._thread_: threading.Thread | None = None
        self._signal_: threading.Event = threading.Event()
        self._guard_: threading.local = threading.local()
        self._buffer_: list = []
        self._length_: int = 0
        self._records_: int = 0
        self._dropped_: int = 0
        self._truncated_: bool = False
        self._interval_: float = self._INTERVAL_
        self._limit_: int = self._LIMIT_

    @property
    def Record(self) -> "LogAPI | None":
        return self._record_

    @property
    def Identifier(self) -> str | None:
        return self._record_.UID if self._record_ is not None else None

    @property
    def Attached(self) -> bool:
        return self._record_ is not None

    @property
    def Records(self) -> int:
        return self._records_

    @property
    def Dropped(self) -> int:
        return self._dropped_

    @property
    def Truncated(self) -> bool:
        return self._truncated_

    @property
    def Interval(self) -> float:
        return self._interval_

    @property
    def Limit(self) -> int:
        return self._limit_

    def attach(self, db: "DatabaseAPI", source: str = None, path: str | Path = None, migrate: bool = False) -> "LogAPI":
        """
        Opens a durable row for this log and starts the background writer.

        The row is inserted immediately rather than at completion so that anything reading the
        database can resolve the log while the work is still in flight.
        :param db: An open database connection owned by the caller.
        :param source: A label identifying what produced the log; defaults to the process name.
        :param path: Optional filesystem location of the same log, for live tailing.
        :param migrate: Whether to create the table if it is absent.
        :return: The freshly inserted log row.
        """
        from Library.Logging.Log import LogAPI
        self.detach()
        self._db_ = db
        self._record_ = LogAPI.start(db, source=source or FileAPI._origin_(), level=self._level_.name, user=find_user() or "Unknown", process=os.getpid(), path=path, migrate=migrate)
        self._buffer_, self._length_, self._records_, self._dropped_, self._truncated_ = [], 0, 0, 0, False
        self._signal_.clear()
        self._thread_ = threading.Thread(target=self._drain_, name="StorageLogging", daemon=True)
        self._thread_.start()
        return self._record_

    def detach(self, timeout: float = 5.0) -> None:
        """
        Stops the background writer, performs a final flush and closes the row.
        :param timeout: Seconds to wait for the writer to finish draining.
        """
        thread, self._thread_ = self._thread_, None
        if thread is not None:
            self._signal_.set()
            thread.join(timeout=timeout)
        if self._record_ is not None:
            try: self._persist_(stopped=utc_now())
            except Exception as error:
                self._fallback_(error)
        self._db_, self._record_ = None, None
        while not self._queue_.empty():
            try: self._queue_.get_nowait()
            except queue.Empty: break

    def set_level(self, level: str | int | VerboseLevel, default: bool = False, force: bool = False) -> None:
        """
        Sets the accepted level.

        The level defaults to Warning and a more verbose one may be set deliberately; the queue is what
        keeps a remote sink from being handed a Debug firehose.
        """
        super().set_level(VerboseLevel.resolve(level), default=default, force=force)

    def set_interval(self, interval: float) -> None:
        """Sets the flush cadence in seconds."""
        if self._locked_: return
        self._interval_ = max(0.1, interval)

    def set_limit(self, limit: int) -> None:
        """Sets the maximum accumulated content in bytes before the log is marked truncated."""
        if self._locked_: return
        self._limit_ = max(0, limit)

    def _persist_(self, stopped: datetime | None | Missing = MISSING) -> None:
        if self._record_ is None: return
        self._record_.stop("".join(self._buffer_), records=self._records_, dropped=self._dropped_, truncated=self._truncated_, stopped=stopped)

    def _flush_(self) -> None:
        if self._record_ is None or self._db_ is None: return
        self._guard_.busy = True
        try: self._persist_()
        finally: self._guard_.busy = False

    def _collect_(self) -> bool:
        collected = False
        while True:
            try: line = self._queue_.get_nowait()
            except queue.Empty: break
            collected = True
            self._records_ += 1
            if self._length_ >= self._limit_ > 0:
                self._truncated_ = True
                continue
            self._buffer_.append(line)
            self._length_ += len(line)
        return collected

    def _drain_(self) -> None:
        while not self._signal_.is_set():
            self._signal_.wait(self._interval_)
            try:
                if self._collect_(): self._flush_()
            except Exception as error:
                self._fallback_(error)
        try:
            if self._collect_(): self._flush_()
        except Exception as error:
            self._fallback_(error)

    def _write_(self, line: str) -> None:
        if self._record_ is None or getattr(self._guard_, "busy", False): return
        try: self._queue_.put_nowait(line)
        except queue.Full: self._dropped_ += 1