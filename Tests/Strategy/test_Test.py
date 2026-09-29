import pytest

from types import SimpleNamespace

from Library.Market.Price import Direction
from Library.Portfolio.Position import PositionType
from Library.Protocol.Action import (
    AskBelowTargetActionAPI,
    BidAboveTargetActionAPI,
    CloseBuyPositionActionAPI,
    CloseSellPositionActionAPI,
    IncreaseBuyPositionVolumeActionAPI,
    ModifyBuyPositionVolumeActionAPI,
    ModifyBuyPositionStopLossActionAPI,
    ModifyBuyPositionTakeProfitActionAPI,
    ModifySellPositionStopLossActionAPI,
    OpenBuyPositionActionAPI,
    OpenSellPositionActionAPI
)
from Library.Strategy.Catalog import CatalogAPI
from Library.Strategy.Rule.Test import ScenarioType
from Library.Strategy.Strategy import StrategyType
from Library.Utility.Parameter import Parameter

def _indicator_(value):
    return SimpleNamespace(Result=SimpleNamespace(last=lambda: value))

def _position_(uid, volume=10000.0, take_profit=None, direction=Direction.Buy):
    return SimpleNamespace(UID=uid, Direction=direction, Volume=volume, TakeProfitPrice=SimpleNamespace(Price=take_profit) if take_profit is not None else None)

def _update_(buys=(), sells=(), atr=0.001):
    contract = SimpleNamespace(VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=10000000.0, PipSize=0.0001, PointSize=0.00001)
    bar = SimpleNamespace(ClosePoint=SimpleNamespace(Bid=SimpleNamespace(Price=1.1), Ask=SimpleNamespace(Price=1.1001), BidTick=SimpleNamespace(BidBaseConversion=SimpleNamespace(Price=1.0), BidQuoteConversion=SimpleNamespace(Price=1.0))))
    portfolio = SimpleNamespace(BuyPositions=list(buys), SellPositions=list(sells), Account=SimpleNamespace(Balance=10000.0), EquityDrawdown=0.0, Security=SimpleNamespace(Contract=contract))
    return SimpleNamespace(Bar=bar, Technical=SimpleNamespace(ATR=_indicator_(atr)), Portfolio=portfolio)

def _strategy_():
    strategy = CatalogAPI.CATALOG["Test"]
    sections = strategy.defaults("Realtime")
    parameter = lambda name: Parameter(sections[name] or {}, ".")
    return strategy(parameter("MoneyManagement"), parameter("RiskManagement"), parameter("SignalManagement"), parameter("TechnicalManagement"), parameter("FundamentalManagement"), parameter("SentimentalManagement"), parameter("PortfolioManagement"))

def _drive_(strategy, update):
    strategy._signal_position_ = lambda _: None
    return strategy.update_position(update)

def test_test_is_registered():
    assert StrategyType.Test.value == 5 and CatalogAPI.resolve("Test").key() == "Test"

def test_entries_rotate_through_every_scenario():
    strategy, update = _strategy_(), _update_()
    seen = []
    for _ in range(5):
        strategy.open_buy_position(update, PositionType.Normal)
        seen.append(strategy._scenario_)
    assert seen == [ScenarioType.Plain, ScenarioType.Target, ScenarioType.Resize, ScenarioType.Hedge, ScenarioType.Plain]

def test_target_entry_sets_and_widens_take_profit():
    strategy, update = _strategy_(), _update_()
    strategy.open_buy_position(update, PositionType.Normal)
    actions = strategy.open_buy_position(update, PositionType.Normal)
    assert isinstance(actions[-1], OpenBuyPositionActionAPI) and actions[-1].StopLoss == pytest.approx(15.0) and actions[-1].TakeProfit == pytest.approx(30.0)
    widened = _drive_(strategy, _update_(buys=[_position_(4, take_profit=1.1030)]))
    assert isinstance(widened[0], ModifyBuyPositionTakeProfitActionAPI) and widened[0].PositionID == 4 and widened[0].TakeProfit == pytest.approx(1.1040)
    assert not strategy._steps_

def test_resize_entry_increases_then_modifies_volume():
    strategy, update = _strategy_(), _update_()
    for _ in range(3): strategy.open_buy_position(update, PositionType.Normal)
    half = strategy._half_(update)
    increased = _drive_(strategy, _update_(buys=[_position_(9, volume=strategy._volume_)]))
    assert isinstance(increased[0], IncreaseBuyPositionVolumeActionAPI) and increased[0].Volume == pytest.approx(strategy._volume_ + half)
    modified = _drive_(strategy, _update_(buys=[_position_(9, volume=strategy._volume_ + half)]))
    assert isinstance(modified[0], ModifyBuyPositionVolumeActionAPI) and modified[0].Volume == pytest.approx(strategy._volume_ + 2 * half)

