from datetime import datetime, timedelta
from Library.Database import BufferAPI
from Library.Database.Query import QueryAPI
from Library.Market.Bar import BarAPI
from Library.Market.Tick import TickAPI

def _make_tick_(security, dt, ask, bid):
    return TickAPI(Security=security, Timestamp=dt, Ask=ask, Bid=bid)

def _make_bar_(security, timeframe, dt, ticks):
    g, o, h, l, c = ticks
    return BarAPI(Security=security, Timeframe=timeframe, Timestamp=dt, GapTick=g, OpenTick=o, HighTick=h, LowTick=l, CloseTick=c, Volume=5.0)

def test_buffer_fk_chain_ticks_then_bar(db, universe, market):
    sec = universe["security"]
    tf = universe["timeframe"]
    db.executeone(QueryAPI(f'DELETE FROM "{BarAPI.Schema}"."{BarAPI.Table}"')).commit()
    db.executeone(QueryAPI(f'DELETE FROM "{TickAPI.Schema}"."{TickAPI.Table}"')).commit()
    dt = datetime(2025, 1, 1, 12, 0, 0)
    ticks = [
        _make_tick_(sec, dt - timedelta(seconds=5), 1.1000, 1.0998),
        _make_tick_(sec, dt - timedelta(seconds=4), 1.1010, 1.1008),
        _make_tick_(sec, dt - timedelta(seconds=3), 1.1020, 1.1018),
        _make_tick_(sec, dt - timedelta(seconds=2), 1.0990, 1.0988),
        _make_tick_(sec, dt - timedelta(seconds=1), 1.1005, 1.1003)
    ]
    bar = _make_bar_(sec, tf, dt, ticks)
    buf = BufferAPI(types=[TickAPI, BarAPI], batch=10, interval=0.0, workers=1, db=lambda: db)
    for t in ticks: buf.add(t)
    buf.add(bar)
    buf.flush()
    buf._consume_(db)
    for t in ticks: assert t.UID is not None
    row = db.select(schema=BarAPI.Schema, table=BarAPI.Table, condition='"Timestamp" = :dt:', parameters={"dt": dt}, limit=1, legacy=False)
    assert not row.is_empty()
    persisted = row.row(0, named=True)
    assert persisted["GapTick"] == ticks[0].UID
    assert persisted["OpenTick"] == ticks[1].UID
    assert persisted["HighTick"] == ticks[2].UID
    assert persisted["LowTick"] == ticks[3].UID
    assert persisted["CloseTick"] == ticks[4].UID

def test_buffer_fk_chain_handles_multiple_bars(db, universe, market):
    sec = universe["security"]
    tf = universe["timeframe"]
    db.executeone(QueryAPI(f'DELETE FROM "{BarAPI.Schema}"."{BarAPI.Table}"')).commit()
    db.executeone(QueryAPI(f'DELETE FROM "{TickAPI.Schema}"."{TickAPI.Table}"')).commit()
    base = datetime(2025, 2, 1, 12, 0, 0)
    all_ticks = []
    bars = []
    for i in range(3):
        dt = base + timedelta(minutes=i)
        ticks = [_make_tick_(sec, dt - timedelta(seconds=5 - j), 1.1 + 0.001 * (j + i), 1.0998 + 0.001 * (j + i)) for j in range(5)]
        bars.append(_make_bar_(sec, tf, dt, ticks))
        all_ticks.extend(ticks)
    buf = BufferAPI(types=[TickAPI, BarAPI], batch=100, interval=0.0, workers=1, db=lambda: db)
    for t in all_ticks: buf.add(t)
    for b in bars: buf.add(b)
    buf.flush()
    buf._consume_(db)
    assert all(t.UID is not None for t in all_ticks)
    for i, b in enumerate(bars):
        row = db.select(schema=BarAPI.Schema, table=BarAPI.Table, condition='"Timestamp" = :dt:', parameters={"dt": base + timedelta(minutes=i)}, limit=1, legacy=False)
        persisted = row.row(0, named=True)
        offset = i * 5
        assert persisted["GapTick"] == all_ticks[offset].UID
        assert persisted["CloseTick"] == all_ticks[offset + 4].UID

def test_buffer_merge_bulk_fk_chain_idempotent(db, universe, market):
    sec = universe["security"]
    tf = universe["timeframe"]
    db.executeone(QueryAPI(f'DELETE FROM "{BarAPI.Schema}"."{BarAPI.Table}"')).commit()
    db.executeone(QueryAPI(f'DELETE FROM "{TickAPI.Schema}"."{TickAPI.Table}"')).commit()
    dt = datetime(2025, 3, 1, 12, 0, 0)
    ticks = [_make_tick_(sec, dt - timedelta(seconds=5 - j), 1.1 + 0.001 * j, 1.0998 + 0.001 * j) for j in range(5)]
    bar = _make_bar_(sec, tf, dt, ticks)
    def _run_():
        buf = BufferAPI(types=[TickAPI, BarAPI], batch=10, interval=0.0, workers=1, bulk=True, db=lambda: db)
        for t in ticks: buf.add(t)
        buf.add(bar)
        buf.flush()
        buf._consume_(db)
    _run_()
    _run_()
    count = db.executeone(QueryAPI(f'SELECT count(*) AS n FROM "{TickAPI.Schema}"."{TickAPI.Table}"')).fetchall(legacy=False)
    assert count.row(0, named=True)["n"] == 5
    row = db.select(schema=BarAPI.Schema, table=BarAPI.Table, condition='"Timestamp" = :dt:', parameters={"dt": dt}, limit=1, legacy=False)
    assert not row.is_empty()
    persisted = row.row(0, named=True)
    assert persisted["GapTick"] == ticks[0].UID
    assert persisted["CloseTick"] == ticks[4].UID
