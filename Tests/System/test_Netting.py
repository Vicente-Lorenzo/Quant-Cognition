import itertools
import random
from datetime import datetime, timedelta

import pytest

from Library.Market.Price import Direction
from Library.Portfolio.Position import PositionType
from Library.Portfolio.Trade import TradeAPI
from Library.Protocol.Action import OpenBuyPositionActionAPI, OpenSellPositionActionAPI
from Library.System.Backtesting import BacktestingAPI
from Library.Universe.Contract import CommissionMode, CommissionType, SpreadType, SwapType
from Library.Utility.Datetime import Weekday
from Library.Utility.Math import truncate

ASK, BID = 1.10002, 1.10000
TOLERANCE = 1e-9

class _Contract_:

    PointSize = 0.00001
    PipSize = 0.0001
    LotSize = 100000
    VolumeMin = 1000.0
    VolumeMax = 10000000.0
    VolumeStep = 1000.0
    Commission = 45.0
    CommissionMode = CommissionMode.BaseAssetPerMillionVolume
    SwapLong = 0.0
    SwapShort = 0.0
    SwapMode = None
    SwapPeriod = 24
    SwapWinterTime = 22
    SwapSummerTime = 21
    SwapExtraDay = Weekday.Wednesday

class _Price_:

    def __init__(self, price) -> None:
        self.Price = price

class _Stamp_:

    def __init__(self, moment) -> None:
        self.DateTime = moment

class _Tick_:

    def __init__(self, ask, bid, moment) -> None:
        self.Ask, self.Bid = _Price_(ask), _Price_(bid)
        self.Timestamp = _Stamp_(moment)
        self.AskBaseConversion = self.BidBaseConversion = None
        self.AskQuoteConversion = self.BidQuoteConversion = None

def _engine_(commission=(CommissionType.Points, 3.5)):
    engine = object.__new__(BacktestingAPI)
    engine._contract_ = _Contract_()
    engine._spread_type_, engine._spread_value_ = SpreadType.Accurate, None
    engine._commission_type_, engine._commission_value_ = commission
    engine._swap_type_, engine._swap_long_, engine._swap_short_ = SwapType.Points, 0.0, 0.0
    engine._account_asset_, engine._base_asset_, engine._quote_asset_ = "EUR", "EUR", "USD"
    engine._digits_ = 5
    engine._positions_ = {}
    engine._arm_version_ = 0
    engine._uid_queue_, engine._arg_queue_ = [], []
    engine._pids_, engine._tids_ = itertools.count(1), itertools.count(1)
    engine.account = None
    engine._security_ = None
    engine._bar_ = None
    engine._netting_ = True
    engine._tick_ = _Tick_(ASK, BID, datetime(2024, 1, 1, 12, 0))
    return engine

def _fill_(engine, direction, volume, ask=ASK, bid=BID, minutes=0):
    engine._tick_ = _Tick_(ask, bid, datetime(2024, 1, 1, 12, 0) + timedelta(minutes=minutes))
    builder = OpenBuyPositionActionAPI if direction == Direction.Buy else OpenSellPositionActionAPI
    action = builder(PositionType=PositionType.Normal, Volume=volume, StopLoss=None, TakeProfit=None)
    engine._emit_net_open_(action, direction, volume, None, None)

def _trades_(engine):
    return [item for item in engine._arg_queue_ if isinstance(item, TradeAPI)]

def _signed_(engine):
    position = engine._net_position_()
    if position is None: return 0.0
    return position.Volume if position.Direction == Direction.Buy else -position.Volume

def test_netting_never_holds_more_than_one_position():
    engine = _engine_()
    for direction, volume in ((Direction.Buy, 2000.0), (Direction.Buy, 3000.0), (Direction.Sell, 1000.0),
                              (Direction.Sell, 9000.0), (Direction.Buy, 4000.0)):
        _fill_(engine, direction, volume)
        assert len(engine._positions_) <= 1

def test_net_volume_equals_the_algebraic_sum_of_fills():
    engine = _engine_()
    fills = ((Direction.Buy, 2000.0), (Direction.Buy, 3000.0), (Direction.Sell, 1000.0), (Direction.Sell, 2000.0))
    for direction, volume in fills: _fill_(engine, direction, volume)
    expected = sum(volume if direction == Direction.Buy else -volume for direction, volume in fills)
    assert _signed_(engine) == pytest.approx(expected, abs=TOLERANCE)

def test_a_flip_leaves_exactly_the_remainder_on_the_other_side():
    engine = _engine_()
    _fill_(engine, Direction.Buy, 3000.0)
    _fill_(engine, Direction.Sell, 8000.0)
    assert _signed_(engine) == pytest.approx(-5000.0, abs=TOLERANCE)

def test_an_exact_offset_leaves_no_position():
    engine = _engine_()
    _fill_(engine, Direction.Buy, 4000.0)
    _fill_(engine, Direction.Sell, 4000.0)
    assert engine._positions_ == {}
    assert _signed_(engine) == 0.0

