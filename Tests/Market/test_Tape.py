import gc
import pytest

from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor

from Library.Database.Dataframe import np
from Library.Market.Bar import BarAPI
from Library.Market.Point import PointAPI
from Library.Market.Tape import ShareAPI, TapeAPI
from Library.Market.Tick import TickAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Datetime import datetime_to_epoch

def _tape_(*ticks: tuple, security: int = 1) -> TapeAPI:
    stamps, asks, bids = zip(*ticks)
    return TapeAPI(Security=security, Stamps=np.array([datetime_to_epoch(stamp) for stamp in stamps], dtype=np.int64), Asks=np.array(asks), Bids=np.array(bids), Volumes=np.ones(len(ticks)))

def _labels_(tape: TapeAPI, timeframe: str) -> list:
    return [stamp.replace(tzinfo=None) for stamp in tape.materialize(tape.bars(TimeframeAPI(UID=timeframe)), TimeframeAPI(UID=timeframe))["Timestamp"].to_list()]

def test_a_read_is_exact_and_ordered_on_one_connection_or_many(stored):
    db, security, add = stored
    stamps = [datetime(2024, 1, 3, 10), datetime(2024, 2, 7, 11), datetime(2024, 3, 12, 12, 0, 0, 123000), datetime(2024, 4, 16, 13)]
    for index, stamp in enumerate(reversed(stamps)): add(stamp, 1.10585 + index / 100000, 1.10583)
    single = TapeAPI.read(db, security, datetime(2024, 1, 1), datetime(2024, 5, 1), workers=1)
    many = TapeAPI.read(db, security, datetime(2024, 1, 1), datetime(2024, 5, 1), workers=4)
    assert single.Stamps.tolist() == many.Stamps.tolist() == [datetime_to_epoch(stamp) for stamp in stamps]
    assert many.Asks.tolist() == [1.10588, 1.10587, 1.10586, 1.10585] and many.Bids.tolist() == [1.10583] * 4

def test_a_tick_is_worth_the_sides_that_moved_unless_it_carries_a_size(stored):
    db, security, add = stored
    add(datetime(2024, 6, 3, 9), 1.1000, 1.0998)
    add(datetime(2024, 6, 3, 9, 0, 1), 1.1000, 1.0999)
    add(datetime(2024, 6, 3, 9, 0, 2), 1.1002, 1.1000)
    add(datetime(2024, 6, 3, 9, 0, 3), 1.1003, 1.1000, volume=5.0)
    assert TapeAPI.read(db, security, datetime(2024, 6, 3), datetime(2024, 6, 4)).Volumes.tolist() == [2.0, 1.0, 2.0, 5.0]
    assert TapeAPI.read(db, security, datetime(2024, 6, 3, 9, 0, 1), datetime(2024, 6, 4)).Volumes.tolist() == [1.0, 2.0, 5.0]

def test_a_bar_takes_each_extreme_at_its_first_occurrence_and_its_gap_from_the_last_close():
    tape = _tape_((datetime(2024, 6, 3, 10, 0, 1), 1.1003, 1.1001), (datetime(2024, 6, 3, 10, 10), 1.1010, 1.1005), (datetime(2024, 6, 3, 10, 20), 1.1008, 1.1007), (datetime(2024, 6, 3, 10, 25), 1.1009, 1.1007), (datetime(2024, 6, 3, 10, 30), 1.0995, 1.0990), (datetime(2024, 6, 3, 10, 40), 1.0994, 1.0992), (datetime(2024, 6, 3, 10, 59), 1.1000, 1.0998), (datetime(2024, 6, 3, 11, 5), 1.1001, 1.0999))
    bars = tape.bars(TimeframeAPI(UID="H1"))
    assert bars.select("Gap", "Open", "HighAsk", "HighBid", "LowAsk", "LowBid", "Close").rows() == [(0, 0, 1, 2, 5, 4, 6), (6, 7, 7, 7, 7, 7, 7)]
    assert bars["Volume"].to_list() == [7.0, 1.0]
    frame = tape.materialize(bars, TimeframeAPI(UID="H1"))
    assert set(frame.columns) == set(BarAPI(ClosePoint=PointAPI(TickAPI(), TickAPI()), GapPoint=PointAPI(TickAPI(), TickAPI()), OpenPoint=PointAPI(TickAPI(), TickAPI()), HighPoint=PointAPI(TickAPI(), TickAPI()), LowPoint=PointAPI(TickAPI(), TickAPI())).dict(flatten=True))
    assert (frame["HighPoint.AskTick.Ask"][0], frame["HighPoint.BidTick.Bid"][0], frame["LowPoint.AskTick.Ask"][0], frame["LowPoint.BidTick.Bid"][0]) == (1.1010, 1.1007, 1.0994, 1.0990)
    assert frame["GapPoint.BidTick.Timestamp"][1] == frame["ClosePoint.BidTick.Timestamp"][0]

