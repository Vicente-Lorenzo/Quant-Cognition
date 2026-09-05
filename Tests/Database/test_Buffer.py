import atexit
import threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from Library.Database import BufferAPI

class _RecA_:

    Schema = "Test"
    Table = "A"

    def __init__(self, v): self.v = v; self.UID = None

    def dict(self): return {"v": self.v}

    def identity_keys(self): return ["UID"]

    def natural_keys(self): return ["v"]

    def _parse_(self, c): return getattr(self, c)

    def _stamp_(self, by, at=None): pass

class _RecB_:

    Schema = "Test"
    Table = "B"

    def __init__(self, v): self.v = v; self.UID = None

    def dict(self): return {"v": self.v}

    def identity_keys(self): return ["UID"]

    def natural_keys(self): return ["v"]

    def _parse_(self, c): return getattr(self, c)

    def _stamp_(self, by, at=None): pass

class _RecC_:

    Schema = "Test"
    Table = "C"

    def __init__(self, v): self.v = v

    def dict(self): return {"v": self.v}

    def identity_keys(self): return []

    def natural_keys(self): return ["v"]

    def _parse_(self, c): return getattr(self, c)

    def _stamp_(self, by, at=None): pass

def _make_buffer_(batch=10, interval=0.0, workers=1, types=(_RecA_, _RecB_)):
    db_factory = MagicMock()
    return BufferAPI(types=types, batch=batch, interval=interval, workers=workers, db=db_factory), db_factory

def test_inactive_when_thresholds_zero():
    buf, _ = _make_buffer_(batch=0, interval=0.0)
    assert buf.Active is False

def test_inactive_when_workers_zero():
    buf, _ = _make_buffer_(batch=10, interval=1.0, workers=0)
    assert buf.Active is False

def test_default_workers_zero_is_inactive():
    db_factory = MagicMock()
    buf = BufferAPI(types=(_RecA_,), batch=10, interval=1.0, db=db_factory)
    assert buf.Active is False

def test_active_when_batch_positive():
    buf, _ = _make_buffer_(batch=5, interval=0.0)
    assert buf.Active is True

def test_active_when_interval_positive():
    buf, _ = _make_buffer_(batch=0, interval=1.0)
    assert buf.Active is True

def test_empty_true_when_inactive():
    buf, _ = _make_buffer_(batch=0, interval=0.0)
    assert buf.Empty is True

def test_empty_true_when_no_records():
    buf, _ = _make_buffer_(batch=10, interval=0.0)
    assert buf.Empty is True

def test_empty_false_when_batch_reached():
    buf, _ = _make_buffer_(batch=3, interval=0.0)
    for _ in range(3): buf.add(_RecA_(1))
    assert buf.Empty is False

def test_empty_false_when_interval_elapsed():
    buf, _ = _make_buffer_(batch=100, interval=0.001)
    buf._last_flush_ = datetime.now() - timedelta(seconds=1)
    buf.add(_RecA_(1))
    assert buf.Empty is False

def test_full_mode_is_active():
    buf, _ = _make_buffer_(batch=-1, interval=0.0)
    assert buf.Active is True

def test_full_mode_never_empty_false_before_shutdown():
    buf, _ = _make_buffer_(batch=-1, interval=0.0)
    for v in range(50): buf.add(_RecA_(v))
    assert len(buf._buffer_[_RecA_]) == 50
    assert buf.Empty is True

def test_full_mode_flush_moves_records_to_queue():
    buf, _ = _make_buffer_(batch=-1, interval=0.0)
    for v in range(50): buf.add(_RecA_(v))
    buf.flush()
    assert buf._buffer_[_RecA_] == []
    assert not buf._queue_[_RecA_].empty()

def test_add_dispatches_by_type():
    buf, _ = _make_buffer_(batch=10, interval=0.0)
    a, b = _RecA_(1), _RecB_(2)
    buf.add(a); buf.add(b)
    assert buf._buffer_[_RecA_] == [a]
    assert buf._buffer_[_RecB_] == [b]

def test_add_noop_when_inactive():
    buf, _ = _make_buffer_(batch=0, interval=0.0)
    buf.add(_RecA_(1))
    assert buf._buffer_[_RecA_] == []

def test_flush_enqueues_per_type_in_declared_order():
    buf, _ = _make_buffer_(batch=10, interval=0.0, types=(_RecA_, _RecB_))
    buf.add(_RecA_(1)); buf.add(_RecB_(2))
    buf.flush()
    assert buf._buffer_[_RecA_] == []
    assert buf._buffer_[_RecB_] == []
    assert not buf._queue_[_RecA_].empty()
    assert not buf._queue_[_RecB_].empty()

def test_flush_signals_worker():
    buf, _ = _make_buffer_(batch=10, interval=0.0)
    buf.add(_RecA_(1))
    buf.flush()
    assert buf._signal_.get_nowait() is True

