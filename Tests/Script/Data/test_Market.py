import pytest
from datetime import datetime, timedelta

from Library.Database.Dataframe import pl
from Script.Data.Market import MarketWorkerAPI
from Library.Market.Download import DownloadAPI, DownloadStatus
from Library.Market.Tape import TapeAPI
from Library.Market.Tick import TickAPI
from Library.Utility.Datetime import epoch_to_datetime, utc_now

DAY = datetime(2026, 3, 10)

class FeedAPI:

    def __init__(self, asks: list, bids: list, failing: bool = False) -> None:
        self._sides_ = {"Ask": asks, "Bid": bids}
        self._failing_ = failing

    def ticks(self, symbol: int, start: datetime, stop: datetime, quote: str, legacy: bool = False) -> pl.DataFrame:
        if self._failing_: raise ConnectionError("Feed unreachable")
        rows = [{"Timestamp": stamp, quote: price} for stamp, price in self._sides_[quote] if start <= stamp <= stop]
        return pl.DataFrame(rows, schema={"Timestamp": pl.Datetime("ms"), quote: pl.Float64})

class ClientAPI:

    def __init__(self, feed: FeedAPI) -> None:
        self.market = feed

def worker(security: int, horizon: datetime = DAY) -> MarketWorkerAPI:
    service = MarketWorkerAPI(security=security, horizon=horizon, database="Tests", vault="Tests")
    service._symbol_, service._label_ = 1, "EURUSD"
    return service

def at(seconds: float, day: datetime = DAY) -> datetime:
    return day + timedelta(hours=9, seconds=seconds)

def feed(day: datetime = DAY) -> FeedAPI:
    asks = [(at(0, day), 1.10002), (at(1, day), 1.10004), (at(1, day), 1.10006), (at(3, day), 1.10010)]
    bids = [(at(0, day), 1.10000), (at(2, day), 1.10001), (at(3, day), 1.10005)]
    return FeedAPI(asks, bids)

def test_the_last_state_of_a_millisecond_wins_and_a_missing_side_carries_forward():
    asks = pl.DataFrame({"Timestamp": [at(0), at(1), at(1)], "Ask": [1.1, 1.2, 1.3]}, schema={"Timestamp": pl.Datetime("ms"), "Ask": pl.Float64})
    bids = pl.DataFrame({"Timestamp": [at(1), at(2)], "Bid": [1.0, 1.05]}, schema={"Timestamp": pl.Datetime("ms"), "Bid": pl.Float64})
    merged = TapeAPI.merge(asks, bids)
    assert merged.rows() == [(int(at(1).timestamp() * 1000), 130000, 100000), (int(at(2).timestamp() * 1000), 130000, 105000)]
    carried = TapeAPI.merge(asks, bids, carry=(90000, 95000))
    assert carried.rows()[0] == (int(at(0).timestamp() * 1000), 110000, 95000)

def test_a_day_is_written_once_recorded_complete_and_rewritten_in_place(tape):
    db, security = tape
    service = worker(security)
    assert service._day_(ClientAPI(feed()), db, DAY) is DownloadStatus.Complete
    read = TapeAPI.read(db, security, DAY, DAY + timedelta(days=1))
    assert [round(value * 100_000) for value in read.Asks] == [110002, 110006, 110006, 110010]
    assert [round(value * 100_000) for value in read.Bids] == [110000, 110000, 110001, 110005]
    assert DownloadAPI.settled(db, security) == {DAY: DownloadStatus.Complete.name}
    assert service._day_(ClientAPI(feed()), db, DAY) is DownloadStatus.Complete
    assert TapeAPI.read(db, security, DAY, DAY + timedelta(days=1)).Stamps.size == 4
    assert DownloadAPI.through(db, security) == DAY + timedelta(days=1)

def test_a_day_is_asked_up_to_the_next_midnight_since_the_server_excludes_its_end(tape):
    db, security = tape
    asks, bids = [(DAY + timedelta(days=1) - timedelta(milliseconds=1), 1.1)], [(DAY + timedelta(days=1) - timedelta(milliseconds=1), 1.0)]
    windows = []
    class LastAPI(FeedAPI):
        def ticks(self, symbol, start, stop, quote, legacy=False):
            windows.append((start, stop))
            return super().ticks(symbol, start, stop - timedelta(milliseconds=1), quote, legacy)
    assert worker(security)._day_(ClientAPI(LastAPI(asks, bids)), db, DAY) is DownloadStatus.Complete
    assert windows == [(DAY, DAY + timedelta(days=1))] * 2
    assert TapeAPI.read(db, security, DAY, DAY + timedelta(days=1)).Stamps.size == 1

def test_a_day_without_ticks_is_empty_and_a_failed_fetch_is_recorded_as_failed(tape):
    db, security = tape
    service = worker(security)
    assert service._day_(ClientAPI(FeedAPI([], [])), db, DAY) is DownloadStatus.Empty
    following = DAY + timedelta(days=1)
    assert service._day_(ClientAPI(FeedAPI([], [], failing=True)), db, following) is DownloadStatus.Failed
    assert DownloadAPI.settled(db, security) == {DAY: DownloadStatus.Empty.name, following: DownloadStatus.Failed.name}
    assert DownloadAPI.through(db, security) == following

