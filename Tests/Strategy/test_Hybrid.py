from datetime import datetime
from types import SimpleNamespace

from Library.Database.Dataframe import np
from Library.Engine import MachineAPI
from Library.Parameter import Parameter
from Library.Protocol.Action import (
    CloseBuyPositionActionAPI,
    CloseSellPositionActionAPI,
    OpenBuyPositionActionAPI,
    OpenSellPositionActionAPI
)
from Library.Strategy.Hybrid import (
    HybridModelStrategyAPI,
    HybridDDPGStrategyAPI,
    HybridRDDPGStrategyAPI,
    HybridSACStrategyAPI,
    HybridTD3StrategyAPI
)
from Library.Strategy.Strategy import StrategyType

class _FakeAgent_:

    def __init__(self, action=0.0):
        self._action_ = np.array([action], dtype=np.float32)

    def decide(self, state, explore=True):
        return self._action_

    def memorize(self, *args):
        pass

    def learn(self):
        pass

    def reset(self):
        pass

class _FakeHybridStrategy_(HybridModelStrategyAPI):

    def _create_agent_(self, observation_shape, action_shape):
        self.observation_shape = observation_shape
        return _FakeAgent_()

def _indicator_(value):
    return SimpleNamespace(Result=SimpleNamespace(last=lambda: value))

def _position_(volume, long, uid=1):
    return SimpleNamespace(Volume=volume, IsLong=long, IsShort=not long, UID=uid, EntryBalance=10000.0, NetPnL=SimpleNamespace(PnL=0.0), MaxEquityDrawdownPnL=SimpleNamespace(PnL=0.0), MaxEquityRunupPnL=SimpleNamespace(PnL=0.0))

def _update_(buys=None, sells=None, close=1.11, atr=0.01):
    technical = SimpleNamespace(ATR=_indicator_(atr), RVFast=_indicator_(0.008))
    bar = SimpleNamespace(
        Timestamp=SimpleNamespace(DateTime=datetime(2020, 6, 15, 13, 30, 0)),
        OpenTick=SimpleNamespace(Bid=SimpleNamespace(Price=1.10)),
        HighTick=SimpleNamespace(Bid=SimpleNamespace(Price=1.13)),
        LowTick=SimpleNamespace(Bid=SimpleNamespace(Price=1.09)),
        CloseTick=SimpleNamespace(Bid=SimpleNamespace(Price=close)),
        Volume=5000.0
    )
    portfolio = SimpleNamespace(
        BuyPositions=buys or [],
        SellPositions=sells or [],
        Account=SimpleNamespace(Balance=10000.0),
        InitialBalance=10000.0,
        Equity=10000.0,
        EquityDrawdown=0.0,
        EquityRunup=0.0,
        Security=SimpleNamespace(Contract=SimpleNamespace(VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=100000.0, PipSize=0.0001, PointSize=0.00001))
    )
    return SimpleNamespace(Bar=bar, Technical=technical, Portfolio=portfolio)

def _strategy_(sizing_min=0.5, sizing_max=2.0, entry=(-0.4, 0.4), exit=(-0.1, 0.1), delay=0):
    money = Parameter({"SizingMode": ["Risk"], "SizingMin": [sizing_min], "SizingMax": [sizing_max]}, ".")
    signal = Parameter({"NormalEntryThreshold": list(entry), "NormalExitThreshold": list(exit), "ContinuationDelay": [delay]}, ".")
    risk = Parameter({"StopLossScale": [1.5], "ScalingOutScale": [1.0], "ScalingOutPercentage": [50.0], "TrailingStopLossScale": [1.5], "TrailingStopLossStep": [0.25]}, ".")
    empty = Parameter({}, ".")
    return _FakeHybridStrategy_(money_management=money, risk_management=risk, signal_management=signal)

def test_strategy_type_registers_hybrids():
    assert StrategyType.HybridDDPG.value == 7
    assert StrategyType.HybridRDDPG.value == 8
    assert StrategyType.HybridSAC.value == 9
    assert StrategyType.HybridTD3.value == 10

def test_strong_long_signal_opens_buy_with_nnfx_sizing():
    strategy = _strategy_()
    actions = strategy._control_(_update_(), 0.7)
    assert len(actions) == 1 and isinstance(actions[0], OpenBuyPositionActionAPI)
    assert actions[0].StopLoss == 150.0
    assert actions[0].Volume == 8000.0

def test_strong_short_signal_opens_sell():
    strategy = _strategy_()
    actions = strategy._control_(_update_(), -1.0)
    assert len(actions) == 1 and isinstance(actions[0], OpenSellPositionActionAPI)
    assert actions[0].Volume == 13000.0

def test_hold_band_is_silent_flat_and_in_position():
    strategy = _strategy_()
    assert strategy._control_(_update_(), 0.25) is None
    assert strategy._control_(_update_(buys=[_position_(5000.0, True)]), 0.25) is None
    assert strategy._control_(_update_(buys=[_position_(5000.0, True)]), 0.7) is None

def test_deadzone_signal_closes_open_position():
    strategy = _strategy_()
    strategy._last_position_id_ = 9
    actions = strategy._control_(_update_(buys=[_position_(5000.0, True, uid=9)]), 0.05)
    assert len(actions) == 1 and isinstance(actions[0], CloseBuyPositionActionAPI) and actions[0].PositionID == 9

def test_strong_opposite_signal_reverses():
    strategy = _strategy_()
    strategy._last_position_id_ = 3
    actions = strategy._control_(_update_(buys=[_position_(5000.0, True, uid=3)]), -0.9)
    assert len(actions) == 2
    assert isinstance(actions[0], CloseBuyPositionActionAPI) and actions[0].PositionID == 3
    assert isinstance(actions[1], OpenSellPositionActionAPI)

