import math
from datetime import datetime
from types import SimpleNamespace

from Library.Database.Dataframe import np
from Library.Market.Price import Direction
from Library.Engine import MachineAPI
from Library.Utility.Parameter import Parameter
from Library.Protocol.Action import OpenBuyPositionActionAPI, OpenSellPositionActionAPI
from Library.Strategy.Hybrid.DDPG import DDPGStrategyAPI
from Library.Strategy.Rule.NNFX import NNFXStrategyAPI
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
    return SimpleNamespace(Volume=volume, Direction=Direction.Buy if long else Direction.Sell, UID=uid, EntryBalance=10000.0, NetPnL=SimpleNamespace(PnL=0.0), MaxEquityDrawdownPnL=SimpleNamespace(PnL=0.0), MaxEquityRunupPnL=SimpleNamespace(PnL=0.0))

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

def _strategy_(risk=1.0, atr_scale=1.5, entry=None, exit=None, action=0.0, training=False, neutralize=False):
    _FakeDDPG_.Fake = action
    _FakeDDPG_.Agent = None
    _FakeDDPG_.Training = training
    _FakeDDPG_.Reward = RewardType.LogReturn
    _FakeDDPG_.RewardScale = 1.0
    money = Parameter({"RiskPercentage": [risk], "ATRScale": [atr_scale]}, ".")
    signal = Parameter({"DirectionalEntryThreshold": list(entry) if entry else None, "DirectionalExitThreshold": list(exit) if exit else None, "ObservationWindow": [1], "NormalizeWindow": [200], "NeutralizeReward": [neutralize]}, ".")
    return _FakeDDPG_(money_management=money, risk_management=None, signal_management=signal, technical_management=_technical_(), fundamental_management=Parameter({}, "."), sentimental_management=Parameter({}, "."), portfolio_management=Parameter({}, "."))

def test_strategy_type_registers_four_strategies():
    assert StrategyType.Download.value == 1
    assert StrategyType.NNFX.value == 2
    assert StrategyType.DDPG.value == 3
    assert StrategyType.Trend.value == 4

def test_signal_maps_to_proportional_target_exposure():
    strategy = _strategy_()
    full = strategy._control_(_update_(), 1.0)
    assert len(full) == 1 and isinstance(full[0], OpenBuyPositionActionAPI)
    assert full[0].Volume == 6000.0 and full[0].StopLoss is None
    partial = _strategy_()._control_(_update_(), 0.7)
    assert isinstance(partial[0], OpenBuyPositionActionAPI) and partial[0].Volume == 4000.0
    short = _strategy_()._control_(_update_(), -1.0)
    assert isinstance(short[0], OpenSellPositionActionAPI) and short[0].Volume == 6000.0

def test_reference_volume_tracks_the_rolling_atr():
    assert _strategy_()._reference_volume_(_update_(atr=0.01)) == 6000.0
    assert _strategy_()._reference_volume_(_update_(atr=0.02)) == 3000.0
    assert _strategy_(risk=2.0)._reference_volume_(_update_(atr=0.01)) == 13000.0

def test_unchanged_signal_still_reduces_when_volatility_rises():
    strategy = _strategy_()
    assert strategy._control_(_update_(atr=0.01), 1.0)[0].Volume == 6000.0
    reduced = strategy._control_(_update_(buys=[_position_(6000.0, True)], atr=0.02), 1.0)
    assert len(reduced) == 1 and isinstance(reduced[0], OpenSellPositionActionAPI)
    assert reduced[0].Volume == 3000.0

def test_netting_adjusts_only_the_delta():
    strategy = _strategy_()
    actions = strategy._control_(_update_(buys=[_position_(2000.0, True)]), 1.0)
    assert len(actions) == 1 and isinstance(actions[0], OpenBuyPositionActionAPI)
    assert actions[0].Volume == 4000.0

def test_zero_signal_flattens_open_exposure():
    strategy = _strategy_()
    actions = strategy._control_(_update_(buys=[_position_(8000.0, True)]), 0.0)
    assert len(actions) == 1 and isinstance(actions[0], OpenSellPositionActionAPI)
    assert actions[0].Volume == 8000.0

