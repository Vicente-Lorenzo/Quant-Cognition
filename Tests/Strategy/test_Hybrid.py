import math
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
from Library.Strategy.Hybrid.DDPG import DDPGStrategyAPI
from Library.Strategy.Model.Reward import RewardType
from Library.Strategy.Strategy import StrategyType

class _FakeAgent_:

    def __init__(self, action=0.0):
        self._action_ = np.array([action], dtype=np.float32)
        self.transitions = []
        self.learned = 0
        self.resets = 0

    def decide(self, state, explore=True):
        return self._action_

    def memorize(self, state, action, reward, next_state, done):
        self.transitions.append((state, action, reward, next_state, done))

    def learn(self):
        self.learned += 1

    def reset(self):
        self.resets += 1

class _FakeDDPG_(DDPGStrategyAPI):

    def _create_agent_(self, observation_shape, action_shape):
        return _FakeAgent_(self.Fake)

def _technical_():
    return Parameter({"ATR": ["ATR", 14], "RVFast": ["RV", 16], "RVSlow": ["RV", 63], "MOMFast": ["ROC", 5], "MOMMedium": ["ROC", 21], "MOMSlow": ["ROC", 63]}, ".")

def _indicator_(value):
    return SimpleNamespace(Result=SimpleNamespace(last=lambda: value))

def _position_(volume, long, uid=1):
    return SimpleNamespace(Volume=volume, IsLong=long, IsShort=not long, UID=uid, EntryBalance=10000.0, NetPnL=SimpleNamespace(PnL=0.0), MaxEquityDrawdownPnL=SimpleNamespace(PnL=0.0), MaxEquityRunupPnL=SimpleNamespace(PnL=0.0))

def _update_(buys=None, sells=None, close=1.11, atr=0.01, equity=10000.0):
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
        Equity=equity,
        EquityDrawdown=0.0,
        EquityRunup=0.0,
        Security=SimpleNamespace(Contract=SimpleNamespace(VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=100000.0, PipSize=0.0001, PointSize=0.00001))
    )
    return SimpleNamespace(Bar=bar, Technical=technical, Portfolio=portfolio)

def _strategy_(sizing_min=0.5, sizing_max=2.0, entry=(-0.4, 0.4), exit=(-0.1, 0.1), delay=0, action=0.0, training=False, neutralize=False):
    _FakeDDPG_.Fake = action
    _FakeDDPG_.Agent = None
    _FakeDDPG_.Training = training
    _FakeDDPG_.Reward = RewardType.LogReturn
    _FakeDDPG_.RewardScale = 1.0
    money = Parameter({"SizingMode": ["Risk"], "SizingMin": [sizing_min], "SizingMax": [sizing_max], "DrawdownThreshold": [0.0], "DrawdownFactor": [1.0]}, ".")
    risk = Parameter({"StopLossScale": [1.5], "StagnationStopLoss": [0], "ScalingOutScale": [1.0], "ScalingOutPercentage": [50.0], "TrailingStopLossScale": [1.5], "TrailingStopLossStep": [0.25]}, ".")
    signal = Parameter({"NormalEntryThreshold": list(entry), "NormalExitThreshold": list(exit), "ContinuationEntryThreshold": list(entry), "ContinuationExitThreshold": list(exit), "ContinuationDelay": [delay], "ObservationWindow": [1], "NormalizeWindow": [200], "NeutralizeReward": [neutralize]}, ".")
    return _FakeDDPG_(money_management=money, risk_management=risk, signal_management=signal, technical_management=_technical_(), fundamental_management=Parameter({}, "."), sentimental_management=Parameter({}, "."), portfolio_management=Parameter({}, "."))

def test_strategy_type_registers_four_strategies():
    assert StrategyType.Download.value == 1
    assert StrategyType.NNFX.value == 2
    assert StrategyType.Trend.value == 3
    assert StrategyType.DDPG.value == 4

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

def test_step_records_transition_reward_and_learns():
    strategy = _strategy_(action=0.5, training=True)
    strategy._step_(_update_(equity=10000.0))
    assert strategy._agent_.transitions == []
    strategy._step_(_update_(equity=10050.0))
    assert len(strategy._agent_.transitions) == 1
    _, _, reward, _, done = strategy._agent_.transitions[0]
    assert abs(reward - math.log(10050.0 / 10000.0)) < 1e-9 and done is False
    assert strategy._agent_.learned >= 1