def test_confidence_maps_risk_between_min_and_max():
    strategy = _strategy_(sizing_min=0.5, sizing_max=2.0)
    strategy._hybrid_confidence_ = 0.4
    assert abs(strategy._entry_risk_percentage_(_update_()) - 0.5) < 1e-12
    strategy._hybrid_confidence_ = 1.0
    assert abs(strategy._entry_risk_percentage_(_update_()) - 2.0) < 1e-12
    strategy._hybrid_confidence_ = 0.7
    assert abs(strategy._entry_risk_percentage_(_update_()) - 1.25) < 1e-12
    strategy._hybrid_confidence_ = -1.0
    assert abs(strategy._entry_risk_percentage_(_update_()) - 2.0) < 1e-12
    strategy._hybrid_confidence_ = -0.7
    assert abs(strategy._entry_risk_percentage_(_update_()) - 1.25) < 1e-12

def test_fixed_risk_when_min_equals_max():
    strategy = _strategy_(sizing_min=2.0, sizing_max=2.0)
    strategy._hybrid_confidence_ = 0.4
    assert strategy._entry_risk_percentage_(_update_()) == 2.0
    strategy._hybrid_confidence_ = 1.0
    assert strategy._entry_risk_percentage_(_update_()) == 2.0

def test_reentry_waits_for_delay_then_continues():
    strategy = _strategy_(delay=5)
    opened = strategy._control_(_update_(), 0.7)
    assert isinstance(opened[0], OpenBuyPositionActionAPI)
    assert strategy._control_(_update_(), 0.7) is None
    assert strategy._control_(_update_(), 0.9) is None
    assert strategy._control_(_update_(), 0.2) is None
    reopened = strategy._control_(_update_(), 0.7)
    assert reopened[0].PositionType.name == "Normal"

def test_reversal_allowed_while_disarmed():
    strategy = _strategy_()
    strategy._control_(_update_(), 0.7)
    strategy._last_position_id_ = 5
    actions = strategy._control_(_update_(buys=[_position_(5000.0, True, uid=5)]), -0.8)
    assert len(actions) == 2 and isinstance(actions[1], OpenSellPositionActionAPI)

def test_continuation_reenters_after_machine_exit_with_cooldown():
    strategy = _strategy_(delay=2)
    opened = strategy._control_(_update_(buys=None), 0.7)
    assert opened[0].PositionType.name == "Normal"
    position = [_position_(5000.0, True, uid=1)]
    assert strategy._control_(_update_(buys=position), 0.7) is None
    assert strategy._control_(_update_(), 0.7) is None
    continuation = strategy._control_(_update_(), 0.7)
    assert isinstance(continuation[0], OpenBuyPositionActionAPI) and continuation[0].PositionType.name == "Continuation"

def test_continuation_immediate_when_delay_zero():
    strategy = _strategy_()
    strategy._control_(_update_(), 0.7)
    continuation = strategy._control_(_update_(), 0.7)
    assert continuation[0].PositionType.name == "Continuation"

def test_model_exit_rearms_and_next_entry_is_normal():
    strategy = _strategy_(delay=1)
    strategy._control_(_update_(), 0.7)
    strategy._last_position_id_ = 2
    closed = strategy._control_(_update_(buys=[_position_(5000.0, True, uid=2)]), 0.05)
    assert isinstance(closed[0], CloseBuyPositionActionAPI)
    assert strategy._continuation_direction_ == 0
    reopened = strategy._control_(_update_(), 0.7)
    assert reopened[0].PositionType.name == "Normal"

def test_reversal_resets_continuation_legs():
    strategy = _strategy_(delay=1)
    strategy._control_(_update_(), 0.7)
    continuation = strategy._control_(_update_(), 0.7)
    assert continuation[0].PositionType.name == "Continuation"
    reversal = strategy._control_(_update_(), -0.8)
    assert isinstance(reversal[0], OpenSellPositionActionAPI) and reversal[0].PositionType.name == "Normal"
    assert strategy._continuation_direction_ == -1

def test_risk_and_signal_machines_present():
    strategy = _strategy_()
    assert isinstance(strategy.risk_management(), MachineAPI)
    assert isinstance(strategy.signal_management(), MachineAPI)

def test_concrete_hybrids_build_agents_with_observation_shape():
    from Library.Model import DDPGAgentAPI, SACAgentAPI, TD3AgentAPI
    money = Parameter({"SizingMode": ["Risk"], "SizingMin": [0.5], "SizingMax": [2.0]}, ".")
    signal = Parameter({"NormalEntryThreshold": [-0.4, 0.4], "NormalExitThreshold": [-0.1, 0.1]}, ".")
    risk = Parameter({"StopLossScale": [1.5], "ScalingOutScale": [1.0], "ScalingOutPercentage": [50.0], "TrailingStopLossScale": [1.5], "TrailingStopLossStep": [0.25]}, ".")
    empty = Parameter({}, ".")
    ddpg = HybridDDPGStrategyAPI(money_management=money, risk_management=risk, signal_management=signal)
    extended = HybridRDDPGStrategyAPI(money_management=money, risk_management=risk, signal_management=signal)
    sac = HybridSACStrategyAPI(money_management=money, risk_management=risk, signal_management=signal)
    td3 = HybridTD3StrategyAPI(money_management=money, risk_management=risk, signal_management=signal)
    assert isinstance(ddpg._agent_, DDPGAgentAPI) and isinstance(sac._agent_, SACAgentAPI) and isinstance(td3._agent_, TD3AgentAPI)
    assert ddpg._agent_.actor_regularization == 0.0 and extended._agent_.actor_regularization == 0.001
    assert ddpg._observation_.shape() == 29