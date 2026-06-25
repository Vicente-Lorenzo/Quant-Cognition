from __future__ import annotations

import atexit
import queue
import threading

from datetime import datetime, timedelta
from collections.abc import Sequence
from typing import Callable, Type, Union, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Postgres.Postgres import PostgresAPI
from Library.Logging import HandlerLoggingAPI
from Library.Utility.Statistic import Timer

if TYPE_CHECKING:
    from Library.Database.Database import DatabaseAPI

class BufferAPI(threading.Thread):

    def __init__(self,
                 types: Sequence[Type[DatapointAPI]],
                 batch: int = 0,
                 interval: float = 0.0,
                 by: str = "Autosave",
                 workers: int = 0,
                 maxsize: int = 0,
                 bulk: bool = False,
                 db: Union[Callable[[], DatabaseAPI], None] = None) -> None:
        super().__init__(daemon=True, name=f"{type(self).__name__}-Worker")

        self._types_: tuple = tuple(types)
        self._batch_: int = batch
        self._interval_: float = interval
        self._by_: str = by
        self._bulk_: bool = bulk
        self._workers_: int = max(1, workers)
        self._full_: bool = batch < 0
        self._active_: bool = workers > 0 and (self._full_ or batch > 0 or interval > 0)

        self._buffer_: dict = {t: [] for t in self._types_}
        self._count_: int = 0
        self._queue_: dict = {t: queue.Queue(maxsize=maxsize) for t in self._types_}
        self._signal_: queue.Queue = queue.Queue()
        self._work_: queue.Queue = queue.Queue()
        self._last_flush_: datetime = datetime.now()

        self._db_: Callable[[], DatabaseAPI] = db or (lambda: PostgresAPI(database=DatapointAPI.Database))

        self._log_: HandlerLoggingAPI = HandlerLoggingAPI(Class=self.__class__.__name__, Subclass="Buffer Management")

        if not self._active_:
            self.add = self._noop_
            self.flush = self._noop_
        else:
            atexit.register(self.shutdown)

    @property
    def Active(self) -> bool:
        return self._active_

    @property
    def Empty(self) -> bool:
        if not self._active_: return True
        total = self._count_
        if total == 0: return True
        if self._full_: return True
        if 0 < self._batch_ <= total: return False
        if self._interval_ > 0 and (datetime.now() - self._last_flush_) >= timedelta(seconds=self._interval_): return False
        return True

    @staticmethod
    def _noop_(*args, **kwargs) -> None:
        pass

    def add(self, record: DatapointAPI) -> None:
        if not self._active_: return
        self._buffer_[type(record)].append(record)
        self._count_ += 1

    def flush(self) -> None:
        pushed = False
        for t in self._types_:
            buffer = self._buffer_[t]
            if not buffer: continue
            self._queue_[t].put(buffer[:])
            buffer.clear()
            pushed = True
        self._count_ = 0
        self._last_flush_ = datetime.now()
        if pushed: self._signal_.put(True)

    def shutdown(self) -> None:
        if not self._active_: return
        self.flush()
        self._signal_.put(None)
        if self.is_alive(): self.join()

    def _collect_(self, t: Type[DatapointAPI]) -> list:
        records: list = []
        q = self._queue_[t]
        while True:
            try: records.extend(q.get_nowait())
            except queue.Empty: break
        return records

    def _partition_(self, records: list) -> list:
        key = records[0].natural_keys()
        buckets: list = [[] for _ in range(self._workers_)]
        for r in records:
            uid = getattr(r, "UID", None)
            bucket = (hash(uid) % self._workers_) if isinstance(uid, int) else (hash(tuple(str(r._parse_(c)) for c in key)) % self._workers_ if key else 0)
            buckets[bucket].append(r)
        return buckets

    def _write_(self, db: DatabaseAPI, t: Type[DatapointAPI], records: list) -> None:
        if not records: return
        stamp = datetime.now()
        try:
            timer = Timer(); timer.start()
            identity = records[0].identity_keys()
            key = records[0].natural_keys()
            structure = getattr(records[0], "Structure", None)
            columns = {str(c) for c in structure.keys()} if structure else None
            valid_cols = [c for c in columns if c not in identity and hasattr(records[0], c)] if columns is not None else None
            if identity:
                unique, mapping = {}, {}
                for r in records:
                    r._stamp_(self._by_, stamp)
                    row = {c: r._parse_(c) for c in valid_cols} if valid_cols is not None else {k: v for k, v in r.dict().items() if k not in identity}
                    k = tuple(str(row.get(c)) for c in key)
                    unique[k] = row
                    mapping.setdefault(k, []).append(r)
                data = list(unique.values())
                df = db.upsert(schema=t.Schema, table=t.Table, data=data, key=key, returning=identity)
                for i, k in enumerate(unique.keys()):
                    if i >= len(df): break
                    for col in identity:
                        val = df[col][i]
                        for r in mapping[k]: setattr(r, col, val)
                count = len(data)
            else:
                if valid_cols is not None:
                    buffers = {c: [] for c in valid_cols}
                    for r in records:
                        r._stamp_(self._by_, stamp)
                        for c in valid_cols: buffers[c].append(r._parse_(c))
                    frame = pl.DataFrame(buffers, strict=False)
                else:
                    for r in records: r._stamp_(self._by_, stamp)
                    frame = pl.DataFrame([r.dict() for r in records], strict=False)
                if key: frame = frame.unique(subset=list(key), keep="last")
                writer = db.merge if self._bulk_ else db.upsert
                writer(schema=t.Schema, table=t.Table, data=frame, key=key)
                count = frame.height
            timer.stop()
            self._log_.debug(lambda: f"Drain {t.Table}: {len(records)} Records · {count} Unique Rows ({timer.result()})")
        except Exception as e:
            self._log_.error(lambda: f"Drain {t.Table}: Failed · {e}")

    def _consume_(self, db: DatabaseAPI) -> None:
        snapshot = {t: self._collect_(t) for t in reversed(self._types_)}
        for t in self._types_:
            records = snapshot.get(t)
            if records: self._write_(db, t, records)

    def _dispatch_(self) -> None:
        snapshot = {t: self._collect_(t) for t in reversed(self._types_)}
        for t in self._types_:
            records = snapshot.get(t)
            if not records: continue
            parts = [part for part in self._partition_(records) if part]
            latch = threading.Semaphore(0)
            for part in parts: self._work_.put((t, part, latch))
            for _ in parts: latch.acquire()

    def _worker_(self) -> None:
        with self._db_() as db:
            while True:
                task = self._work_.get()
                if task is None: break
                t, records, latch = task
                try: self._write_(db, t, records)
                finally: latch.release()

    def run(self) -> None:
        if self._workers_ <= 1:
            with self._db_() as db:
                while True:
                    wake = self._signal_.get()
                    if wake is None: break
                    self._consume_(db)
            return
        threads = [threading.Thread(target=self._worker_, daemon=True, name=f"{type(self).__name__}-Persist") for _ in range(self._workers_)]
        for thread in threads: thread.start()
        try:
            while True:
                wake = self._signal_.get()
                if wake is None: break
                self._dispatch_()
        finally:
            for _ in threads: self._work_.put(None)
            for thread in threads: thread.join()