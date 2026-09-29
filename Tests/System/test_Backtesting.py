import pytest
import random

from datetime import datetime
from types import SimpleNamespace

from Library.Database.Dataframe import np, pl
from Library.Market.Price import Direction
from Library.Market.Tape import TapeAPI
from Library.Logging import LoggingAPI, VerboseLevel
from Library.System.Backtesting import BacktestingAPI, DatasetAPI
from Library.System.Learning import LearningAPI
from Library.System.Optimization import OptimizationAPI
from Library.System.System import SystemAPI
from Library.Protocol.Update import UpdateID
from Library.Universe.Timeframe import TimeframeAPI
from Library.Universe.Contract import CommissionType, CommissionMode, ContractAPI, SpreadType, SwapType, SwapMode
from Library.Utility.Datetime import Weekday, datetime_to_epoch, epoch_to_datetime
from Library.Utility.Math import quantize
from Library.Utility.Typing import MISSING

def _dataset_(**overrides):
    fields = dict(
        WarmupBars=None,
        ExecutionBars=[],
        Ticks=TapeAPI.empty(1),
        Conversions=(None, None)
    )
    fields.update(overrides)
    return DatasetAPI(**fields)

def _nights_(engine, entry, exit):
    stamps, days = engine._rolls_
    return int(days[np.searchsorted(stamps, datetime_to_epoch(entry), side="right"):np.searchsorted(stamps, datetime_to_epoch(exit), side="left")].sum())

def _contract_():
    return ContractAPI(PointSize=0.00001, PipSize=0.0001, LotSize=100000, Commission=45.0, CommissionMode=CommissionMode.BaseAssetPerMillionVolume, SwapLong=-2.445, SwapShort=-0.105, SwapMode=SwapMode.Pips, SwapPeriod=24, SwapTime=1259, SwapExtraDay=Weekday.Wednesday, SwapWeekends=False)

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
    engine._contract_ = _contract_()
    engine._start_, engine._stop_ = datetime(2015, 1, 1), datetime(2024, 1, 1)
    engine._rolls_ = engine._schedule_()
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
    assert engine._commission_(10000.0, 1.1, 1.0, 1.0 / 1.1) == pytest.approx(10000.0 * (-1.0 * 0.00001) * (1.0 / 1.1))

def test_commission_percentage():
    engine = _engine_(commission=(CommissionType.Percentage, 1.0))
    assert engine._commission_(10000.0, 1.1, 1.0, 1.0 / 1.1) == pytest.approx(-1.0 / 100.0 * 10000.0)

def test_commission_amount():
    engine = _engine_(commission=(CommissionType.Amount, 5.0))
    assert engine._commission_(10000.0, 1.1, 1.0, 1.0 / 1.1) == pytest.approx(-5.0)

def test_commission_per_lot_is_the_same_amount_on_every_pair():
    engine = _engine_(commission=(CommissionType.Lots, 3.5))
    assert engine._commission_(100000.0, 1.1, 1.0, 1.0 / 1.1) == pytest.approx(-3.5)
    assert engine._commission_(250000.0, 150.0, 1.0, 1.0 / 150.0) == pytest.approx(-8.75)

def test_commission_accurate_base_per_million():
    engine = _engine_()
    assert engine._commission_(10000.0, 1.1, 1.0, 1.0 / 1.1) == pytest.approx(10000.0 * (-45.0 / 1_000_000) * 1.0)

def test_commission_accurate_per_lot():
    engine = _engine_()
    engine._contract_.CommissionMode = CommissionMode.BaseAssetPerOneLot
    assert engine._commission_(100000.0, 1.1, 1.0, 1.0 / 1.1) == pytest.approx(1.0 * -45.0 * 1.0)

def test_commission_accurate_percentage_of_value():
    engine = _engine_()
    engine._contract_.CommissionMode, engine._contract_.Commission = CommissionMode.PercentageOfVolume, 0.01
    assert engine._commission_(10.0, 4000.0, 1.0, 0.9) == pytest.approx(-0.0001 * 10.0 * 4000.0 * 0.9)

