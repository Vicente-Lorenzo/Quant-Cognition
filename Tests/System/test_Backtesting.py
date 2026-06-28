import random
import numpy as np
import pytest
from datetime import datetime

from Library.System.Backtesting import BacktestingAPI, DatasetAPI
from Library.Market.Price import Direction
from Library.Protocol.Update import UpdateID
from Library.Universe.Contract import CommissionType, CommissionMode, SpreadType, SwapType, SwapMode
from Library.Utility.Datetime import Weekday
from Library.Utility.Math import truncate
from Library.Utility.Typing import MISSING

def _dataset_(**overrides):
    fields = dict(WarmupBars=None, ExecutionBars=[], TickTimestamps=np.empty(0, dtype="int64"),
                  TickAsks=np.empty(0, dtype="float64"), TickBids=np.empty(0, dtype="float64"),
                  TickConversions=None, IntraLevels=[], IntraBars={})
    fields.update(overrides)
    return DatasetAPI(**fields)

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

class _ConvTick_:
    def __init__(self, ask, bid, abc=None, bbc=None, aqc=None, bqc=None):
        self.Ask = _Price_(ask)
        self.Bid = _Price_(bid)
        self.AskBaseConversion = _Price_(abc) if abc is not None else None
        self.BidBaseConversion = _Price_(bbc) if bbc is not None else None
        self.AskQuoteConversion = _Price_(aqc) if aqc is not None else None
        self.BidQuoteConversion = _Price_(bqc) if bqc is not None else None

def test_conversions_uses_stored_bid_fields():
    engine = _engine_()
    tick = _ConvTick_(1.06929, 1.06927, abc=1.0, bbc=1.0, aqc=0.93522, bqc=0.93520)
    base, quote = engine._conversions_(tick)
    assert base == pytest.approx(1.0)
    assert quote == pytest.approx(0.93520)

def test_conversions_fallback_is_bid_side():
    engine = _engine_()
    base, quote = engine._conversions_(_ConvTick_(1.10005, 1.10000))
    assert base == pytest.approx(1.0)
    assert quote == pytest.approx(1.0 / 1.10005)

def _conversion_engine_():
    engine = _engine_()
    engine._needs_conversion_ = True
    conversions = (np.array([0.80, 0.81, 0.82]), np.array([0.79, 0.80, 0.81]),
                   np.array([0.90, 0.91, 0.92]), np.array([0.89, 0.90, 0.91]))
    engine._dataset_ = _dataset_(TickTimestamps=np.array([100, 200, 300], dtype="int64"), TickConversions=conversions)
    return engine

def test_conversion_at_none_without_arrays():
    engine = _engine_()
    engine._dataset_ = _dataset_(TickTimestamps=np.array([100, 200], dtype="int64"), TickConversions=None)
    assert engine._conversion_at_(150) == (None, None, None, None)

def test_conversion_at_indexes_latest_at_or_before():
    engine = _conversion_engine_()
    assert engine._conversion_at_(200) == pytest.approx((0.81, 0.80, 0.91, 0.90))
    assert engine._conversion_at_(250) == pytest.approx((0.81, 0.80, 0.91, 0.90))
    assert engine._conversion_at_(300) == pytest.approx((0.82, 0.81, 0.92, 0.91))

def test_conversion_at_before_first_tick_is_none():
    engine = _conversion_engine_()
    assert engine._conversion_at_(50) == (None, None, None, None)

def test_conversion_at_nan_falls_back_to_none():
    engine = _conversion_engine_()
    conversions = (np.array([np.nan, 0.81, 0.82]), np.array([0.79, 0.80, 0.81]),
                   np.array([np.nan, 0.91, 0.92]), np.array([0.89, 0.90, 0.91]))
    engine._dataset_ = _dataset_(TickTimestamps=engine._dataset_.TickTimestamps, TickConversions=conversions)
    assert engine._conversion_at_(100) == (None, 0.79, None, 0.89)

