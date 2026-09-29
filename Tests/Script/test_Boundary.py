import pytest
from datetime import datetime, timedelta

from Library.Database.Dataframe import pl
from Library.Database.Query import QueryAPI
from Library.Market.Download import DownloadAPI, DownloadStatus
from Library.Market.Tape import TapeAPI
from Library.Market.Tick import TickAPI
from Library.Utility.Datetime import datetime_to_epoch
from Script.Setup import Boundary

DAY = datetime(2026, 3, 10)
LAST = DAY + timedelta(days=1) - timedelta(milliseconds=1)

FOLLOWING = DAY + timedelta(days=1)
SIDES = {"Ask": [(FOLLOWING + timedelta(hours=1), 1.1003)], "Bid": [(LAST, 1.1), (FOLLOWING + timedelta(hours=2), 1.1001)]}

class FeedAPI:

    def ticks(self, symbol: int, start: datetime, stop: datetime, quote: str, legacy: bool = False) -> pl.DataFrame:
        return pl.DataFrame([{"Timestamp": stamp, quote: price} for stamp, price in SIDES[quote] if start <= stamp < stop], schema={"Timestamp": pl.Datetime("ms"), quote: pl.Float64})

class ClientAPI:

    market = FeedAPI()

@pytest.fixture
def tape(db, universe):
    try: TapeAPI.create(db)
    except Exception as error: pytest.skip(f"TimescaleDB unavailable in the Tests database · {error}")
    DownloadAPI(db=db, migrate=True, autoload=False)
    security = universe["security"].UID
    def clear() -> None:
        db.executeone(QueryAPI('DELETE FROM "Market"."Tick" WHERE "UID" BETWEEN :low: AND :high:'), low=security << TickAPI.bits(), high=((security + 1) << TickAPI.bits()) - 1)
        db.remove(schema=DownloadAPI.Schema, table=DownloadAPI.Table, condition='"Security" = :security:', parameters={"security": security})
    clear()
    yield db, security
    clear()

def _stored_(db, security: int, day: datetime, ask: int, bid: int) -> None:
    frame = pl.DataFrame({"Stamp": [datetime_to_epoch(day + timedelta(hours=23))], "Ask": [ask], "Bid": [bid]}, schema={"Stamp": pl.Int64, "Ask": pl.Int64, "Bid": pl.Int64})
    TapeAPI.write(db, security, frame, day, day + timedelta(days=1), "Tester")
    DownloadAPI(Security=security, Timestamp=day, Ticks=1, Status=DownloadStatus.Complete, Through=day + timedelta(days=1), db=db).save(by="Tester")

def _sides_(db, security: int, day: datetime) -> list[tuple[int, int]]:
    tape = TapeAPI.read(db, security, day, day + timedelta(days=1))
    return [(round(float(ask) * 100_000), round(float(bid) * 100_000)) for ask, bid in zip(tape.Asks, tape.Bids)]

def test_the_last_millisecond_of_a_day_is_restored_once_with_the_other_side_carried(tape):
    db, security = tape
    _stored_(db, security, DAY, 110_010, 110_005)
    assert Boundary._days_(db, DAY + timedelta(days=2)) == [(security, 1, DAY)]
    assert Boundary._repair_(ClientAPI(), db, security, 1, DAY, DAY + timedelta(days=2)) == 1
    assert Boundary._repair_(ClientAPI(), db, security, 1, DAY, DAY + timedelta(days=2)) == 0
    assert _sides_(db, security, DAY) == [(110_010, 110_005), (110_010, 110_000)]

def test_a_restored_tick_is_carried_into_the_next_stored_day(tape):
    db, security = tape
    _stored_(db, security, DAY, 110_010, 110_005)
    _stored_(db, security, FOLLOWING, 110_040, 110_035)
    assert Boundary._repair_(ClientAPI(), db, security, 1, DAY, FOLLOWING + timedelta(days=1)) == 1
    assert _sides_(db, security, FOLLOWING) == [(110_030, 110_000), (110_030, 110_010)]

def test_a_day_written_before_its_predecessor_is_found(tape):
    db, security = tape
    _stored_(db, security, FOLLOWING, 110_040, 110_035)
    _stored_(db, security, DAY, 110_010, 110_005)
    assert Boundary._disordered_(db, FOLLOWING + timedelta(days=1)) == [(security, 1, FOLLOWING)]
    assert Boundary._disordered_(db, FOLLOWING) == []