def test_commission_minimum_is_charged_per_side_in_its_asset():
    engine = _engine_()
    engine._contract_.CommissionMode, engine._contract_.Commission = CommissionMode.PercentageOfVolume, 0.01
    engine._contract_.MinCommission, engine._contract_.MinCommissionAsset = 4.0, "USD"
    engine._account_asset_, engine._base_asset_, engine._quote_asset_ = "EUR", "US 500", "USD"
    tick = SimpleNamespace(Ask=_Price_(7670.8), Bid=_Price_(7670.6), BidBaseConversion=None, BidQuoteConversion=_Price_(1.0 / 1.1363), Timestamp=SimpleNamespace(DateTime=datetime(2026, 9, 28)))
    assert engine._fee_(1.0, tick) == pytest.approx(-3.52)
    assert engine._fee_(20.0, tick) == pytest.approx(quantize(-0.0001 * 20.0 * 7670.7 / 1.1363))

def test_commission_minimum_through_its_own_conversion():
    engine = _engine_()
    engine._contract_.CommissionMode, engine._contract_.Commission = CommissionMode.PercentageOfVolume, 0.01
    engine._contract_.MinCommission, engine._contract_.MinCommissionAsset = 4.0, "USD"
    engine._account_asset_, engine._base_asset_, engine._quote_asset_ = "CHF", "GERMANY 40", "EUR"
    engine._dataset_ = _dataset_(Conversions=(None, None, _source_([0.80, 0.80, 0.80], [0.79, 0.79, 0.79])))
    tick = SimpleNamespace(Timestamp=SimpleNamespace(DateTime=epoch_to_datetime(150)))
    assert engine._minimum_(tick, 1.0, 0.95) == pytest.approx(4.0 * 0.79)

def test_base_conversion_is_optional_unless_commission_needs_it():
    engine = _engine_()
    engine._contract_.CommissionMode = CommissionMode.PercentageOfVolume
    engine._account_asset_, engine._base_asset_ = "EUR", "US 500"
    engine._log_ = LoggingAPI()
    def refuse(asset, tape): raise ValueError(f"Conversion {asset} to EUR: Failed")
    engine._source_ = refuse
    source = engine._base_source_(TapeAPI.empty(7))
    assert source[0].Stamps.size == 0 and np.isnan(TapeAPI.rates(np.array([1], dtype=np.int64), source)[1][0])
    engine._contract_.CommissionMode = CommissionMode.BaseAssetPerOneLot
    with pytest.raises(ValueError, match="US 500"): engine._base_source_(TapeAPI.empty(7))

def test_overnights_zero_when_not_held():
    engine = _engine_()
    assert _nights_(engine, datetime(2023, 6, 1, 12), datetime(2023, 6, 1, 12)) == 0

def test_overnights_positive_for_multiday():
    engine = _engine_()
    assert _nights_(engine, datetime(2023, 6, 5, 12), datetime(2023, 6, 9, 12)) > 0

def test_overnights_roll_at_the_contract_swap_time_in_utc_all_year():
    engine = _engine_()
    assert _nights_(engine, datetime(2015, 4, 1, 21, 0, 0, 303000), datetime(2015, 4, 2, 13, 49)) == 0
    assert _nights_(engine, datetime(2015, 4, 1, 20, 58, 59), datetime(2015, 4, 1, 20, 59, 1)) == 3
    assert _nights_(engine, datetime(2023, 1, 10, 20, 30), datetime(2023, 1, 10, 21, 30)) == 1
    assert _nights_(engine, datetime(2023, 1, 10, 21, 30), datetime(2023, 1, 10, 22, 30)) == 0
    assert _nights_(engine, datetime(2023, 6, 9, 12), datetime(2023, 6, 12, 12)) == 1

def test_no_swap_time_means_no_roll():
    engine = _engine_()
    engine._contract_.SwapTime = None
    engine._rolls_ = engine._schedule_()
    assert _nights_(engine, datetime(2023, 6, 5, 12), datetime(2023, 6, 9, 12)) == 0

