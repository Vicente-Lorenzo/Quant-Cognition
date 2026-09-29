import pytest

from datetime import datetime, timedelta

from Library.Database.Dataframe import pl
from Library.Market.Market import MarketAPI
from Library.Market.Point import PointAPI
from Library.Market.Price import PriceMode
from Library.Market.Tick import TickAPI

def test_pull_ticks_reads_the_stored_window(stored):
    db, security, add = stored
    base = datetime(2023, 1, 2, 10)
    for second in range(100): add(base + timedelta(seconds=second), 1.1000 + second / 10000, 1.0999 + second / 10000)
    pulled = MarketAPI.pull_ticks(db, security, base, base + timedelta(seconds=49))
    assert pulled.height == 50 and pulled.columns == ["Timestamp", "Ask", "Bid", "Volume"]
    assert pulled["Ask"].max() == pytest.approx(1.1049) and pulled["Timestamp"][0] == base

def test_pull_bars_derives_every_bar_of_a_range(stored):
    db, security, add = stored
    base = datetime(2023, 1, 2, 10)
    for minute in range(180): add(base + timedelta(minutes=minute, seconds=5), 1.1000 + minute / 100000, 1.0998 + minute / 100000)
    bars = MarketAPI.pull_bars(db, security, "H1", start=base, stop=base + timedelta(hours=2))
    assert bars["Timestamp"].to_list() == [base, base + timedelta(hours=1), base + timedelta(hours=2)]
    assert bars["ClosePoint.BidTick.Bid"].to_list() == pytest.approx([1.10039, 1.10099, 1.10159])
    assert bars["Volume"].to_list() == [120.0, 120.0, 120.0]

def test_pull_bars_with_a_limit_returns_the_last_complete_bars_before_the_stop(stored):
    db, security, add = stored
    base = datetime(2023, 1, 2, 10)
    for minute in range(300): add(base + timedelta(minutes=minute, seconds=5), 1.1000, 1.0998)
    bars = MarketAPI.pull_bars(db, security, "H1", stop=base + timedelta(hours=4), limit=2)
    assert bars["Timestamp"].to_list() == [base + timedelta(hours=2), base + timedelta(hours=3)]

def test_pull_bars_of_an_empty_window_is_empty(stored):
    db, security, _ = stored
    assert MarketAPI.pull_bars(db, security, "H1", start=datetime(2023, 1, 2), stop=datetime(2023, 1, 3)).is_empty()
    assert MarketAPI.pull_bars(db, security, "H1", stop=datetime(2023, 1, 3), limit=5).is_empty()

def test_series_tick_initialization():
    market = MarketAPI()
    data = pl.DataFrame({
        "Timestamp": [datetime(2020, 1, 1), datetime(2020, 1, 2)],
        "Security": [1, 1],
        "Ask": [1.1, 1.2],
        "Bid": [1.0, 1.1],
        "Volume": [100.0, 200.0]
    })
    market.init_data(data)
    assert market.Ticks.Bid.last() == 1.1
    assert market.Ticks.Ask.last() == 1.2
    tick = market.Ticks.last(dataframe=False)
    assert isinstance(tick, TickAPI)
    assert tick.Bid.Price == 1.1
    assert tick.Ask.Price == 1.2
    market.update_offset(2)
    assert market.Ticks.Bid.last() == 1.0

def test_series_bar_initialization():
    market = MarketAPI()
    data = pl.DataFrame({
        "Timestamp": [datetime(2020, 1, 1)],
        "Security": [1],
        "Timeframe": ["M1"],
        "ClosePoint.AskTick.Ask": [1.2],
        "ClosePoint.BidTick.Bid": [1.1],
        "OpenPoint.AskTick.Ask": [1.1],
        "OpenPoint.BidTick.Bid": [1.0],
        "Volume": [1000.0]
    })
    market.init_data(data)
    assert market.ClosePoints.Bid.last() == 1.1
    assert market.OpenPoints.Ask.last() == 1.1
    assert market.ClosePoints.Bid.over(market.OpenPoints.Bid) == True

def test_a_point_series_returns_points():
    market = MarketAPI()
    market.init_data(pl.DataFrame({"Timestamp": [datetime(2020, 1, 1)], "Timeframe": ["M1"], "HighPoint.AskTick.Ask": [1.3], "HighPoint.AskTick.Bid": [1.2], "HighPoint.BidTick.Ask": [1.25], "HighPoint.BidTick.Bid": [1.24]}))
    point = market.HighPoints.last()
    assert isinstance(point, PointAPI) and (point.Ask.Price, point.Bid.Price) == (1.3, 1.24)