def test_tick_conversions_account_is_base_uses_raw():
    engine = _engine_()
    engine._needs_conversion_ = False
    assert engine._tick_conversions_(0, 1.10005, 1.10000) == pytest.approx((1.0, 1.0, 1.0 / 1.10000, 1.0 / 1.10005))

def test_tick_conversions_account_is_quote_uses_raw():
    engine = _engine_()
    engine._account_asset_, engine._base_asset_, engine._quote_asset_ = "USD", "GBP", "USD"
    engine._needs_conversion_ = False
    assert engine._tick_conversions_(0, 1.30010, 1.30000) == pytest.approx((1.30010, 1.30000, 1.0, 1.0))

def test_commission_accurate_is_truncated_per_deal():
    engine = _engine_()
    raw = engine._commission_(7000.0, 1.1)
    assert raw == pytest.approx(7000.0 * (-45.0 / 1_000_000) * 1.0)
    assert truncate(raw) == pytest.approx(-0.31)

_BIDS_ = (1.10000, 1.10500, 1.09500, 1.10100)
_ASKS_ = (1.10002, 1.10502, 1.09502, 1.10102)

def _descend_engine_():
    engine = _engine_()
    engine._positions_ = {}
    engine._ask_above_ = engine._ask_below_ = engine._bid_above_ = engine._bid_below_ = None
    return engine

def test_spread_ceiling_accurate_is_max_raw_spread():
    assert _descend_engine_()._spread_ceiling_(_BIDS_, _ASKS_) == pytest.approx(0.00002)

def test_should_descend_skips_when_flat():
    assert _descend_engine_()._should_descend_(_BIDS_, _ASKS_) is False

def test_should_descend_true_when_buy_stop_reachable():
    engine = _descend_engine_()
    engine._positions_ = {1: _Position_(Direction.Buy, stop_loss=1.10000)}
    assert engine._should_descend_(_BIDS_, _ASKS_) is True

def test_should_descend_false_when_buy_stop_below_bar():
    engine = _descend_engine_()
    engine._positions_ = {1: _Position_(Direction.Buy, stop_loss=1.08000)}
    assert engine._should_descend_(_BIDS_, _ASKS_) is False

def test_should_descend_true_when_target_reachable():
    engine = _descend_engine_()
    engine._bid_above_ = 1.10300
    assert engine._should_descend_(_BIDS_, _ASKS_) is True

def test_should_descend_true_when_sell_stop_below_gapped_bar():
    engine = _descend_engine_()
    engine._positions_ = {1: _Position_(Direction.Sell, stop_loss=1.09000)}
    assert engine._should_descend_(_BIDS_, _ASKS_) is True

def test_should_descend_false_when_sell_stop_above_bar():
    engine = _descend_engine_()
    engine._positions_ = {1: _Position_(Direction.Sell, stop_loss=1.12000)}
    assert engine._should_descend_(_BIDS_, _ASKS_) is False

def test_effective_bounds_accurate_is_raw_ask():
    engine = _descend_engine_()
    ask, bid = np.array([1.10002, 1.10502]), np.array([1.10000, 1.10500])
    eb, ask_low, ask_high = engine._effective_bounds_(ask, bid)
    assert eb.tolist() == bid.tolist()
    assert ask_low.tolist() == ask.tolist() and ask_high.tolist() == ask.tolist()

def test_candidate_mask_flat_is_empty():
    engine = _descend_engine_()
    bid = np.array([1.10000, 1.10500, 1.09500])
    eb, ask_low, ask_high = engine._effective_bounds_(bid + 0.00002, bid)
    assert not engine._candidate_mask_(eb, ask_low, ask_high).any()