def test_step_does_not_record_when_not_training():
    strategy = _strategy_(action=0.5, training=False)
    strategy._step_(_update_(equity=10000.0))
    strategy._step_(_update_(equity=10100.0))
    assert strategy._agent_.transitions == [] and strategy._agent_.learned == 0

def test_neutral_reward_off_by_default_matches_raw_log_return():
    strategy = _strategy_(action=0.5, training=True)
    assert strategy._neutralize_reward_ is False
    strategy._step_(_update_(equity=10000.0, sells=[_position_(10000.0, False)]))
    strategy._step_(_update_(equity=10100.0, close=1.089))
    _, _, reward, _, _ = strategy._agent_.transitions[0]
    assert abs(reward - math.log(10100.0 / 10000.0)) < 1e-9

def test_neutral_reward_subtracts_held_exposure_times_market_return():
    strategy = _strategy_(action=0.5, training=True, neutralize=True)
    assert strategy._neutralize_reward_ is True
    strategy._step_(_update_(equity=10000.0, close=1.10, sells=[_position_(10000.0, False)]))
    assert abs(strategy._previous_exposure_ - (-1.10)) < 1e-9
    strategy._step_(_update_(equity=10100.0, close=1.089))
    _, _, reward, _, _ = strategy._agent_.transitions[0]
    hedge = -1.10 * math.log(1.089 / 1.10)
    assert abs(reward - (math.log(10100.0 / 10000.0) - hedge)) < 1e-9

def test_neutral_reward_flat_bar_has_no_hedge():
    strategy = _strategy_(action=0.5, training=True, neutralize=True)
    strategy._step_(_update_(equity=10000.0, close=1.10))
    assert strategy._previous_exposure_ == 0.0
    strategy._step_(_update_(equity=10000.0, close=1.089))
    _, _, reward, _, _ = strategy._agent_.transitions[0]
    assert reward == 0.0

def test_initialize_resets_episode_state():
    strategy = _strategy_(action=0.5, training=True)
    strategy._step_(_update_())
    strategy._initialize_(None)
    assert strategy._previous_observation_ is None
    assert strategy._previous_action_ is None
    assert strategy._previous_equity_ is None
    assert strategy._agent_.resets == 1

def test_ddpg_builds_agent_and_regularization_is_parameter_driven():
    from Library.Model import DDPGAgentAPI
    DDPGStrategyAPI.Agent = None
    DDPGStrategyAPI.Training = False
    money = Parameter({"SizingMode": ["Risk"], "SizingMin": [0.5], "SizingMax": [2.0], "DrawdownThreshold": [0.0], "DrawdownFactor": [1.0]}, ".")
    risk = Parameter({"StopLossScale": [1.5], "StagnationStopLoss": [0], "ScalingOutScale": [1.0], "ScalingOutPercentage": [50.0], "TrailingStopLossScale": [1.5], "TrailingStopLossStep": [0.25]}, ".")
    agent = {"ActorLearningRate": [0.0001], "CriticLearningRate": [0.001], "SoftUpdate": [0.001], "HiddenShape1": [400], "HiddenShape2": [300], "MemorySize": [1000000], "BatchSize": [64], "DiscountFactor": [0.99], "GradientClip": [1.0]}
    common = {"NormalEntryThreshold": [-0.4, 0.4], "NormalExitThreshold": [-0.1, 0.1], "ContinuationEntryThreshold": [-2.0, 2.0], "ContinuationExitThreshold": [-0.1, 0.1], "ContinuationDelay": [0], "ObservationWindow": [1], "NormalizeWindow": [200]}
    technical = _technical_()
    ddpg = DDPGStrategyAPI(money_management=money, risk_management=risk, signal_management=Parameter({**common, **agent, "ActorRegularization": [0.0]}, "."), technical_management=technical, fundamental_management=Parameter({}, "."), sentimental_management=Parameter({}, "."), portfolio_management=Parameter({}, "."))
    rddpg = DDPGStrategyAPI(money_management=money, risk_management=risk, signal_management=Parameter({**common, **agent, "ActorRegularization": [0.01]}, "."), technical_management=technical, fundamental_management=Parameter({}, "."), sentimental_management=Parameter({}, "."), portfolio_management=Parameter({}, "."))
    assert isinstance(ddpg._agent_, DDPGAgentAPI)
    assert ddpg._agent_.actor_regularization == 0.0 and rddpg._agent_.actor_regularization == 0.01
    assert ddpg._observation_.shape() == 30