def test_entry_price_is_volume_weighted_across_increases():
    engine = _engine_()
    _fill_(engine, Direction.Buy, 2000.0, ask=1.10000, bid=1.09998)
    _fill_(engine, Direction.Buy, 6000.0, ask=1.20000, bid=1.19998)
    expected = (1.10000 * 2000.0 + 1.20000 * 6000.0) / 8000.0
    assert engine._net_position_().EntryPrice.Price == pytest.approx(round(expected, 5), abs=1e-6)

def test_a_partial_close_preserves_the_average_entry():
    engine = _engine_()
    _fill_(engine, Direction.Buy, 2000.0, ask=1.10000, bid=1.09998)
    _fill_(engine, Direction.Buy, 6000.0, ask=1.20000, bid=1.19998)
    average = engine._net_position_().EntryPrice.Price
    _fill_(engine, Direction.Sell, 3000.0, ask=1.30000, bid=1.29998)
    assert engine._net_position_().EntryPrice.Price == pytest.approx(average, abs=TOLERANCE)
    assert engine._net_position_().Volume == pytest.approx(5000.0, abs=TOLERANCE)

def test_realized_pnl_on_a_reduce_uses_the_average_entry():
    engine = _engine_()
    _fill_(engine, Direction.Buy, 2000.0, ask=1.10000, bid=1.09998)
    _fill_(engine, Direction.Buy, 6000.0, ask=1.20000, bid=1.19998)
    average = engine._net_position_().EntryPrice.Price
    _fill_(engine, Direction.Sell, 3000.0, ask=1.30000, bid=1.29998)
    trade = _trades_(engine)[-1]
    quote = 1.0 / 1.30000
    assert trade.GrossPnL.PnL == pytest.approx((1.29998 - average) * 3000.0 * quote, abs=1e-6)
    assert trade.EntryPrice.Price == pytest.approx(average, abs=TOLERANCE)

def test_commission_is_conserved_across_a_partial_close():
    engine = _engine_()
    _fill_(engine, Direction.Buy, 2000.0)
    opened = engine._net_position_().CommissionPnL.PnL
    _fill_(engine, Direction.Sell, 500.0)
    trade = _trades_(engine)[-1]
    retained = engine._net_position_().CommissionPnL.PnL
    charged = truncate(engine._commission_(500.0, engine._symbol_rate_(engine._tick_), *engine._conversions_(engine._tick_)))
    assert retained + (trade.CommissionPnL.PnL - charged) == pytest.approx(opened, abs=1e-6)

def test_commission_accrues_on_added_volume_only():
    engine = _engine_()
    _fill_(engine, Direction.Buy, 1000.0)
    first = engine._net_position_().CommissionPnL.PnL
    _fill_(engine, Direction.Buy, 1000.0)
    second = engine._net_position_().CommissionPnL.PnL
    assert second == pytest.approx(2.0 * first, abs=1e-6)

def test_a_round_trip_realizes_exactly_the_volume_that_was_opened():
    engine = _engine_()
    for direction, volume in ((Direction.Buy, 2000.0), (Direction.Buy, 3000.0)): _fill_(engine, direction, volume)
    _fill_(engine, Direction.Sell, 5000.0)
    assert sum(trade.Volume for trade in _trades_(engine)) == pytest.approx(5000.0, abs=TOLERANCE)
    assert engine._positions_ == {}

def test_a_flip_realizes_the_whole_old_side_before_reopening():
    engine = _engine_()
    _fill_(engine, Direction.Buy, 3000.0)
    _fill_(engine, Direction.Sell, 8000.0)
    assert sum(trade.Volume for trade in _trades_(engine)) == pytest.approx(3000.0, abs=TOLERANCE)
    assert engine._net_position_().Direction == Direction.Sell

def test_a_random_walk_of_fills_keeps_volume_conserved():
    engine = _engine_()
    walk = random.Random(20260721)
    exposure = 0.0
    for step in range(120):
        direction = walk.choice((Direction.Buy, Direction.Sell))
        volume = walk.choice((1000.0, 2000.0, 3000.0, 4000.0))
        _fill_(engine, direction, volume, minutes=step)
        exposure += volume if direction == Direction.Buy else -volume
        assert len(engine._positions_) <= 1
        assert _signed_(engine) == pytest.approx(exposure, abs=1e-6)

def test_quantity_tracks_volume_through_every_transition():
    engine = _engine_()
    for direction, volume in ((Direction.Buy, 2000.0), (Direction.Buy, 3000.0), (Direction.Sell, 1000.0), (Direction.Sell, 9000.0)):
        _fill_(engine, direction, volume)
        position = engine._net_position_()
        if position is None: continue
        assert position.Quantity == pytest.approx(position.Volume / _Contract_.LotSize, abs=TOLERANCE)