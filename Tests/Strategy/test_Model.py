import math
from datetime import datetime
from types import SimpleNamespace

from Library.Database.Dataframe import np
from Library.Engine import MachineAPI
from Library.Parameter import Parameter
from Library.Protocol.Action import (
    CloseBuyPositionActionAPI,
    ModifyBuyPositionVolumeActionAPI,
    OpenBuyPositionActionAPI,
    OpenSellPositionActionAPI
)
from Library.Strategy.Model import ModelStrategyAPI, DDPGStrategyAPI, RDDPGStrategyAPI, SACStrategyAPI, TD3StrategyAPI
from Library.Strategy.Model.Reward import RewardType
from Library.Strategy.Strategy import StrategyType

class _FakeAgent_:

    def __init__(self, action):
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

class _FakeModelStrategy_(ModelStrategyAPI):

    def _create_agent_(self, observation_shape, action_shape):
        self.observation_shape = observation_shape
        return self.Fake

def _indicator_(value):
    return SimpleNamespace(Result=SimpleNamespace(last=lambda: value))

def _position_(volume, long, uid=1):
    return SimpleNamespace(Volume=volume, IsLong=long, IsShort=not long, UID=uid, EntryBalance=10000.0, NetPnL=SimpleNamespace(PnL=0.0), MaxEquityDrawdownPnL=SimpleNamespace(PnL=0.0), MaxEquityRunupPnL=SimpleNamespace(PnL=0.0))

def _update_(buys=None, sells=None, equity=10000.0, drawdown=0.0, close=1.11):
    technical = SimpleNamespace(ATR=_indicator_(0.01), RVFast=_indicator_(0.008))
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
        EquityDrawdown=drawdown,
        EquityRunup=0.0,
        Security=SimpleNamespace(Contract=SimpleNamespace(VolumeStep=1000.0, VolumeMin=1000.0, VolumeMax=100000.0))
    )
    return SimpleNamespace(Bar=bar, Technical=technical, Portfolio=portfolio)

def _strategy_(action=0.5, mode="Fixed", maximum=10000.0, minimum=0.0, entry=(0.0, 0.0), exit=(0.0, 0.0), training=False):
    _FakeModelStrategy_.Fake = _FakeAgent_(action)
    _FakeModelStrategy_.Agent = None
    _FakeModelStrategy_.Training = training
    _FakeModelStrategy_.Reward = RewardType.LogReturn
    _FakeModelStrategy_.RewardScale = 1.0
    money = Parameter({"SizingMode": [mode], "SizingMin": [minimum], "SizingMax": [maximum]}, ".")
    signal = Parameter({"NormalEntryThreshold": list(entry), "NormalExitThreshold": list(exit)}, ".")
    empty = Parameter({}, ".")
    return _FakeModelStrategy_(money_management=money, risk_management=empty, signal_management=signal)

def test_control_opens_from_flat():
    strategy = _strategy_()
    buy = strategy._control_(_update_(), 0.5)
    sell = strategy._control_(_update_(), -0.5)
    assert len(buy) == 1 and isinstance(buy[0], OpenBuyPositionActionAPI) and buy[0].Volume == 5000.0
    assert len(sell) == 1 and isinstance(sell[0], OpenSellPositionActionAPI) and sell[0].Volume == 5000.0

def test_control_scales_out_same_side():
    strategy = _strategy_()
    actions = strategy._control_(_update_(buys=[_position_(8000.0, True, uid=7)]), 0.5)
    assert len(actions) == 1 and isinstance(actions[0], ModifyBuyPositionVolumeActionAPI)
    assert actions[0].PositionID == 7 and actions[0].Volume == 5000.0

def test_control_holds_no_scale_in():
    strategy = _strategy_()
    assert strategy._control_(_update_(buys=[_position_(5000.0, True)]), 0.8) is None

def test_control_reverses_on_sign_flip():
    strategy = _strategy_()
    actions = strategy._control_(_update_(buys=[_position_(5000.0, True, uid=3)]), -0.5)
    assert len(actions) == 2
    assert isinstance(actions[0], CloseBuyPositionActionAPI) and actions[0].PositionID == 3
    assert isinstance(actions[1], OpenSellPositionActionAPI) and actions[1].Volume == 5000.0

def test_control_closes_on_zero_target():
    strategy = _strategy_()
    actions = strategy._control_(_update_(buys=[_position_(5000.0, True, uid=9)]), 0.05)
    assert len(actions) == 1 and isinstance(actions[0], CloseBuyPositionActionAPI) and actions[0].PositionID == 9

def test_control_exit_interval_is_flat():
    strategy = _strategy_(exit=(-0.2, 0.2))
    assert strategy._control_(_update_(), 0.1) is None

def test_control_entry_interval_gates_entry_and_reversal():
    strategy = _strategy_(entry=(-0.4, 0.4), exit=(-0.1, 0.1))
    assert strategy._control_(_update_(), 0.25) is None
    opened = strategy._control_(_update_(), 0.5)
    assert len(opened) == 1 and isinstance(opened[0], OpenBuyPositionActionAPI)
    weak = strategy._control_(_update_(buys=[_position_(5000.0, True, uid=4)]), -0.25)
    assert len(weak) == 1 and isinstance(weak[0], CloseBuyPositionActionAPI) and weak[0].PositionID == 4
    strong = strategy._control_(_update_(buys=[_position_(5000.0, True)]), -0.6)
    assert len(strong) == 2 and isinstance(strong[1], OpenSellPositionActionAPI)