def test_series_group_crossover():
    market = MarketAPI()
    data = pl.DataFrame({
        "Timestamp": [datetime(2020, 1, 1), datetime(2020, 1, 2)],
        "Security": [1, 1],
        "Timeframe": ["M1", "M1"],
        "ClosePoint.AskTick.Ask": [1.0, 1.3],
        "ClosePoint.BidTick.Bid": [0.9, 1.2],
        "OpenPoint.AskTick.Ask": [1.1, 1.1],
        "OpenPoint.BidTick.Bid": [1.0, 1.0],
        "Volume": [1000.0, 1000.0]
    })
    market.init_data(data)
    df_res = market.ClosePoints.crossover(market.OpenPoints, dataframe=True)
    assert df_res["ClosePoint.AskTick.Ask"][0] == True
    assert df_res["ClosePoint.BidTick.Bid"][0] == True

def test_market_update_data():
    market = MarketAPI()
    t1 = TickAPI(Timestamp=datetime(2020, 1, 1), Security=1, Ask=1.1, Bid=1.0, Volume=100.0)
    market.init_data(pl.DataFrame([t1.dict()], strict=False))
    market.update_data(TickAPI(Timestamp=datetime(2020, 1, 2), Security=1, Ask=1.2, Bid=1.1, Volume=200.0))
    assert market.Ticks.Ask.last() == 1.2

def test_head_and_tail_without_a_count_return_every_row():
    market = MarketAPI()
    market.init_data(pl.DataFrame({"Timestamp": [datetime(2020, 1, 1), datetime(2020, 1, 2)], "Bid": [1.0, 1.1]}))
    assert market.head().height == 2 and market.tail().height == 2
    assert market.head(1)["Bid"].to_list() == [1.0] and market.tail(1)["Bid"].to_list() == [1.1]
    assert market.Ticks.Bid.tail().to_list() == [1.0, 1.1]

def _points_() -> pl.DataFrame:
    return pl.DataFrame({
        "Timestamp": [datetime(2020, 1, 1), datetime(2020, 1, 2)],
        "Timeframe": ["M1", "M1"],
        "HighPoint.AskTick.Ask": [1.30, 1.40], "HighPoint.AskTick.Bid": [1.20, 1.30],
        "HighPoint.BidTick.Ask": [1.27, 1.37], "HighPoint.BidTick.Bid": [1.26, 1.36],
        "HighPoint.MidTick.Ask": [1.29, 1.39], "HighPoint.MidTick.Bid": [1.25, 1.35],
        "ClosePoint.AskTick.Ask": [1.21, 1.31], "ClosePoint.BidTick.Bid": [1.19, 1.29],
        "ClosePoint.MidTick.Ask": [1.21, 1.31], "ClosePoint.MidTick.Bid": [1.19, 1.29]
    })

def test_a_market_prices_at_the_bid_unless_told_otherwise():
    market = MarketAPI()
    market.init_data(_points_())
    assert market.HighPoints.Price.tail().to_list() == [1.26, 1.36] and market.ClosePoints.Price.last() == 1.29

def test_a_market_in_ask_mode_prices_every_point_at_its_ask_tick():
    market = MarketAPI(mode=PriceMode.Ask)
    market.init_data(_points_())
    assert market.HighPoints.Price.tail().to_list() == [1.30, 1.40] and market.ClosePoints.Price.last(1) == 1.21

def test_a_market_in_mid_mode_prices_every_point_at_the_mid_of_its_mid_tick():
    market = MarketAPI(mode=PriceMode.Mid)
    market.init_data(_points_())
    assert market.HighPoints.Price.tail().to_list() == [(1.29 + 1.25) / 2, (1.39 + 1.35) / 2]
    assert market.HighPoints.Price.last() == (1.39 + 1.35) / 2 and market.HighPoints.Price.last(1) == (1.29 + 1.25) / 2 and market.HighPoints.Price.last(2) is None
    assert market.HighPoints.Price.tail(1).to_list() == [(1.39 + 1.35) / 2] and market.HighPoints.Price.dataframe().name == "HighPoint.MidTick.Mid"
    assert market.HighPoints.Price.over(market.ClosePoints.Price) and market.ClosePoints.Price.under(1.35)
    market.update_offset(2)
    assert market.HighPoints.Price.last() == (1.29 + 1.25) / 2
    point = market.HighPoints.last()
    assert (point.Ask.Price, point.Bid.Price, point.Mid.Price) == (1.30, 1.26, (1.29 + 1.25) / 2)

def test_a_tick_series_carries_its_mid():
    market = MarketAPI(mode=PriceMode.Mid)
    market.init_data(pl.DataFrame({"Timestamp": [datetime(2020, 1, 1), datetime(2020, 1, 2)], "Ask": [1.1, 1.3], "Bid": [1.0, 1.1]}))
    assert market.Ticks.Price is market.Ticks.Mid and market.Ticks.Mid.last() == (1.3 + 1.1) / 2 and market.Ticks.Mid.tail().to_list() == [(1.1 + 1.0) / 2, (1.3 + 1.1) / 2]