def test_skipped_periods_spare_a_position_its_first_charges():
    engine = _engine_()
    engine._contract_.SwapSkip = 1
    engine._rolls_ = engine._schedule_()
    engine._positions_, engine._roll_index_, engine._tick_ = {}, 0, None
    engine._roll_rates_ = np.ones(engine._rolls_[0].size)
    charged = []
    engine.portfolio = SimpleNamespace(charge=lambda position, swap: charged.append(swap))
    position = SimpleNamespace(UID=1, EntryTimestamp=SimpleNamespace(DateTime=datetime(2015, 1, 5, 12)), Direction=Direction.Buy, Volume=10000.0)
    engine._positions_[1] = position
    engine._accrue_(datetime_to_epoch(datetime(2015, 1, 7, 12)))
    assert len(charged) == 1

def test_swap_amount_is_charged_per_day_in_the_account_currency():
    engine = _engine_(swap=(SwapType.Amount, -2.0, -3.0))
    assert engine._swap_amount_(True, 10000.0, 1.1, 2, 0.5) == pytest.approx(-4.0)
    assert engine._swap_amount_(False, 10000.0, 1.1, 3, 0.5) == pytest.approx(-9.0)

def test_swap_zero_intraday():
    assert _nights_(_engine_(), datetime(2023, 6, 5, 12), datetime(2023, 6, 5, 18)) == 0

def test_swap_accurate_pips_are_converted_from_the_quote():
    engine = _engine_()
    assert engine._swap_amount_(True, 10000.0, 1.1, 1, 1.0 / 1.1) == pytest.approx(10000.0 * -2.445 * 0.0001 / 1.1)
    assert engine._swap_amount_(False, 10000.0, 1.1, 3, 1.0 / 1.1) == pytest.approx(3 * 10000.0 * -0.105 * 0.0001 / 1.1)

def test_swap_points_and_percentage_follow_their_own_terms():
    assert _engine_(swap=(SwapType.Points, -5.0, 2.0))._swap_amount_(True, 10000.0, 1.1, 2, 1.0) == pytest.approx(10000.0 * -5.0 * 0.00001 * 2)
    assert _engine_(swap=(SwapType.Percentage, -3.65, 1.0))._swap_amount_(True, 10000.0, 1.1, 1, 1.0) == pytest.approx(10000.0 * 1.1 * -0.0365 / 365.0)

def test_the_roll_schedule_comes_from_the_contract():
    engine = _engine_()
    engine._contract_.SwapWeekends = True
    engine._rolls_ = engine._schedule_()
    assert _nights_(engine, datetime(2023, 6, 9, 12), datetime(2023, 6, 12, 12)) == 3
    engine._contract_.SwapWeekends, engine._contract_.SwapExtraDay = False, Weekday.Friday
    engine._rolls_ = engine._schedule_()
    assert _nights_(engine, datetime(2023, 6, 9, 12), datetime(2023, 6, 12, 12)) == 3 and _nights_(engine, datetime(2023, 6, 6, 12), datetime(2023, 6, 8, 12)) == 2

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