def test_control_hold_band_suppresses_small_rescales():
    strategy = _strategy_(entry=(-0.4, 0.4), exit=(-0.1, 0.1))
    assert strategy._control_(_update_(buys=[_position_(5000.0, True)]), 0.45) is None
    actions = strategy._control_(_update_(buys=[_position_(9000.0, True)]), 0.3)
    assert len(actions) == 1 and isinstance(actions[0], ModifyBuyPositionVolumeActionAPI) and actions[0].Volume == 3000.0
    closed = strategy._control_(_update_(buys=[_position_(5000.0, True)]), 0.05)
    assert len(closed) == 1 and isinstance(closed[0], CloseBuyPositionActionAPI)

def test_control_asymmetric_entry_disables_one_side():
    strategy = _strategy_(entry=(-2.0, 0.4), exit=(-0.1, 0.1))
    assert strategy._control_(_update_(), -0.9) is None
    opened = strategy._control_(_update_(), 0.5)
    assert len(opened) == 1 and isinstance(opened[0], OpenBuyPositionActionAPI)

def test_control_sizing_min_floors_volume():
    strategy = _strategy_(minimum=4000.0, entry=(-0.4, 0.4), exit=(-0.1, 0.1))
    opened = strategy._control_(_update_(), 0.41)
    assert len(opened) == 1 and opened[0].Volume == 4000.0

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

def test_initialize_resets_episode_state():
    strategy = _strategy_(training=True)
    strategy._step_(_update_())
    strategy._initialize_(None)
    assert strategy._previous_observation_ is None
    assert strategy._previous_action_ is None
    assert strategy._previous_equity_ is None
    assert strategy._agent_.resets == 1

def test_signal_management_is_machine_and_risk_is_none():
    strategy = _strategy_()
    assert isinstance(strategy.signal_management(), MachineAPI)
    assert strategy.risk_management() is None

def test_value_helper_reads_or_defaults():
    assert ModelStrategyAPI._value_(Parameter({"X": [5]}, "."), "X", 9) == 5
    assert ModelStrategyAPI._value_(Parameter({}, "."), "X", 9) == 9
    assert ModelStrategyAPI._value_(None, "X", 9) == 9

def test_strategy_type_registers_model_strategies():
    assert StrategyType.SAC.value == 4
    assert StrategyType.RDDPG.value == 5
    assert StrategyType.TD3.value == 6

def test_concrete_strategies_build_agents_with_observation_shape():
    from Library.Model import DDPGAgentAPI, SACAgentAPI, TD3AgentAPI
    money = Parameter({"SizingMode": ["Fixed"], "SizingMax": [1000.0], "SizingDeadzone": [0.0]}, ".")
    empty = Parameter({}, ".")
    ddpg = DDPGStrategyAPI(money_management=money, risk_management=empty, signal_management=empty)
    sac = SACStrategyAPI(money_management=money, risk_management=empty, signal_management=empty)
    td3 = TD3StrategyAPI(money_management=money, risk_management=empty, signal_management=empty)
    assert isinstance(ddpg._agent_, DDPGAgentAPI) and isinstance(sac._agent_, SACAgentAPI) and isinstance(td3._agent_, TD3AgentAPI)
    assert ddpg._observation_.shape() == 29

def test_rddpg_defaults_regularized_and_vanilla_stays_pure():
    money = Parameter({"SizingMode": ["Fixed"], "SizingMax": [1000.0], "SizingDeadzone": [0.0]}, ".")
    empty = Parameter({}, ".")
    ddpg = DDPGStrategyAPI(money_management=money, risk_management=empty, signal_management=empty)
    extended = RDDPGStrategyAPI(money_management=money, risk_management=empty, signal_management=empty)
    assert ddpg._agent_.actor_regularization == 0.0
    assert extended._agent_.actor_regularization == 0.001

def test_td3_recipe_overrides_agent_hyperparameters():
    money = Parameter({"SizingMode": ["Fixed"], "SizingMax": [1000.0], "SizingDeadzone": [0.0]}, ".")
    empty = Parameter({}, ".")
    recipe = Parameter({"BatchSize": [50], "PolicyDelay": [3], "PolicyNoise": [0.3]}, ".")
    td3 = TD3StrategyAPI(money_management=money, risk_management=empty, signal_management=recipe)
    assert td3._agent_.batch_size == 50 and td3._agent_.policy_delay == 3 and td3._agent_.policy_noise == 0.3

def test_recipe_overrides_agent_hyperparameters():
    money = Parameter({"SizingMode": ["Fixed"], "SizingMax": [1000.0], "SizingDeadzone": [0.0]}, ".")
    empty = Parameter({}, ".")
    recipe = Parameter({"BatchSize": [32], "DiscountFactor": [0.95]}, ".")
    ddpg = DDPGStrategyAPI(money_management=money, risk_management=empty, signal_management=recipe)
    assert ddpg._agent_.batch_size == 32 and ddpg._agent_.gamma == 0.95