from __future__ import annotations

from pathlib import Path
from typing import Any, Union, TYPE_CHECKING

from Library.Engine import MachineAPI
from Library.Portfolio import PositionType
from Library.Portfolio.Sizing import SizingMode
from Library.Protocol.Update import UpdateID, BarUpdateAPI
from Library.Strategy.Model.Action import ActionAPI
from Library.Strategy.Model.Observation import ObservationAPI
from Library.Strategy.Model.Reward import RewardAPI, RewardType
from Library.Strategy.Rule.NNFX import NNFXStrategyAPI

if TYPE_CHECKING:
    from Library.Parameter import Parameter
    from Library.Model.Core.Agent import AgentAPI

class DDPGStrategyAPI(NNFXStrategyAPI):

    Agent: Union[AgentAPI, None] = None
    Weights: Union[Path, None] = None
    Training: bool = False
    Epochs: int = 1
    Seed: Union[int, None] = None
    Reward: RewardType = RewardType.LogReturn
    RewardScale: float = 1.0
    RewardClip: float = 1.0
    TrainFrequency: int = 1
    GradientSteps: int = 1

    _ACTION_SHAPE_: int = 1
    _EXPOSURE_REFERENCE_: float = 100.0
    _DEFAULT_WEIGHTS_: Path = Path.home() / ".cache" / "cAlgo" / "models"

    def __init__(self,
                 money_management: Parameter,
                 risk_management: Parameter,
                 signal_management: Parameter) -> None:
        super().__init__(money_management, risk_management, signal_management)
        self._entry_threshold_ = tuple(self.SignalManagement.NormalEntryThreshold)
        self._exit_threshold_ = tuple(self.SignalManagement.NormalExitThreshold)
        self._continuation_entry_ = tuple(self.SignalManagement.ContinuationEntryThreshold)
        self._continuation_exit_ = tuple(self.SignalManagement.ContinuationExitThreshold)
        self._continuation_delay_, = self.SignalManagement.ContinuationDelay
        self._sizing_min_, = self.MoneyManagement.SizingMin
        self._sizing_max_, = self.MoneyManagement.SizingMax
        weights = self.SignalManagement.Weights
        self._configured_weights_ = weights[0] if weights else None
        self._action_ = ActionAPI(mode=SizingMode.Balance, maximum=self._EXPOSURE_REFERENCE_)
        self._observation_ = ObservationAPI(action=self._action_, momentum_horizons=tuple(self.SignalManagement.MomentumHorizons), moving_average_horizons=tuple(self.SignalManagement.MovingAverageHorizons), normalize_window=self.SignalManagement.NormalizeWindow[0], window=self.SignalManagement.ObservationWindow[0])
        self._reward_ = RewardAPI(kind=self.Reward, scale=self.RewardScale, clip=self.RewardClip)
        self._agent_: AgentAPI = self.Agent if self.Agent is not None else self._create_agent_((self._observation_.shape(),), self._ACTION_SHAPE_)
        if self.Agent is None and not self.Training and (self.Weights is not None or self._configured_weights_ is not None):
            self._agent_.load()
        self._previous_observation_ = None
        self._previous_action_ = None
        self._previous_equity_: Union[float, None] = None
        self._step_index_: int = 0
        self._hybrid_confidence_: float = 0.0
        self._armed_: bool = True
        self._continuation_direction_: int = 0
        self._continuation_leg_: bool = False
        self._flat_bars_: int = 0

    def _create_agent_(self, observation_shape: tuple, action_shape: int) -> AgentAPI:
        from Library.Model import DDPGAgentAPI
        return DDPGAgentAPI(
            path=self._weights_path_(),
            input_shape=observation_shape,
            action_shape=action_shape,
            alpha=self.SignalManagement.ActorLearningRate[0],
            beta=self.SignalManagement.CriticLearningRate[0],
            tau=self.SignalManagement.SoftUpdate[0],
            fc1_shape=self.SignalManagement.HiddenShape1[0],
            fc2_shape=self.SignalManagement.HiddenShape2[0],
            memory_size=self.SignalManagement.MemorySize[0],
            batch_size=self.SignalManagement.BatchSize[0],
            gamma=self.SignalManagement.DiscountFactor[0],
            grad_clip=self.SignalManagement.GradientClip[0],
            actor_regularization=self.SignalManagement.ActorRegularization[0],
            seed=self.Seed
        )

    def _weights_path_(self) -> Path:
        if self.Weights is not None: return self.Weights
        if self._configured_weights_ is not None: return Path(self._configured_weights_)
        return self._DEFAULT_WEIGHTS_

    def _entry_risk_percentage_(self, update: BarUpdateAPI) -> float:
        entry_low, entry_high = self._entry_threshold_
        confidence = self._hybrid_confidence_
        if confidence > 0.0:
            span = 1.0 - entry_high
            fraction = (confidence - entry_high) / span if span > 0.0 else 1.0
        else:
            span = 1.0 + entry_low
            fraction = (entry_low - confidence) / span if span > 0.0 else 1.0
        fraction = min(1.0, max(0.0, fraction))
        return self._sizing_min_ + fraction * (self._sizing_max_ - self._sizing_min_)

    def _continuation_allowed_(self, sign: int) -> bool:
        if self._continuation_direction_ != sign: return False
        return self._flat_bars_ >= self._continuation_delay_

    def _control_(self, update: BarUpdateAPI, action: float) -> Union[list, None]:
        entry_low, entry_high = self._entry_threshold_
        continuation_low, continuation_high = self._continuation_entry_
        buys = update.Portfolio.BuyPositions
        sells = update.Portfolio.SellPositions
        self._flat_bars_ = self._flat_bars_ + 1 if not buys and not sells else 0
        if entry_low < action < entry_high:
            self._armed_ = True
        if not buys and (action >= entry_high or action >= continuation_high):
            if action >= entry_high and (self._armed_ or sells or self._continuation_direction_ < 0):
                self._armed_ = False
                self._hybrid_confidence_ = action
                self._continuation_direction_ = 1
                self._continuation_leg_ = False
                return self.open_buy_position(update, PositionType.Normal)
            if action >= continuation_high and self._continuation_allowed_(1):
                self._hybrid_confidence_ = action
                self._continuation_leg_ = True
                return self.open_buy_position(update, PositionType.Continuation)
            return None
        if not sells and (action <= entry_low or action <= continuation_low):
            if action <= entry_low and (self._armed_ or buys or self._continuation_direction_ > 0):
                self._armed_ = False
                self._hybrid_confidence_ = action
                self._continuation_direction_ = -1
                self._continuation_leg_ = False
                return self.open_sell_position(update, PositionType.Normal)
            if action <= continuation_low and self._continuation_allowed_(-1):
                self._hybrid_confidence_ = action
                self._continuation_leg_ = True
                return self.open_sell_position(update, PositionType.Continuation)
            return None
        exit_low, exit_high = self._continuation_exit_ if self._continuation_leg_ and (buys or sells) else self._exit_threshold_
        if exit_low < action < exit_high:
            if buys:
                self._continuation_direction_ = 0
                return self.close_buy_position(update)
            if sells:
                self._continuation_direction_ = 0
                return self.close_sell_position(update)
        return None

    def _step_(self, update: BarUpdateAPI) -> Union[list, None]:
        observation = self._observation_.encode(update)
        equity = update.Portfolio.Equity
        if self.Training and self._previous_observation_ is not None:
            reward = self._reward_.reward(equity, self._previous_equity_, update.Portfolio.EquityDrawdown)
            self._agent_.memorize(self._previous_observation_, self._previous_action_, reward, observation, False)
            self._step_index_ += 1
            if self._step_index_ % self.TrainFrequency == 0:
                for _ in range(self.GradientSteps): self._agent_.learn()
        action = self._agent_.decide(observation, explore=self.Training)
        self._previous_observation_ = observation
        self._previous_action_ = action
        self._previous_equity_ = equity
        return self._control_(update, float(action[0]))

    def _initialize_(self, _: Any) -> None:
        self._agent_.reset()
        self._observation_.reset()
        self._reward_.reset()
        self._previous_observation_ = None
        self._previous_action_ = None
        self._previous_equity_ = None
        self._step_index_ = 0

    def signal_management(self) -> MachineAPI:
        signal_engine = MachineAPI(Name="Signal Management", Events=len(UpdateID))
        initialization = signal_engine.state(name="Initialization")
        waiting_signal = signal_engine.state(name="Waiting Signal")
        termination = signal_engine.state(name="Termination", end=True)
        initialization.on(event=UpdateID.Execution, to=waiting_signal, action=self._initialize_, reason="Initialized")
        initialization.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Abruptly Terminated")
        waiting_signal.on(event=UpdateID.BarClosed, to=waiting_signal, action=self._step_, reason=None)
        waiting_signal.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Safely Terminated")
        return signal_engine