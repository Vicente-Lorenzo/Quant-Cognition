import random
import pytest
from datetime import datetime

from Library.System.Backtesting import BacktestingAPI
from Library.Market.Price import Direction
from Library.Protocol.Update import UpdateID
from Library.Universe.Contract import CommissionType, CommissionMode, SpreadType, SwapType, SwapMode
from Library.Utility.Datetime import Weekday

class _Contract_:
    PointSize = 0.00001
    PipSize = 0.0001
    LotSize = 100000
    Commission = 45.0
    CommissionMode = CommissionMode.BaseAssetPerMillionVolume
    SwapLong = -2.445
    SwapShort = -0.105
    SwapMode = SwapMode.Pips
    SwapPeriod = 24
    SwapWinterTime = 22
    SwapSummerTime = 21
    SwapExtraDay = Weekday.Wednesday

class _Price_:
    def __init__(self, price):
        self.Price = price

class _Position_:
    def __init__(self, direction, stop_loss=None, take_profit=None):
        self.Direction = direction
        self.StopLossPrice = _Price_(stop_loss) if stop_loss is not None else None
        self.TakeProfitPrice = _Price_(take_profit) if take_profit is not None else None

def _engine_(spread=(SpreadType.Accurate, None), commission=(CommissionType.Accurate, None), swap=(SwapType.Accurate, None, None)):
    engine = object.__new__(BacktestingAPI)
    engine._contract_ = _Contract_()
    engine._rng_ = random.Random(1)
    engine._spread_type_, engine._spread_value_ = spread
    engine._commission_type_, engine._commission_value_ = commission
    engine._swap_type_, engine._swap_long_, engine._swap_short_ = swap
    engine._account_asset_, engine._base_asset_, engine._quote_asset_ = "EUR", "EUR", "USD"
    engine._digits_ = 5
    return engine

def test_spread_points():
    engine = _engine_(spread=(SpreadType.Points, 2.0))
    assert engine._spread_value_amount_(1.10005, 1.10000) == pytest.approx(2.0 * 0.00001)
    assert engine._effective_ask_bid_(1.10005, 1.10000) == pytest.approx((1.10000 + 2.0 * 0.00001, 1.10000))

def test_spread_percentage():
    engine = _engine_(spread=(SpreadType.Percentage, 0.01))
    assert engine._spread_value_amount_(1.2, 1.1) == pytest.approx(0.01 / 100.0 * 1.1)

def test_spread_accurate_and_approximate():
    for kind in (SpreadType.Accurate, SpreadType.Approximate):
        engine = _engine_(spread=(kind, None))
        assert engine._spread_value_amount_(1.10005, 1.10000) == pytest.approx(1.10005 - 1.10000)
        assert engine._effective_ask_bid_(1.10005, 1.10000) == (1.10005, 1.10000)

def test_spread_random_bounded_and_reproducible():
    engine = _engine_(spread=(SpreadType.Random, 3.0))
    values = [engine._spread_value_amount_(1.1, 1.1) for _ in range(100)]
    assert all(0.0 <= v <= 3.0 * 0.00001 for v in values)
    assert _engine_(spread=(SpreadType.Random, 3.0))._spread_value_amount_(1.1, 1.1) == values[0]

def test_commission_points():
    engine = _engine_(commission=(CommissionType.Points, 1.0))
    assert engine._commission_(10000.0, 1.1) == pytest.approx(10000.0 * (-1.0 * 0.00001) * (1.0 / 1.1))

def test_commission_percentage():
    engine = _engine_(commission=(CommissionType.Percentage, 1.0))
    assert engine._commission_(10000.0, 1.1) == pytest.approx(-1.0 / 100.0 * 10000.0)

def test_commission_amount():
    engine = _engine_(commission=(CommissionType.Amount, 5.0))
    assert engine._commission_(10000.0, 1.1) == pytest.approx(-5.0)

def test_commission_accurate_base_per_million():
    engine = _engine_()
    assert engine._commission_(10000.0, 1.1) == pytest.approx(10000.0 * (-45.0 / 1_000_000) * 1.0)

def test_commission_accurate_per_lot():
    engine = _engine_()
    engine._contract_.CommissionMode = CommissionMode.BaseAssetPerOneLot
    assert engine._commission_(100000.0, 1.1) == pytest.approx(1.0 * -45.0 * 1.0)

def test_overnights_zero_when_not_held():
    engine = _engine_()
    assert engine._overnights_(datetime(2023, 6, 1, 12), datetime(2023, 6, 1, 12)) == 0

def test_overnights_positive_for_multiday():
    engine = _engine_()
    assert engine._overnights_(datetime(2023, 6, 5, 12), datetime(2023, 6, 9, 12)) > 0

def test_swap_amount():
    engine = _engine_(swap=(SwapType.Amount, -2.0, -3.0))
    assert engine._swap_(Direction.Buy, 10000.0, 1.1, datetime(2023, 6, 5, 12), datetime(2023, 6, 9, 12)) == pytest.approx(-2.0)
    assert engine._swap_(Direction.Sell, 10000.0, 1.1, datetime(2023, 6, 5, 12), datetime(2023, 6, 9, 12)) == pytest.approx(-3.0)

def test_swap_zero_intraday():
    engine = _engine_(swap=(SwapType.Amount, -2.0, -3.0))
    assert engine._swap_(Direction.Buy, 10000.0, 1.1, datetime(2023, 6, 5, 12), datetime(2023, 6, 5, 18)) == 0.0

def test_swap_accurate_pips_negative():
    engine = _engine_()
    assert engine._swap_(Direction.Buy, 10000.0, 1.1, datetime(2023, 6, 5, 12), datetime(2023, 6, 9, 12)) < 0.0

def test_stop_level_buy():
    engine = _engine_()
    buy = _Position_(Direction.Buy, stop_loss=1.0950, take_profit=1.1050)
    assert engine._stop_level_(buy, 1.0951, 1.0949) == (1.0950, UpdateID.StopLossBuyPosition)
    assert engine._stop_level_(buy, 1.1051, 1.1051) == (1.1050, UpdateID.TakeProfitBuyPosition)
    assert engine._stop_level_(buy, 1.1000, 1.1000) == (None, None)

def test_stop_level_sell():
    engine = _engine_()
    sell = _Position_(Direction.Sell, stop_loss=1.1050, take_profit=1.0950)
    assert engine._stop_level_(sell, 1.1051, 1.1049) == (1.1050, UpdateID.StopLossSellPosition)
    assert engine._stop_level_(sell, 1.0949, 1.0949) == (1.0950, UpdateID.TakeProfitSellPosition)
    assert engine._stop_level_(sell, 1.1000, 1.1000) == (None, None)

def test_tick_bars_grouping(monkeypatch):
    engine = _engine_()
    timestamps = [datetime(2023, 1, 1, 0, 0, i) for i in range(5)]
    asks = bids = [1.10, 1.12, 1.09, 1.11, 1.13]
    monkeypatch.setattr(engine, "_period_ticks_", lambda bar: (timestamps, asks, bids))
    out = list(engine._tick_bars_(None, 5))
    assert [bid for _, _, bid in out] == [1.10, 1.09, 1.13]

def test_parse_date():
    assert BacktestingAPI._parse_date_("2023-01-01", end=False) == datetime(2023, 1, 1, 0, 0, 0)
    end = BacktestingAPI._parse_date_("2023-01-01", end=True)
    assert (end.hour, end.minute, end.second) == (23, 59, 59)