def test_hedge_entry_adds_same_side_then_opposite_then_closes_opposite():
    strategy, update = _strategy_(), _update_()
    for _ in range(4): strategy.open_sell_position(update, PositionType.Normal)
    primary = _position_(3)
    same = _drive_(strategy, _update_(sells=[primary]))
    assert isinstance(same[0], OpenSellPositionActionAPI) and same[0].PositionType == PositionType.Continuation and same[0].TakeProfit == pytest.approx(30.0)
    opposite = _drive_(strategy, _update_(sells=[primary, _position_(5)]))
    assert isinstance(opposite[0], OpenBuyPositionActionAPI) and opposite[0].StopLoss == pytest.approx(15.0)
    closed = _drive_(strategy, _update_(sells=[primary, _position_(5)], buys=[_position_(6), _position_(7)]))
    assert [(type(action), action.PositionID) for action in closed] == [(CloseBuyPositionActionAPI, 6), (CloseBuyPositionActionAPI, 7)]

def test_steps_stop_once_the_primary_is_gone():
    strategy, update = _strategy_(), _update_()
    for _ in range(4): strategy.open_buy_position(update, PositionType.Normal)
    assert _drive_(strategy, _update_()) is None and not strategy._steps_

def test_close_reaches_every_position_of_the_side():
    strategy = _strategy_()
    actions = strategy.close_sell_position(_update_(sells=[_position_(2), _position_(8)]))
    assert [(type(action), action.PositionID) for action in actions] == [(CloseSellPositionActionAPI, 2), (CloseSellPositionActionAPI, 8)]

def test_break_even_only_when_the_stop_would_be_valid():
    strategy = _strategy_()
    strategy._last_position_id_ = 3
    losing = SimpleNamespace(Position=SimpleNamespace(EntryPrice=SimpleNamespace(Price=1.1000)), Trade=SimpleNamespace(ExitPrice=SimpleNamespace(Price=1.1005)))
    winning = SimpleNamespace(Position=SimpleNamespace(EntryPrice=SimpleNamespace(Price=1.1000)), Trade=SimpleNamespace(ExitPrice=SimpleNamespace(Price=1.0990)))
    assert strategy.breakeven_sell_action(losing) == []
    actions = strategy.breakeven_sell_action(winning)
    assert isinstance(actions[0], ModifySellPositionStopLossActionAPI) and actions[0].StopLoss == pytest.approx(1.1000)
def test_each_direction_rotates_on_its_own():
    strategy, update = _strategy_(), _update_()
    seen = []
    for _ in range(4):
        strategy.open_buy_position(update, PositionType.Normal)
        seen.append(strategy._scenario_)
        strategy.open_sell_position(update, PositionType.Normal)
        seen.append(strategy._scenario_)
    assert seen == [scenario for scenario in ScenarioType for _ in range(2)]

def test_a_reset_disarms_both_targets():
    strategy = _strategy_()
    for actions in (strategy.undefine_tsl_buy_action(None), strategy.undefine_tsl_sell_action(None)):
        assert [(type(action), action.Bid if isinstance(action, BidAboveTargetActionAPI) else action.Ask) for action in actions] == [(BidAboveTargetActionAPI, None), (AskBelowTargetActionAPI, None)]

def test_no_trailing_or_widening_once_the_target_is_reached():
    strategy = _strategy_()
    strategy._last_position_id_, strategy._last_position_atr_ = 16, 0.00265
    position = SimpleNamespace(UID=16, Direction=Direction.Buy, TakeProfitPrice=SimpleNamespace(Price=1.07077))
    tick = lambda bid: SimpleNamespace(Tick=SimpleNamespace(Bid=SimpleNamespace(Price=bid), Ask=SimpleNamespace(Price=bid + 0.00002)), Portfolio=SimpleNamespace(position=lambda uid: position))
    assert strategy.detected_tsl_buy_action(tick(1.07086)) == []
    assert isinstance(strategy.detected_tsl_buy_action(tick(1.07067))[0], ModifyBuyPositionStopLossActionAPI)
    strategy._direction_ = Direction.Buy
    closed = lambda bid: SimpleNamespace(Bar=SimpleNamespace(ClosePoint=SimpleNamespace(Bid=SimpleNamespace(Price=bid), Ask=SimpleNamespace(Price=bid + 0.00002))))
    assert strategy._widen_target_(closed(1.07080), position) == []
    assert isinstance(strategy._widen_target_(closed(1.07000), position)[0], ModifyBuyPositionTakeProfitActionAPI)