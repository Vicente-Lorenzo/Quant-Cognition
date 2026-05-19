from __future__ import annotations

import atexit
import queue
import threading

from datetime import datetime, timedelta
from collections.abc import Sequence
from typing import Callable, Type, Union, TYPE_CHECKING

from Library.Logging import HandlerLoggingAPI
from Library.Database.Postgres.Postgres import PostgresAPI

if TYPE_CHECKING:
    from Library.Database.Database import DatabaseAPI
    from Library.Database.Datapoint import DatapointAPI

class BufferAPI(threading.Thread):

    def __init__(self,
                 types: Sequence[Type[DatapointAPI]],
                 batch: int = 0,
                 interval: float = 0.0,
                 db: Union[Callable[[], DatabaseAPI], None] = None) -> None:
        super().__init__(daemon=True, name=f"{type(self).__name__}-Worker")

        self._types_: tuple = tuple(types)
        self._batch_: int = batch
        self._interval_: float = interval
        self._active_: bool = batch > 0 or interval > 0

        self._buffer_: dict = {t: [] for t in self._types_}
        self._queue_: dict = {t: queue.Queue() for t in self._types_}
        self._signal_: queue.Queue = queue.Queue()
        self._last_flush_: datetime = datetime.now()

        self._db_: Callable[[], DatabaseAPI] = db or (lambda: PostgresAPI(database="Quant"))

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
        while not q.empty():
            try: records = q.get_nowait()
            except queue.Empty: break
            try:
                identity = records[0].identity_keys()
                data = [r.dict() for r in records]
                key = records[0].natural_keys()
                if identity:
                    df = db.upsert(schema=t.Schema, table=t.Table, data=data, key=key, returning=identity)
                    for i, r in enumerate(records):
                        if i >= len(df): break
                        for col in identity:
                            setattr(r, col, df[col][i])
                else:
                    db.upsert(schema=t.Schema, table=t.Table, data=data, key=key)
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