def test_every_timeframe_counts_from_the_new_york_close_through_daylight_saving():
    winter, summer = datetime(2024, 3, 7, 12, 30), datetime(2024, 3, 12, 12, 30)
    tape = _tape_((winter, 1.1, 1.0), (summer, 1.1, 1.0))
    assert _labels_(tape, "H1") == [datetime(2024, 3, 7, 12), datetime(2024, 3, 12, 12)]
    assert _labels_(tape, "H4") == [datetime(2024, 3, 7, 10), datetime(2024, 3, 12, 9)]
    assert _labels_(tape, "H12") == [datetime(2024, 3, 7, 10), datetime(2024, 3, 12, 9)]
    assert _labels_(tape, "D1") == [datetime(2024, 3, 6, 22), datetime(2024, 3, 11, 21)]
    assert _labels_(tape, "W1") == [datetime(2024, 3, 3, 22), datetime(2024, 3, 10, 21)]
    assert _labels_(_tape_((datetime(2024, 11, 15), 1.1, 1.0)), "MN1") == [datetime(2024, 10, 31, 21)]

def test_a_month_that_opens_on_a_daylight_saving_weekend_keeps_its_own_label():
    assert _labels_(_tape_((datetime(2025, 11, 3, 12), 1.1, 1.0)), "MN1") == [datetime(2025, 10, 31, 21)]

def test_the_floor_of_an_instant_is_its_bar_label():
    tape = _tape_((datetime(2024, 3, 7), 1.1, 1.0))
    assert tape.floor(datetime(2024, 3, 12, 12, 30), TimeframeAPI(UID="D1")) == datetime(2024, 3, 11, 21)
    assert tape.floor(datetime(2024, 3, 12, 12, 30), TimeframeAPI(UID="M15")) == datetime(2024, 3, 12, 12, 30)

def test_rates_read_the_latest_quote_at_or_before_each_tick():
    pair = _tape_((datetime(2024, 1, 1, 0, 0, 1), 2.0, 1.6), (datetime(2024, 1, 1, 0, 0, 3), 4.0, 3.2))
    stamps = np.array([datetime_to_epoch(datetime(2024, 1, 1, 0, 0, second)) for second in (0, 1, 2, 3)], dtype=np.int64)
    asks, bids = TapeAPI.rates(stamps, (pair, False))
    assert np.isnan(asks[0]) and asks[1:].tolist() == [2.0, 2.0, 4.0] and bids[1:].tolist() == [1.6, 1.6, 3.2]
    asks, bids = TapeAPI.rates(stamps, (pair, True))
    assert asks[1:].tolist() == [1 / 1.6, 1 / 1.6, 1 / 3.2] and bids[1:].tolist() == [0.5, 0.5, 0.25]
    assert TapeAPI.rates(stamps, None)[0].tolist() == [1.0] * 4

def _total_(handle: tuple) -> float:
    tape = TapeAPI.attach(handle)
    return float(tape.Stamps.sum() + tape.Asks.sum() + tape.Bids.sum() + tape.Volumes.sum())

def test_a_span_takes_the_bars_it_is_handed_instead_of_building_them(stored):
    db, security, add = stored
    for hour in range(3): add(datetime(2024, 2, 5, 10 + hour), 1.1 + hour / 10000, 1.0998 + hour / 10000)
    tape, bars = TapeAPI.span(db, security, TimeframeAPI(UID="H1"), datetime(2024, 2, 5, 10), datetime(2024, 2, 5, 12))
    handed = bars.head(1)
    again, kept = TapeAPI.span(db, security, TimeframeAPI(UID="H1"), datetime(2024, 2, 5, 10), datetime(2024, 2, 5, 12), shelf=tape, bars=handed)
    assert bars.height == 3 and kept is handed and again.Stamps.tolist() == tape.Stamps.tolist()

