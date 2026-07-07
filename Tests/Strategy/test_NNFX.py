from types import SimpleNamespace

from Library.Parameter import Parameter
from Library.Protocol.Action import CloseBuyPositionActionAPI
from Library.Protocol.Update import UpdateID
from Library.Strategy.Rule.NNFX import NNFXStrategyAPI

def _indicator_(value):
    return SimpleNamespace(Result=SimpleNamespace(last=lambda: value))

def _position_(volume, long, uid=1):
    return SimpleNamespace(Volume=volume, IsLong=long, IsShort=not long, UID=uid)

def _update_(buys=None, sells=None, drawdown=0.0, atr=0.01, close=1.0):
    technical = SimpleNamespace(ATR=_indicator_(atr))
    bar = SimpleNamespace(CloseTick=SimpleNamespace(Bid=SimpleNamespace(Price=close)))
    portfolio = SimpleNamespace(
        BuyPositions=buys or [],
        SellPositions=sells or [],
        Account=SimpleNamespace(Balance=10000.0),
        EquityDrawdown=drawdown,
        Security=SimpleNamespace(Contract=SimpleNamespace(VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=100000.0, PipSize=0.0001, PointSize=0.00001))
    )
    return SimpleNamespace(Bar=bar, Technical=technical, Portfolio=portfolio)

def _strategy_(time_stop=0, threshold=0.0, factor=1.0, mode="Risk", maximum=2.0):
    money = Parameter({"SizingMode": [mode], "SizingMax": [maximum], "DrawdownThreshold": [threshold], "DrawdownFactor": [factor]}, ".")
    risk = Parameter({"StopLossScale": [1.5], "ScalingOutScale": [1.0], "ScalingOutPercentage": [50.0], "TrailingStopLossScale": [1.5], "TrailingStopLossStep": [0.25], "StagnationStopOut": [time_stop]}, ".")
    empty = Parameter({}, ".")
    return NNFXStrategyAPI(money_management=money, risk_management=risk, signal_management=empty)

def test_risk_scale_off_by_default():
    strategy = _strategy_()
    assert strategy._risk_scale_(_update_(drawdown=-0.5)) == 1.0

def test_risk_scale_cuts_risk_beyond_drawdown_threshold():
    strategy = _strategy_(threshold=10.0, factor=0.5)
    assert strategy._risk_scale_(_update_(drawdown=-0.05)) == 1.0
    assert strategy._risk_scale_(_update_(drawdown=-0.15)) == 0.5

def test_drawdown_halves_position_volume():
    strategy = _strategy_(threshold=10.0, factor=0.5)
    full, sl_pips = strategy.calculate_position(_update_(drawdown=0.0))
    halved, _ = strategy.calculate_position(_update_(drawdown=-0.15))
    assert sl_pips == 150.0 and full == 13000.0 and halved == 6000.0

def test_risk_mode_sizes_by_stop_distance():
    strategy = _strategy_(mode="Risk", maximum=2.0)
    volume, sl_pips = strategy.calculate_position(_update_(atr=0.01))
    assert sl_pips == 150.0 and volume == 13000.0

def test_volume_mode_uses_fixed_units():
    strategy = _strategy_(mode="Volume", maximum=5000.0)
    volume, sl_pips = strategy.calculate_position(_update_(atr=0.01))
    assert sl_pips == 150.0 and volume == 5000.0

def test_balance_mode_uses_percent_of_balance_notional():
    strategy = _strategy_(mode="Balance", maximum=50.0)
    volume, _ = strategy.calculate_position(_update_(atr=0.01, close=1.0))
    assert volume == 5000.0

def test_drawdown_scaling_applies_across_modes():
    strategy = _strategy_(mode="Volume", maximum=6000.0, threshold=10.0, factor=0.5)
    full, _ = strategy.calculate_position(_update_(drawdown=0.0))
    cut, _ = strategy.calculate_position(_update_(drawdown=-0.15))
    assert full == 6000.0 and cut == 3000.0

def test_time_stop_closes_after_configured_bars():
    strategy = _strategy_(time_stop=3)
    strategy._last_position_id_ = 7
    strategy._last_position_atr_ = 0.01
    strategy.define_so_buy_action(SimpleNamespace(Position=SimpleNamespace(UID=7, EntryPrice=SimpleNamespace(Price=1.10))))
    update = _update_(buys=[_position_(5000.0, True, uid=7)])
    assert strategy.stagnation_stop_out_action(update) == []
    assert strategy.stagnation_stop_out_action(update) == []
    actions = strategy.stagnation_stop_out_action(update)
    assert len(actions) == 1 and isinstance(actions[0], CloseBuyPositionActionAPI) and actions[0].PositionID == 7

def test_time_stop_counter_resets_on_new_position():
    strategy = _strategy_(time_stop=3)
    strategy._position_bars_held_ = 2
    strategy._last_position_atr_ = 0.01
    strategy.define_so_buy_action(SimpleNamespace(Position=SimpleNamespace(UID=8, EntryPrice=SimpleNamespace(Price=1.10))))
    assert strategy._position_bars_held_ == 0

def test_machine_gains_bar_transition_only_when_enabled():
    enabled = _strategy_(time_stop=3).risk_management()
    disabled = _strategy_(time_stop=0).risk_management()
    assert enabled.state(name="Waiting SO")._transitions_[UpdateID.BarClosed.value] is not None
    assert disabled.state(name="Waiting SO")._transitions_[UpdateID.BarClosed.value] is None

def test_pure_tsl_when_scaling_out_disabled():
    money = Parameter({"SizingMode": ["Risk"], "SizingMax": [2.0], "DrawdownThreshold": [0.0], "DrawdownFactor": [1.0]}, ".")
    risk = Parameter({"StopLossScale": [1.5], "ScalingOutScale": [1.0], "ScalingOutPercentage": [0.0], "TrailingStopLossScale": [1.5], "TrailingStopLossStep": [0.25], "StagnationStopOut": [0]}, ".")
    strategy = NNFXStrategyAPI(money_management=money, risk_management=risk, signal_management=Parameter({}, "."))
    engine = strategy.risk_management()
    transition = engine.state(name="No Position")._transitions_[UpdateID.OpenedBuyPosition.value]
    assert transition.To.Name == "Waiting TSL"
    strategy._last_position_atr_ = 0.01
    update = SimpleNamespace(Position=SimpleNamespace(UID=4, StopLossPrice=SimpleNamespace(Price=1.0850)), Portfolio=SimpleNamespace(Security=SimpleNamespace(Contract=SimpleNamespace(PointSize=0.00001))))
    actions = strategy.define_tsl_open_buy_action(update)
    assert abs(actions[0].Bid - (1.0850 + 1.75 * 0.01 + 0.00001)) < 1e-12