def test_flush_no_signal_when_buffers_empty():
    buf, _ = _make_buffer_(batch=10, interval=0.0)
    buf.flush()
    assert buf._signal_.empty()

def test_flush_clears_buffers():
    buf, _ = _make_buffer_(batch=10, interval=0.0)
    buf.add(_RecA_(1)); buf.add(_RecA_(2))
    buf.flush()
    assert buf._buffer_[_RecA_] == []

def test_consume_calls_upsert_per_type_in_fk_order():
    buf, _ = _make_buffer_(batch=10, interval=0.0, types=(_RecA_, _RecB_))
    buf.add(_RecA_(1)); buf.add(_RecB_(2)); buf.flush()
    db = MagicMock()
    df = MagicMock()
    df.__getitem__ = lambda s, k: [99]
    df.__len__ = lambda s: 1
    db.upsert.return_value = df
    buf._consume_(db)
    calls = db.upsert.call_args_list
    assert calls[0].kwargs["table"] == "A"
    assert calls[1].kwargs["table"] == "B"

def test_consume_backfills_identity_uid():
    buf, _ = _make_buffer_(batch=10, interval=0.0)
    rec = _RecA_(1)
    buf.add(rec); buf.flush()
    db = MagicMock()
    df = MagicMock()
    df.__getitem__ = lambda s, k: [42]
    df.__len__ = lambda s: 1
    db.upsert.return_value = df
    buf._consume_(db)
    assert rec.UID == 42

def test_consume_skips_returning_when_no_identity():
    buf, _ = _make_buffer_(batch=10, interval=0.0, types=(_RecC_,))
    buf.add(_RecC_(1)); buf.flush()
    db = MagicMock()
    buf._consume_(db)
    kwargs = db.upsert.call_args.kwargs
    assert "returning" not in kwargs

def test_shutdown_drains_and_signals_sentinel():
    buf, _ = _make_buffer_(batch=10, interval=0.0)
    buf.add(_RecA_(1))
    buf.shutdown()
    items = []
    while not buf._signal_.empty(): items.append(buf._signal_.get_nowait())
    assert items[-1] is None

def test_shutdown_is_noop_when_inactive():
    buf, _ = _make_buffer_(batch=0, interval=0.0)
    buf.shutdown()
    assert buf._signal_.empty()

def test_shutdown_idempotent():
    buf, _ = _make_buffer_(batch=10, interval=0.0)
    buf.shutdown(); buf.shutdown()

def test_atexit_registered_when_active():
    with patch.object(atexit, "register") as mock_reg:
        buf, _ = _make_buffer_(batch=10, interval=0.0)
        assert mock_reg.called
        assert mock_reg.call_args.args[0] == buf.shutdown

def test_atexit_not_registered_when_inactive():
    with patch.object(atexit, "register") as mock_reg:
        _make_buffer_(batch=0, interval=0.0)
        assert not mock_reg.called

def test_run_opens_db_and_drains_until_sentinel():
    buf, db_factory = _make_buffer_(batch=10, interval=0.0)
    db = MagicMock()
    db.__enter__ = MagicMock(return_value=db)
    db.__exit__ = MagicMock(return_value=False)
    db_factory.return_value = db
    buf.add(_RecA_(1))
    buf.flush()
    buf._signal_.put(None)
    buf.run()
    db.upsert.assert_called_once()

def test_partition_groups_same_key_into_one_bucket():
    buf, _ = _make_buffer_(batch=10, interval=0.0, types=(_RecA_,))
    buf._workers_ = 4
    records = [_RecA_(v) for v in (1, 2, 3, 1, 2, 1)]
    buckets = buf._partition_(records)
    assert sum(len(b) for b in buckets) == len(records)
    located = {}
    for index, bucket in enumerate(buckets):
        for r in bucket: located.setdefault(r.v, index)
    for index, bucket in enumerate(buckets):
        for r in bucket: assert located[r.v] == index

class _RecorderDB_:

    def __init__(self, log, lock):
        self._log_, self._lock_ = log, lock

    def __enter__(self): return self

    def __exit__(self, *a): return False

    def upsert(self, **kwargs):
        with self._lock_: self._log_.append(kwargs["table"])
        return self

class _ParallelFactory_:

    def __init__(self):
        self.log, self.lock = [], threading.Lock()

    def __call__(self): return _RecorderDB_(self.log, self.lock)

def test_run_parallel_persists_all_and_preserves_type_barrier():
    factory = _ParallelFactory_()
    buf = BufferAPI(types=(_RecC_, _RecB_), batch=100, interval=0.0, workers=4, db=factory)
    for v in range(20): buf.add(_RecC_(v))
    for v in range(20): buf.add(_RecB_(v))
    buf.flush()
    buf._signal_.put(None)
    buf.run()
    assert factory.log.count("C") >= 1
    assert factory.log.count("B") >= 1
    assert max(i for i, t in enumerate(factory.log) if t == "C") < min(i for i, t in enumerate(factory.log) if t == "B")