def test_only_unsettled_days_are_missing_and_a_failed_day_is_retried(tape):
    db, security = tape
    service = worker(security, horizon=DAY)
    service._day_(ClientAPI(feed()), db, DAY)
    service._day_(ClientAPI(FeedAPI([], [], failing=True)), db, DAY + timedelta(days=1))
    assert service._missing_(db, DAY + timedelta(days=3)) == [DAY + timedelta(days=1), DAY + timedelta(days=2)]

def test_coverage_needs_every_day_of_the_window_settled_through_its_end(tape):
    db, security = tape
    service = worker(security)
    service._day_(ClientAPI(feed()), db, DAY)
    assert DownloadAPI.covers(db, security, at(0), at(3))
    assert not DownloadAPI.covers(db, security, at(0), at(3, DAY + timedelta(days=1)))
    service._day_(ClientAPI(FeedAPI([], [], failing=True)), db, DAY + timedelta(days=1))
    assert not DownloadAPI.covers(db, security, at(0), at(3, DAY + timedelta(days=1)))

def test_a_live_poll_extends_the_tape_and_records_what_it_covers(tape):
    db, security = tape
    service = worker(security)
    today = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    recent = utc_now() - timedelta(seconds=5)
    live = FeedAPI([(recent, 1.2), (recent + timedelta(milliseconds=1), 1.3)], [(recent, 1.1)])
    frontier = service._poll_window_(ClientAPI(live), db, today, today)
    assert frontier == recent.replace(microsecond=(recent.microsecond // 1000) * 1000) + timedelta(milliseconds=1)
    assert TapeAPI.read(db, security, today, utc_now()).Stamps.size == 2
    record = db.first(schema=DownloadAPI.Schema, table=DownloadAPI.Table, condition='"Security" = :security: AND "Timestamp" = :day:', parameters={"security": security, "day": today})
    assert record["Status"] == DownloadStatus.Live.name and record["Through"] <= utc_now() - timedelta(seconds=service._overlap_.total_seconds() - 1)

def test_the_summary_and_the_month_strip_count_each_status(tape):
    db, security = tape
    service = worker(security)
    service._day_(ClientAPI(feed()), db, DAY)
    service._day_(ClientAPI(FeedAPI([], [])), db, DAY + timedelta(days=1))
    service._day_(ClientAPI(FeedAPI([], [], failing=True)), db, DAY + timedelta(days=2))
    summary = {row["Security"]: row for row in DownloadAPI.summary(db).to_dicts()}[security]
    assert (summary["Complete"], summary["Empty"], summary["Failed"], summary["Ticks"]) == (1, 1, 1, 4)
    assert summary["First"] == DAY and summary["Last"] == DAY + timedelta(days=2) and summary["Through"] == DAY + timedelta(days=2)
    months = [row for row in DownloadAPI.months(db).to_dicts() if row["Security"] == security]
    assert [(row["Month"], row["Complete"], row["Empty"], row["Failed"]) for row in months] == [(datetime(2026, 3, 1), 1, 1, 1)]

def test_the_previous_state_is_found_near_first_and_across_a_weekend_after(tape):
    db, security = tape
    worker(security)._day_(ClientAPI(feed()), db, DAY)
    assert TapeAPI.previous(db, security, at(0)) is None
    assert TapeAPI.previous(db, security, at(1800)) == (110010, 110005)
    assert TapeAPI.previous(db, security, DAY + timedelta(days=3)) == (110010, 110005)

def test_a_day_across_a_chunk_boundary_is_replaced_on_both_sides(tape):
    db, security = tape
    boundary = -(-TickAPI.encode(security, DAY) // TapeAPI._interval_()) * TapeAPI._interval_()
    moment = epoch_to_datetime(boundary - (security << TickAPI.bits()))
    day = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    around = [moment - timedelta(seconds=1), moment + timedelta(seconds=1)] if moment - timedelta(seconds=1) >= day and moment + timedelta(seconds=1) < day + timedelta(days=1) else pytest.skip("The chunk boundary falls on midnight")
    worker(security)._day_(ClientAPI(FeedAPI([(stamp, 1.2) for stamp in around], [(stamp, 1.1) for stamp in around])), db, day)
    assert len(TapeAPI._covering_(db, TickAPI.encode(security, day), TickAPI.encode(security, day + timedelta(days=1)) - 1)) == 2
    worker(security)._day_(ClientAPI(FeedAPI([(around[1], 1.3)], [(around[1], 1.0)])), db, day)
    read = TapeAPI.read(db, security, day, day + timedelta(days=1))
    assert read.Stamps.size == 1 and round(float(read.Asks[0]) * 100_000) == 130_000

def test_a_rollover_rewrites_the_finished_day_and_compresses_what_came_before(tape, monkeypatch):
    db, security = tape
    service, compressed = worker(security), []
    monkeypatch.setattr(TapeAPI, "compress", classmethod(lambda cls, db, security, before: compressed.append((security, before)) or 0))
    service._roll_(ClientAPI(feed()), db, DAY, DAY + timedelta(days=1))
    assert DownloadAPI.settled(db, security) == {DAY: DownloadStatus.Complete.name} and compressed == [(security, DAY + timedelta(days=1))]
    monkeypatch.setattr(TapeAPI, "compress", classmethod(lambda cls, db, security, before: 1 / 0))
    service._roll_(ClientAPI(feed()), db, DAY, DAY + timedelta(days=1))

def test_a_day_is_replaced_whole_or_not_at_all(tape, monkeypatch):
    db, security = tape
    worker(security)._day_(ClientAPI(feed()), db, DAY)
    frame = TapeAPI.merge(*[pl.DataFrame({"Timestamp": [at(5)], side: [1.2]}, schema={"Timestamp": pl.Datetime("ms"), side: pl.Float64}) for side in ("Ask", "Bid")])
    def interrupted(self, **kwargs): raise ConnectionError("Copy interrupted")
    monkeypatch.setattr(type(db), "copy", interrupted)
    with pytest.raises(ConnectionError): TapeAPI.write(db, security, frame, DAY, DAY + timedelta(days=1), "Tester")
    assert TapeAPI.read(db, security, DAY, DAY + timedelta(days=1)).Stamps.size == 4

def test_a_compressed_month_reads_the_same_and_still_takes_a_rewrite(tape):
    db, security = tape
    worker(security)._day_(ClientAPI(feed()), db, DAY)
    before = TapeAPI.read(db, security, DAY, DAY + timedelta(days=1))
    assert TapeAPI.compress(db, security, datetime(2026, 6, 1)) >= 1
    after = TapeAPI.read(db, security, DAY, DAY + timedelta(days=1))
    assert (after.Stamps == before.Stamps).all() and (after.Asks == before.Asks).all() and (after.Bids == before.Bids).all()
    assert TapeAPI.compress(db, security, datetime(2026, 6, 1)) == 0
    assert worker(security)._day_(ClientAPI(feed()), db, DAY) is DownloadStatus.Complete
    assert TapeAPI.read(db, security, DAY, DAY + timedelta(days=1)).Stamps.size == 4

def test_a_conversion_takes_the_direct_pair_either_way_round_and_never_a_third_currency(tape, universe):
    db, _ = tape
    security = universe["security"]
    assert TapeAPI.route(db, security, "USD", "USD") is None
    assert TapeAPI.route(db, security, "EUR", "USD") == (security.UID, False, "EURUSD")
    assert TapeAPI.route(db, security, "USD", "EUR") == (security.UID, True, "EURUSD")
    with pytest.raises(ValueError, match="no direct pair"): TapeAPI.route(db, security, "JPY", "CHF")

def test_a_day_written_after_its_successor_rewrites_the_successor_with_the_true_carry(tape, monkeypatch):
    db, security = tape
    following = DAY + timedelta(days=1)
    asks = [(at(0), 1.10002), (following + timedelta(hours=8), 1.10020), (following + timedelta(hours=9), 1.10030)]
    bids = [(at(0), 1.10000), (following + timedelta(hours=9), 1.10025)]
    service = worker(security)
    assert service._day_(ClientAPI(FeedAPI(asks, bids)), db, following) is DownloadStatus.Complete
    assert TapeAPI.read(db, security, following, following + timedelta(days=1)).Stamps.size == 1
    monkeypatch.setattr("Script.Data.Market.utc_now", lambda: DAY + timedelta(days=3, hours=1))
    assert service._backfill_(ClientAPI(FeedAPI(asks, bids)), db) == 0
    read = TapeAPI.read(db, security, following, following + timedelta(days=1))
    assert [(round(float(ask) * 100_000), round(float(bid) * 100_000)) for ask, bid in zip(read.Asks, read.Bids)] == [(110020, 110000), (110030, 110025)]
    assert DownloadAPI.settled(db, security) == {DAY: DownloadStatus.Complete.name, following: DownloadStatus.Complete.name, DAY + timedelta(days=2): DownloadStatus.Empty.name}

def test_the_successor_skips_empty_days_and_stops_at_an_unsettled_one(tape):
    db, security = tape
    service = worker(security)
    service._day_(ClientAPI(feed()), db, DAY)
    service._day_(ClientAPI(FeedAPI([], [])), db, DAY + timedelta(days=1))
    service._day_(ClientAPI(feed(DAY + timedelta(days=2))), db, DAY + timedelta(days=2))
    assert DownloadAPI.successor(db, security, DAY, DAY + timedelta(days=5)) == DAY + timedelta(days=2)
    assert DownloadAPI.successor(db, security, DAY, DAY + timedelta(days=2)) is None
    assert DownloadAPI.successor(db, security, DAY + timedelta(days=2), DAY + timedelta(days=5)) is None