def test_candidate_mask_flags_only_reachable_buy_stop():
    engine = _descend_engine_()
    engine._positions_ = {1: _Position_(Direction.Buy, stop_loss=1.10000)}
    bid = np.array([1.10100, 1.10000, 1.10050])
    eb, ask_low, ask_high = engine._effective_bounds_(bid + 0.00002, bid)
    assert engine._candidate_mask_(eb, ask_low, ask_high).tolist() == [False, True, False]

class _LogStub_:
    def info(self, fn): pass
    def debug(self, fn): pass

class _FakeArr_:
    size = 7

def _preload_stub_():
    engine = object.__new__(BacktestingAPI)
    engine._injected_ = None
    engine._security_ = type("S", (), {"UID": 1})()
    engine._timeframe_ = type("T", (), {"UID": "D1"})()
    engine._start_ = datetime(2023, 1, 1)
    engine._stop_ = datetime(2024, 1, 1)
    engine._auto_ = True
    engine._log_ = _LogStub_()
    return engine

def test_preload_cache_reuses_across_instances(monkeypatch):
    BacktestingAPI._PRELOAD_CACHE_.clear()
    monkeypatch.setattr(BacktestingAPI, "_DISK_CACHE_", False)
    bars = [object()]
    monkeypatch.setattr(BacktestingAPI, "_load_bars_", lambda self: (None, bars))
    calls = []
    monkeypatch.setattr(BacktestingAPI, "_load_frames_", lambda self, b: (calls.append(1), (_FakeArr_(), _FakeArr_(), _FakeArr_(), None, [], {}))[1])
    first, second = _preload_stub_(), _preload_stub_()
    first._preload_()
    second._preload_()
    assert len(calls) == 1
    assert first._dataset_ is second._dataset_
    assert first._dataset_.ExecutionBars is second._dataset_.ExecutionBars
    third = _preload_stub_()
    third._start_ = datetime(2022, 1, 1)
    third._preload_()
    assert len(calls) == 2
    BacktestingAPI._PRELOAD_CACHE_.clear()

def test_preload_injects_dataset_without_loading(monkeypatch):
    BacktestingAPI._PRELOAD_CACHE_.clear()
    calls = []
    monkeypatch.setattr(BacktestingAPI, "_load_bars_", lambda self: calls.append("bars"))
    monkeypatch.setattr(BacktestingAPI, "_acquire_frames_", lambda self, b: calls.append("frames"))
    arr = _FakeArr_()
    bars = [object()]
    dataset = _dataset_(ExecutionBars=bars, TickTimestamps=arr, TickAsks=arr, TickBids=arr)
    engine = _preload_stub_()
    engine._injected_ = dataset
    engine._preload_()
    assert calls == []
    assert engine._dataset_ is dataset
    assert engine._dataset_.ExecutionBars is bars
    assert engine._dataset_.TickTimestamps is arr

def test_extract_inject_round_trips_state():
    arr = _FakeArr_()
    bars = [object()]
    source = _preload_stub_()
    source._dataset_ = _dataset_(ExecutionBars=bars, TickTimestamps=arr, TickAsks=arr, TickBids=arr)
    target = _preload_stub_()
    target.inject(source.extract())
    target._preload_()
    assert target._dataset_ is source._dataset_
    assert target._dataset_.ExecutionBars is bars
    assert target._dataset_.TickTimestamps is arr

def test_auto_fee_types_resolve_to_accurate():
    engine = BacktestingAPI(
        strategy=type("Strategy", (), {}), security=object(), timeframe=object(), resolution=MISSING,
        parameters=object(), start="2023-01-01", stop="2024-01-01", account=("EUR", 10000.0, 30.0),
        spread=(SpreadType.Auto, MISSING), commission=(CommissionType.Auto, MISSING), swap=(SwapType.Auto, MISSING, MISSING),
        report=False, export=False)
    assert engine._spread_type_ == SpreadType.Accurate
    assert engine._commission_type_ == CommissionType.Accurate
    assert engine._swap_type_ == SwapType.Accurate
    assert engine._resolution_arg_ is MISSING