def test_a_tick_bar_keeps_the_ask_extremes_where_the_spread_widens():
    bids = np.array([1.1000, 1.1002, 1.1001, 1.0999, 1.1000, 1.1003, 1.1001, 1.1002, 1.1000, 1.1001])
    asks = bids + np.array([0.2, 0.2, 1.5, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]) / 1000
    tape = TapeAPI(Security=1, Stamps=np.arange(10, dtype=np.int64) * 1000, Asks=asks, Bids=bids, Volumes=np.ones(10))
    points = BacktestingAPI._points_(tape, tape.bars(TimeframeAPI(UID="T5")))
    assert (points.Stamps // 1000).tolist() == [0, 1, 2, 3, 4, 5, 8, 9]

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

def _source_(asks: list, bids: list) -> tuple:
    stamps = np.array([100, 200, 300], dtype=np.int64)
    return TapeAPI(Security=2, Stamps=stamps, Asks=np.array(asks), Bids=np.array(bids), Volumes=np.ones(3)), False

def _conversion_engine_(base=([0.80, 0.81, 0.82], [0.79, 0.80, 0.81]), quote=([0.90, 0.91, 0.92], [0.89, 0.90, 0.91])):
    engine = _engine_()
    engine._needs_conversion_ = True
    engine._dataset_ = _dataset_(Conversions=(_source_(*base), _source_(*quote)))
    return engine

def test_conversion_at_without_a_source_is_one():
    engine = _engine_()
    engine._dataset_ = _dataset_()
    assert engine._conversion_at_(150) == (1.0, 1.0, 1.0, 1.0)

def test_conversion_at_inverts_an_inverse_source():
    engine = _engine_()
    engine._dataset_ = _dataset_(Conversions=(None, (_source_([1.25, 1.25, 1.25], [1.0, 1.0, 1.0])[0], True)))
    assert engine._conversion_at_(200) == pytest.approx((1.0, 1.0, 1.0, 0.8))

def test_conversion_at_indexes_latest_at_or_before():
    engine = _conversion_engine_()
    assert engine._conversion_at_(200) == pytest.approx((0.81, 0.80, 0.91, 0.90))
    assert engine._conversion_at_(250) == pytest.approx((0.81, 0.80, 0.91, 0.90))
    assert engine._conversion_at_(300) == pytest.approx((0.82, 0.81, 0.92, 0.91))

def test_conversion_at_before_first_tick_is_none():
    engine = _conversion_engine_()
    assert engine._conversion_at_(50) == (None, None, None, None)

def test_a_conversion_kept_only_at_the_walked_stamps_reads_the_same_rates():
    source = TapeAPI(Security=2, Stamps=np.array([100, 150, 300], dtype=np.int64), Asks=np.array([0.80, 0.81, 0.82]), Bids=np.array([0.79, 0.80, 0.81]), Volumes=np.ones(3))
    stamps = np.array([90, 120, 150, 299, 300], dtype=np.int64)
    reduced = BacktestingAPI._reduce_((source, True), stamps)
    for stamp in stamps.tolist():
        full, kept = TapeAPI.rates(np.array([stamp]), (source, True)), TapeAPI.rates(np.array([stamp]), reduced)
        assert np.array_equal(full[0], kept[0], equal_nan=True) and np.array_equal(full[1], kept[1], equal_nan=True)
    assert BacktestingAPI._reduce_(None, stamps) is None

def test_conversion_at_nan_falls_back_to_none():
    engine = _conversion_engine_(base=([np.nan, 0.81, 0.82], [0.79, 0.80, 0.81]), quote=([np.nan, 0.91, 0.92], [0.89, 0.90, 0.91]))
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

def test_commission_accurate_is_rounded_half_up_per_deal():
    engine = _engine_()
    raw = engine._commission_(7000.0, 1.1, 1.0, 1.0 / 1.1)
    assert raw == pytest.approx(7000.0 * (-45.0 / 1_000_000) * 1.0)
    assert quantize(raw) == pytest.approx(-0.32)

def test_a_partial_close_takes_the_rounded_share_of_its_lot_fee():
    engine = _engine_()
    engine._lots_ = {7: [[datetime(2026, 9, 29), 1.13693, 10000.0, -0.45, 0.0]]}
    position = SimpleNamespace(UID=7)
    first = engine._consume_(position, 5000.0)
    second = engine._consume_(position, 5000.0)
    assert (first[2], second[2]) == (pytest.approx(-0.23), pytest.approx(-0.22)) and not engine._lots_[7]

def _walk_engine_():
    engine = _engine_()
    engine._positions_ = {}
    engine._ask_above_ = engine._ask_below_ = engine._bid_above_ = engine._bid_below_ = None
    return engine

def test_effective_bounds_accurate_is_raw_ask():
    engine = _walk_engine_()
    ask, bid = np.array([1.10002, 1.10502]), np.array([1.10000, 1.10500])
    eb, ask_low, ask_high = engine._effective_bounds_(ask, bid)
    assert eb.tolist() == bid.tolist()
    assert ask_low.tolist() == ask.tolist() and ask_high.tolist() == ask.tolist()

def test_nothing_is_reachable_when_nothing_is_armed():
    engine = _walk_engine_()
    bid = np.array([1.10000, 1.10500, 1.09500])
    eb, ask_low, ask_high = engine._effective_bounds_(bid + 0.00002, bid)
    assert not np.any(engine._reachable_(eb, eb, ask_low, ask_high))

def test_only_the_ticks_that_reach_a_buy_stop_are_walked():
    engine = _walk_engine_()
    engine._positions_ = {1: _Position_(Direction.Buy, stop_loss=1.10000)}
    bid = np.array([1.10100, 1.10000, 1.10050])
    eb, ask_low, ask_high = engine._effective_bounds_(bid + 0.00002, bid)
    assert engine._reachable_(eb, eb, ask_low, ask_high).tolist() == [False, True, False]

def _bar_(asks: np.ndarray, bids: np.ndarray) -> SimpleNamespace:
    point = lambda ask, bid: SimpleNamespace(AskTick=SimpleNamespace(Ask=SimpleNamespace(Price=float(ask))), BidTick=SimpleNamespace(Bid=SimpleNamespace(Price=float(bid))))
    return SimpleNamespace(LowPoint=point(asks.min(), bids.min()), HighPoint=point(asks.max(), bids.max()))

@pytest.mark.parametrize("spread", [(SpreadType.Accurate, None), (SpreadType.Points, 7.0), (SpreadType.Percentage, 0.01), (SpreadType.Random, 5.0)])
def test_the_auto_gate_skips_a_bar_only_when_no_tick_of_it_would_be_walked(spread):
    generator = np.random.default_rng(7)
    engine = _walk_engine_()
    engine._spread_type_, engine._spread_value_ = spread
    for _ in range(400):
        bids = np.round(1.1 + np.cumsum(generator.normal(0, 0.0002, 50)), 5)
        asks = np.round(bids + generator.integers(0, 30, 50) / 100000, 5)
        level = float(np.round(1.1 + generator.normal(0, 0.003), 5))
        engine._positions_, engine._ask_above_, engine._bid_below_ = {}, None, None
        match int(generator.integers(0, 4)):
            case 0: engine._positions_ = {1: _Position_(Direction.Buy, stop_loss=level, take_profit=level + 0.004)}
            case 1: engine._positions_ = {1: _Position_(Direction.Sell, stop_loss=level, take_profit=level - 0.004)}
            case 2: engine._ask_above_ = level
            case _: engine._bid_below_ = level
        bid, ask_low, ask_high = engine._effective_bounds_(asks, bids)
        assert engine._gate_(_bar_(asks, bids)) == bool(np.any(engine._reachable_(bid, bid, ask_low, ask_high)))

def test_a_finer_bar_is_walked_open_then_its_extremes_in_time_then_close():
    tape = TapeAPI(Security=1, Stamps=np.arange(10, dtype=np.int64) * 1000, Asks=np.arange(10) / 10 + 1.0, Bids=np.arange(10) / 10 + 0.9, Volumes=np.ones(10))
    bars = pl.DataFrame({"Open": [0, 5], "HighAsk": [3, 9], "HighBid": [1, 9], "LowAsk": [2, 6], "LowBid": [2, 7], "Close": [4, 9]})
    points = BacktestingAPI._points_(tape, bars)
    assert (points.Stamps // 1000).tolist() == [0, 1, 2, 3, 4, 5, 6, 7, 9]
    assert points.Asks.tolist() == tape.Asks[[0, 1, 2, 3, 4, 5, 6, 7, 9]].tolist()

def test_a_bar_is_walked_through_its_distinct_ticks_in_time():
    tick = lambda second: SimpleNamespace(Timestamp=SimpleNamespace(DateTime=datetime(2024, 1, 2, 10, 0, second)))
    first, low, high, last = tick(0), tick(20), tick(40), tick(59)
    bar = SimpleNamespace(OpenPoint=SimpleNamespace(BidTick=first), HighPoint=SimpleNamespace(AskTick=high, BidTick=first), LowPoint=SimpleNamespace(AskTick=low, BidTick=low), ClosePoint=SimpleNamespace(BidTick=last))
    assert BacktestingAPI._intrabar_(bar) == [first, low, high, last]

def test_auto_walks_nothing_in_a_bar_the_gate_closes(monkeypatch):
    engine = _walk_engine_()
    engine._auto_, engine._resolution_, engine._descended_, engine._skipped_ = True, None, 0, 0
    monkeypatch.setattr(engine, "_gate_", lambda bar: False)
    assert list(engine._intrabar_source_(None)) == [] and engine._skipped_ == 1

class _LogStub_:

    def info(self, fn): pass

    def debug(self, fn): pass

def _preload_stub_(window: int = 20):
    engine = object.__new__(BacktestingAPI)
    engine._injected_ = None
    engine._window_ = window
    engine._security_ = type("S", (), {"UID": 1})()
    engine._timeframe_ = type("T", (), {"UID": "D1"})()
    engine._start_ = datetime(2023, 1, 1)
    engine._stop_ = datetime(2024, 1, 1)
    engine._resolution_, engine._auto_ = type("R", (), {"UID": "T1"})(), True
    engine._account_asset_, engine._bridge_ = "EUR", MISSING
    engine._log_ = _LogStub_()
    return engine

def _loaded_(bars: list) -> tuple:
    return pl.DataFrame(), (None, None), pl.DataFrame({"Row": [0, 1]}), bars, TapeAPI.empty(1), None, [None]

def test_preload_cache_reuses_across_instances(monkeypatch):
    BacktestingAPI._PRELOAD_CACHE_.clear()
    BacktestingAPI._TAPE_CACHE_.clear()
    bars = [object()]
    monkeypatch.setattr(BacktestingAPI, "_load_warmup_", lambda self, early, rows, history: None)
    calls = []
    monkeypatch.setattr(BacktestingAPI, "_load_tape_", lambda self: (calls.append(1), _loaded_(bars))[1])
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

def test_preload_rebuilds_per_window_but_loads_the_tape_once(monkeypatch):
    BacktestingAPI._PRELOAD_CACHE_.clear()
    BacktestingAPI._TAPE_CACHE_.clear()
    bars = [object()]
    windows = []
    monkeypatch.setattr(BacktestingAPI, "_load_warmup_", lambda self, early, rows, history: windows.append(self._window_))
    tapes = []
    monkeypatch.setattr(BacktestingAPI, "_load_tape_", lambda self: (tapes.append(1), _loaded_(bars))[1])
    narrow, wide = _preload_stub_(20), _preload_stub_(30)
    narrow._preload_()
    wide._preload_()
    assert windows == [20, 30]
    assert narrow._dataset_ is not wide._dataset_
    assert len(tapes) == 1
    assert narrow._dataset_.Ticks is wide._dataset_.Ticks and narrow._dataset_.ExecutionBars is wide._dataset_.ExecutionBars
    BacktestingAPI._PRELOAD_CACHE_.clear()
    BacktestingAPI._TAPE_CACHE_.clear()

def test_preload_injects_dataset_without_loading(monkeypatch):
    BacktestingAPI._PRELOAD_CACHE_.clear()
    calls = []
    monkeypatch.setattr(BacktestingAPI, "_load_warmup_", lambda self, early, rows, history: calls.append("bars"))
    monkeypatch.setattr(BacktestingAPI, "_load_tape_", lambda self: calls.append("tape"))
    ticks = TapeAPI.empty(1)
    bars = [object()]
    dataset = _dataset_(ExecutionBars=bars, Ticks=ticks)
    engine = _preload_stub_()
    engine._injected_ = dataset
    engine._preload_()
    assert calls == []
    assert engine._dataset_ is dataset
    assert engine._dataset_.ExecutionBars is bars
    assert engine._dataset_.Ticks is ticks

def test_a_run_that_fans_out_publishes_its_tapes_once_and_reads_them_itself(monkeypatch):
    shares = []
    class _Share_:
        def tapes(self) -> dict:
            return {1: "Shared"}
    def share(self, start, stop):
        shares.append((start, stop))
        return _Share_()
    monkeypatch.setattr(BacktestingAPI, "_share_", share)
    engine = _preload_stub_()
    engine._shared_, engine._shelf_, engine._range_start_, engine._range_stop_ = None, {2: "Conversion"}, engine._start_, engine._stop_
    assert engine._shelve_() is engine._shelve_()
    assert shares == [(engine._start_, engine._stop_)] and engine._shelf_ == {2: "Conversion", 1: "Shared"}
    assert not BacktestingAPI._spawns_(engine)

def test_every_offline_system_publishes_its_run_files_through_the_system():
    assert BacktestingAPI._publish_ is SystemAPI._publish_ and OptimizationAPI._publish_ is SystemAPI._publish_ and LearningAPI._publish_ is SystemAPI._publish_

def test_no_offline_system_shadows_a_private_method_of_its_engine():
    engine = {name for name in vars(BacktestingAPI) if name.startswith("_") and name.endswith("_") and not name.startswith("__") and callable(vars(BacktestingAPI)[name])}
    system = {name for name in vars(SystemAPI) if name.startswith("_") and name.endswith("_") and not name.startswith("__") and callable(vars(SystemAPI)[name])}
    for child in (OptimizationAPI, LearningAPI):
        shadowed = {name for name in vars(child) if name in engine | system and name not in {"_connect_", "_disconnect_", "_spawns_", "_worker_", "_workspace_", "_analysis_", "_fitness_", "_replay_", "_report_"}}
        assert not shadowed, (child.__name__, sorted(shadowed))

def test_a_published_history_serves_every_window_without_a_read(monkeypatch):
    history = pl.DataFrame({"Timestamp": [1, 2, 3, 4, 5], "Close": [1.0, 2.0, 3.0, 4.0, 5.0]})
    early = pl.DataFrame({"Timestamp": [6], "Close": [6.0]})
    monkeypatch.setattr(TapeAPI, "before", classmethod(lambda cls, *args, **kwargs: pytest.fail("Read the database")))
    engine, cell = _preload_stub_(3), [None]
    engine._history_ = {engine._start_: (history, 5)}
    assert engine._load_warmup_(early, None, cell)["Close"].to_list() == [4.0, 5.0, 6.0]
    engine._window_ = 5
    assert engine._load_warmup_(early, None, cell)["Close"].to_list() == [2.0, 3.0, 4.0, 5.0, 6.0]
    assert cell[0][0] is history

def test_a_start_without_a_published_history_reads_its_own(monkeypatch):
    history = pl.DataFrame({"Timestamp": [4, 5], "Close": [4.0, 5.0]})
    reads = []
    def before(cls, db, security, timeframe, stop, count, **kwargs):
        reads.append((stop, count))
        return SimpleNamespace(materialize=lambda bars, timeframe: history), None
    monkeypatch.setattr(TapeAPI, "before", classmethod(before))
    engine = _preload_stub_(3)
    engine._history_, engine._db_, engine._readers_, engine._shelf_ = {datetime(2020, 1, 1): (history, 5)}, None, 1, {}
    assert engine._load_warmup_(pl.DataFrame({"Timestamp": [6], "Close": [6.0]}), None, [None])["Close"].to_list() == [4.0, 5.0, 6.0]
    assert reads == [(engine._start_, 2)]

def test_extract_inject_round_trips_state():
    ticks = TapeAPI.empty(1)
    bars = [object()]
    source = _preload_stub_()
    source._dataset_ = _dataset_(ExecutionBars=bars, Ticks=ticks)
    target = _preload_stub_()
    target.inject(source.extract())
    target._preload_()
    assert target._dataset_ is source._dataset_
    assert target._dataset_.ExecutionBars is bars
    assert target._dataset_.Ticks is ticks

def test_auto_fee_types_resolve_to_accurate():
    engine = BacktestingAPI(
        strategy=type("Strategy", (), {}),
        security=object(),
        timeframe=object(),
        resolution=MISSING,
        parameters=object(),
        start="2023-01-01",
        stop="2024-01-01",
        account=("EUR", 10000.0, 30.0),
        spread=(SpreadType.Auto, MISSING),
        commission=(CommissionType.Auto, MISSING),
        swap=(SwapType.Auto, MISSING, MISSING),
        report=False,
        export=False
    )
    assert engine._spread_type_ == SpreadType.Accurate
    assert engine._commission_type_ == CommissionType.Accurate
    assert engine._swap_type_ == SwapType.Accurate
    assert engine._resolution_arg_ is MISSING

def _artifact_stub_(report=False, export=False, plot=False) -> BacktestingAPI:
    engine = object.__new__(BacktestingAPI)
    engine._reporting_, engine._exporting_, engine._plotting_ = report, export, plot
    engine._log_ = LoggingAPI()
    return engine

def test_deliverables_scopes_the_flags_and_restores_them():
    engine = _artifact_stub_()
    with engine.deliverables(True, True, False):
        assert (engine._reporting_, engine._exporting_, engine._plotting_) == (True, True, False)
    assert (engine._reporting_, engine._exporting_, engine._plotting_) == (False, False, False)

def test_deliverables_restores_even_when_the_block_raises():
    engine = _artifact_stub_()
    with pytest.raises(RuntimeError):
        with engine.deliverables(True, True, True): raise RuntimeError("boom")
    assert (engine._reporting_, engine._exporting_, engine._plotting_) == (False, False, False)

def test_quieted_lowers_both_sinks_when_nothing_is_delivered():
    engine = _artifact_stub_()
    console, file = engine._log_.console.Level, engine._log_.file.Level
    with engine.quieted():
        assert engine._log_.console.Level == VerboseLevel.Warning
        assert engine._log_.file.Level == VerboseLevel.Warning
    assert (engine._log_.console.Level, engine._log_.file.Level) == (console, file)

def test_quieted_stays_transparent_while_delivering():
    engine = _artifact_stub_(report=True)
    console, file = engine._log_.console.Level, engine._log_.file.Level
    with engine.quieted():
        assert (engine._log_.console.Level, engine._log_.file.Level) == (console, file)

def test_a_worker_payload_carries_the_contract_and_the_worker_pins_it(monkeypatch):
    from types import SimpleNamespace
    from Library.Universe.Contract import ContractAPI
    from Library.Universe.Security import SecurityAPI
    from Library.Universe.Ticker import ContractType
    import Library.System.Backtesting as module
    parent = SecurityAPI(Ticker="EURUSD", Provider="Spotware(cTrader)", Type=ContractType.Spot, Contract=ContractAPI(SwapLong=-9.0)).Contract
    engine = SimpleNamespace(_strategy_="Trend", _security_=SimpleNamespace(_provider_=parent._owner_.Provider, _ticker_=parent._owner_.Ticker, Contract=parent), _timeframe_=SimpleNamespace(UID="H1"),
                             _account_asset_="EUR", _bridge_=MISSING, _account_balance_=10000.0, _account_leverage_=30.0, _spread_type_=SpreadType.Accurate, _spread_value_=None,
                             _commission_type_=CommissionType.Accurate, _commission_value_=None, _swap_type_=SwapType.Accurate, _swap_long_=None, _swap_short_=None, _risk_free_=0.02)
    payload = BacktestingAPI._dispatch_(engine, SimpleNamespace(data={}), datetime(2023, 1, 1), datetime(2024, 1, 1))
    assert payload["contract"] == parent.snapshot() and payload["risk_free"] == 0.02
    stored = SecurityAPI(Ticker="EURUSD", Provider="Spotware(cTrader)", Type=ContractType.Spot, Contract=ContractAPI(SwapLong=-2.445)).Contract
    class _Database_:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *exc): return False
    monkeypatch.setattr(module, "PostgresDatabaseAPI", _Database_)
    monkeypatch.setattr(module, "SecurityAPI", lambda **kwargs: SimpleNamespace(Contract=stored))
    monkeypatch.setattr(module, "TimeframeAPI", lambda **kwargs: SimpleNamespace(UID=kwargs["UID"]))
    security, timeframe = BacktestingAPI._resolve_(payload)
    assert security.Contract.SwapLong == -9.0 and timeframe.UID == "H1"