def test_a_history_asks_for_the_first_tick_only_when_it_comes_back_short(stored, monkeypatch):
    db, security, add = stored
    for day in range(1, 29): add(datetime(2024, 2, day, 12), 1.1 + day / 10000, 1.0998 + day / 10000)
    firsts, first = [], TapeAPI.first.__func__
    monkeypatch.setattr(TapeAPI, "first", classmethod(lambda cls, db, security: firsts.append(security) or first(cls, db, security)))
    tape, bars = TapeAPI.before(db, security, TimeframeAPI(UID="D1"), datetime(2024, 2, 20), 5)
    assert bars.height == 5 and firsts == [] and tape.Stamps[int(bars["Close"][-1])] == datetime_to_epoch(datetime(2024, 2, 19, 12))
    tape, bars = TapeAPI.before(db, security, TimeframeAPI(UID="D1"), datetime(2024, 2, 20), 40)
    assert bars.height == 19 and firsts == [security]
    tape, bars = TapeAPI.before(db, security, TimeframeAPI(UID="D1"), datetime(2024, 1, 20), 5)
    assert bars.height == 0 and not tape.Stamps.size

def test_a_shared_tape_reads_the_same_in_another_mapping_and_cannot_be_written(stored):
    db, security, add = stored
    for second in range(40): add(datetime(2024, 1, 3, 10) + timedelta(seconds=second), 1.10000 + (second % 7) / 100000, 1.09998 + (second % 5) / 100000)
    private = TapeAPI.read(db, security, datetime(2024, 1, 1), datetime(2024, 1, 5))
    share, attached, cut = ShareAPI([TapeAPI.read(db, security, datetime(2024, 1, 1), datetime(2024, 1, 5), shared=True)]), None, None
    try:
        attached = ShareAPI.attach(share.handles())[security]
        for name in ("Stamps", "Asks", "Bids", "Volumes"):
            assert np.array_equal(getattr(attached, name), getattr(private, name)) and not getattr(attached, name).flags.writeable
        start, stop = datetime(2024, 1, 3, 10, 0, 10), datetime(2024, 1, 3, 10, 0, 30)
        cut, direct = TapeAPI.read(db, security, start, stop, shelf=attached), TapeAPI.read(db, security, start, stop)
        for name in ("Stamps", "Asks", "Bids", "Volumes"):
            assert np.array_equal(getattr(cut, name), getattr(direct, name))
        assert cut.Memory is attached.Memory and cut.Stamps.size == 21
        assert TapeAPI.read(db, security, datetime(2023, 12, 1), stop, shelf=attached).Memory is None
    finally:
        del attached, cut
        gc.collect()
        handle = share.handles()[0]
        share.close()
    with pytest.raises(FileNotFoundError):
        TapeAPI.attach(handle)

def test_closing_a_share_while_a_window_is_still_held_frees_it_with_the_window():
    tape = TapeAPI._allocate_(7, 5, (0, 10), True)
    tape.Stamps[:], tape.Asks[:], tape.Bids[:], tape.Volumes[:] = [1, 2, 3, 4, 5], [1.1] * 5, [1.0] * 5, [2.0] * 5
    share, window = ShareAPI([tape]), tape.cut(2, 4)
    handle = share.handles()[0]
    del tape
    share.close()
    assert window.Stamps.tolist() == [2, 3, 4] and TapeAPI.attach(handle).Stamps.tolist() == [1, 2, 3, 4, 5]
    del window
    gc.collect()
    with pytest.raises(FileNotFoundError):
        TapeAPI.attach(handle)

def test_a_worker_process_reads_the_tape_the_parent_shared():
    tape = TapeAPI._allocate_(7, 5, (0, 10), True)
    tape.Stamps[:], tape.Asks[:], tape.Bids[:], tape.Volumes[:] = [1, 2, 3, 4, 5], [1.1] * 5, [1.0] * 5, [2.0] * 5
    share = ShareAPI([tape])
    handle = share.handles()[0]
    del tape
    try:
        with ProcessPoolExecutor(max_workers=1) as pool:
            assert pool.submit(_total_, handle).result() == pytest.approx(15 + 5.5 + 5.0 + 10.0)
    finally:
        share.close()

def test_bar_starts_do_not_depend_on_how_the_tape_is_chunked(monkeypatch):
    stamps = np.arange(datetime_to_epoch(datetime(2024, 3, 8)), datetime_to_epoch(datetime(2024, 3, 13)), 7 * 60_000, dtype=np.int64)
    prices = 1.1 + np.sin(np.arange(stamps.size)) / 1000
    tape = TapeAPI(Security=1, Stamps=stamps, Asks=prices + 0.00002, Bids=prices, Volumes=np.ones(stamps.size))
    expected = {uid: tape.bars(TimeframeAPI(UID=uid)) for uid in ("M5", "H1", "H4", "D1")}
    monkeypatch.setattr(TapeAPI, "_chunks_", staticmethod(lambda low, high, size=4_000_000: [(start, min(start + 7, high)) for start in range(low, high, 7)]))
    for uid, frame in expected.items():
        assert tape.bars(TimeframeAPI(UID=uid)).equals(frame), uid