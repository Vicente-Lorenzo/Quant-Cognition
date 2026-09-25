from datetime import datetime
from Library.Market.Bar import BarAPI
from Library.Market.Point import PointAPI
from Library.Market.Tick import TickAPI

AT = datetime(2023, 1, 1, 12)

def _tick_(minute: int, ask: float, bid: float) -> TickAPI:
    return TickAPI(5, AT.replace(minute=minute), Ask=ask, Bid=bid, Volume=1.0)

def _bar_() -> BarAPI:
    gap, opened, closed = _tick_(0, 1.0499, 1.0497), _tick_(1, 1.0500, 1.0498), _tick_(59, 1.0505, 1.0503)
    high = PointAPI(AskTick=_tick_(10, 1.0512, 1.0506), BidTick=_tick_(20, 1.0511, 1.0508))
    low = PointAPI(AskTick=_tick_(30, 1.0489, 1.0486), BidTick=_tick_(40, 1.0490, 1.0485))
    return BarAPI(5, "H1", AT, PointAPI(gap, gap), PointAPI(opened, opened), high, low, PointAPI(closed, closed), 6.0)

def test_a_point_reads_its_ask_from_the_ask_tick_and_its_bid_from_the_bid_tick():
    bar = _bar_()
    assert (bar.HighPoint.Ask.Price, bar.HighPoint.Bid.Price) == (1.0512, 1.0508)
    assert (bar.LowPoint.Ask.Price, bar.LowPoint.Bid.Price) == (1.0489, 1.0485)
    assert bar.ClosePoint.AskTick is bar.ClosePoint.BidTick

def test_every_field_is_reachable_from_the_bar():
    bar = _bar_()
    assert bar.HighPoint.AskTick.Timestamp.DateTime == AT.replace(minute=10)
    assert (bar.HighPoint.AskTick.Ask.Price, bar.HighPoint.AskTick.Bid.Price, bar.HighPoint.AskTick.Volume) == (1.0512, 1.0506, 1.0)
    assert (bar.Timestamp.DateTime, bar.Volume, bar.Timeframe.UID, bar.Security.UID) == (AT, 6.0, "H1", 5)

def test_flattening_names_every_tick_of_every_point():
    row = _bar_().dict(flatten=True)
    assert (row["HighPoint.AskTick.Ask"], row["HighPoint.BidTick.Bid"]) == (1.0512, 1.0508)
    assert row["ClosePoint.AskTick.Timestamp"] == row["ClosePoint.BidTick.Timestamp"] == AT.replace(minute=59)
    assert str(BarAPI.OID.HighPoint.AskTick.Ask) == "HighPoint.AskTick.Ask"

def test_a_bar_has_no_identity_of_its_own():
    assert "UID" not in _bar_().dict(flatten=True)