def test_opposite_signal_flips_through_a_single_oversized_action():
    strategy = _strategy_()
    actions = strategy._control_(_update_(buys=[_position_(8000.0, True)]), -0.7)
    assert len(actions) == 1 and isinstance(actions[0], OpenSellPositionActionAPI)
    assert actions[0].Volume == 12000.0

def test_delta_below_volume_minimum_is_silent():
    strategy = _strategy_()
    assert strategy._control_(_update_(), 0.0) is None
    assert strategy._control_(_update_(buys=[_position_(4000.0, True)]), 0.7) is None

def test_thresholds_are_disabled_by_default():
    strategy = _strategy_()
    assert strategy.DirectionalEntryThreshold == (None, None)
    assert strategy.DirectionalExitThreshold == (None, None)
    assert strategy.VolumeEntryThreshold == (None, None)
    assert strategy.VolumeExitThreshold == (None, None)
    assert strategy._control_(_update_(), 0.25) is not None

def test_entry_threshold_blocks_signals_inside_the_band():
    strategy = _strategy_(entry=(-0.4, 0.4))
    assert strategy._control_(_update_(), 0.25) is None
    assert strategy._control_(_update_(buys=[_position_(8000.0, True)]), 0.25) is None
    assert strategy._control_(_update_(), 0.7) is not None

def test_exit_threshold_flattens_inside_the_band():
    strategy = _strategy_(exit=(-0.1, 0.1))
    actions = strategy._control_(_update_(buys=[_position_(8000.0, True)]), 0.05)
    assert len(actions) == 1 and isinstance(actions[0], OpenSellPositionActionAPI)
    assert actions[0].Volume == 8000.0
    assert strategy._control_(_update_(), 0.05) is None

def test_one_sided_threshold_constrains_only_that_side():
    strategy = _strategy_(entry=(None, 0.4))
    assert strategy.DirectionalEntryThreshold == (None, 0.4)
    assert strategy._control_(_update_(), 0.25) is None
    assert isinstance(strategy._control_(_update_(), -0.25)[0], OpenSellPositionActionAPI)

def test_every_position_is_opened_as_normal():
    strategy = _strategy_()
    assert strategy._control_(_update_(), 0.7)[0].PositionType.name == "Normal"
    assert strategy._control_(_update_(buys=[_position_(8000.0, True)]), -0.7)[0].PositionType.name == "Normal"

def test_strategy_owns_no_rule_based_risk_machine():
    strategy = _strategy_()
    assert strategy.risk_management() is None
    assert isinstance(strategy.signal_management(), MachineAPI)
    assert not isinstance(strategy, NNFXStrategyAPI)

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
    money = Parameter({"RiskPercentage": [1.0], "ATRScale": [1.5]}, ".")
    agent = {"ActorLearningRate": [0.0001], "CriticLearningRate": [0.001], "SoftUpdate": [0.001], "HiddenShape1": [400], "HiddenShape2": [300], "MemorySize": [1000000], "BatchSize": [64], "DiscountFactor": [0.99], "GradientClip": [1.0]}
    common = {"DirectionalEntryThreshold": None, "DirectionalExitThreshold": None, "ObservationWindow": [1], "NormalizeWindow": [200]}
    technical = _technical_()
    ddpg = DDPGStrategyAPI(money_management=money, risk_management=None, signal_management=Parameter({**common, **agent, "ActorRegularization": [0.0]}, "."), technical_management=technical, fundamental_management=Parameter({}, "."), sentimental_management=Parameter({}, "."), portfolio_management=Parameter({}, "."))
    rddpg = DDPGStrategyAPI(money_management=money, risk_management=None, signal_management=Parameter({**common, **agent, "ActorRegularization": [0.01]}, "."), technical_management=technical, fundamental_management=Parameter({}, "."), sentimental_management=Parameter({}, "."), portfolio_management=Parameter({}, "."))
    assert isinstance(ddpg._agent_, DDPGAgentAPI)
    assert ddpg._agent_.actor_regularization == 0.0 and rddpg._agent_.actor_regularization == 0.01
    assert ddpg._observation_.shape() == 30
