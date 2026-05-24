from __future__ import annotations

import atexit
import queue
import threading

from datetime import datetime, timedelta
from collections.abc import Sequence
from typing import Callable, Type, Union, TYPE_CHECKING

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
                 db: Union[Callable[[], DatabaseAPI], None] = None) -> None:
        super().__init__(daemon=True, name=f"{type(self).__name__}-Worker")

        self._types_: tuple = tuple(types)
        self._batch_: int = batch
        self._interval_: float = interval
        self._by_: str = by
        self._active_: bool = batch > 0 or interval > 0

        self._buffer_: dict = {t: [] for t in self._types_}
        self._queue_: dict = {t: queue.Queue() for t in self._types_}
        self._signal_: queue.Queue = queue.Queue()
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
        total = sum(len(b) for b in self._buffer_.values())
        if total == 0: return True
        if 0 < self._batch_ <= total: return False
        if self._interval_ > 0 and (datetime.now() - self._last_flush_) >= timedelta(seconds=self._interval_): return False
        return True

    @staticmethod
    def _noop_(*args, **kwargs) -> None:
        pass

    def add(self, record: DatapointAPI) -> None:
        self._buffer_[type(record)].append(record)

    def flush(self) -> None:
        pushed = False
        for t in self._types_:
            buffer = self._buffer_[t]
            if not buffer: continue
            self._queue_[t].put(buffer[:])
            buffer.clear()
            pushed = True
        self._last_flush_ = datetime.now()
        if pushed: self._signal_.put(True)

    def shutdown(self) -> None:
        if not self._active_: return
        self.flush()
        self._signal_.put(None)
        if self.is_alive(): self.join(timeout=10.0)

    def _drain_(self, db: DatabaseAPI, t: Type[DatapointAPI]) -> None:
        q = self._queue_[t]
        stamp = datetime.now()
        while not q.empty():
            try: records = q.get_nowait()
            except queue.Empty: break
            try:
                timer = Timer(); timer.start()
                identity = records[0].identity_keys()
                key = records[0].natural_keys()
                structure = getattr(records[0], "Structure", None)
                columns = {str(c) for c in structure.keys()} if structure else None
                unique, mapping = {}, {}
                valid_cols = None
                if columns is not None:
                    valid_cols = [c for c in columns if c not in identity and hasattr(records[0], c)]
                for r in records:
                    r._stamp_(self._by_, stamp)
                    if valid_cols is not None:
                        row = {c: r._parse_(c) for c in valid_cols}
                    else:
                        row = {k: v for k, v in r.dict().items() if k not in identity}
                    k = tuple(str(row.get(c)) for c in key)
                    unique[k] = row
                    mapping.setdefault(k, []).append(r)
                data = list(unique.values())
                if identity:
                    df = db.upsert(schema=t.Schema, table=t.Table, data=data, key=key, returning=identity)
                    for i, k in enumerate(unique.keys()):
                        if i >= len(df): break
                        for col in identity:
                            val = df[col][i]
                            for r in mapping[k]: setattr(r, col, val)
                else:
                    db.upsert(schema=t.Schema, table=t.Table, data=data, key=key)
                timer.stop()
                self._log_.debug(lambda: f"Drain {t.Table}: {len(records)} records, {len(data)} unique rows ({timer.result()})")
            except Exception as e:
                self._log_.error(lambda: f"Persist error on {t.Table}: {e}")

    def _consume_(self, db: DatabaseAPI) -> None:
        for t in self._types_: self._drain_(db, t)

    def run(self) -> None:
        with self._db_() as db:
            while True:
                wake = self._signal_.get()
                if wake is None: break
                self._consume_(db)