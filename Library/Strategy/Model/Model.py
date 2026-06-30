from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any, Union, TYPE_CHECKING

from Library.Engine import MachineAPI
from Library.Portfolio import PositionType
from Library.Protocol.Action import (
    CloseBuyPositionActionAPI,
    CloseSellPositionActionAPI,
    ModifyBuyPositionVolumeActionAPI,
    ModifySellPositionVolumeActionAPI,
    OpenBuyPositionActionAPI,
    OpenSellPositionActionAPI,
    Stream
)
from Library.Protocol.Update import UpdateID, BarUpdateAPI
from Library.Strategy.Model.Action import ActionAPI, SizingMode
from Library.Strategy.Model.Observation import ObservationAPI
from Library.Strategy.Model.Reward import RewardAPI, RewardType
from Library.Strategy.Strategy import StrategyAPI

if TYPE_CHECKING:
    from Library.Parameter import Parameter
    from Library.Model.Core.Agent import AgentAPI

class ModelStrategyAPI(StrategyAPI):

    Subscription = Stream.All & ~Stream.Tick

    Agent: Union[AgentAPI, None] = None
    Weights: Union[Path, None] = None
    Training: bool = False
    Epochs: int = 1
    Seed: Union[int, None] = None
    Reward: RewardType = RewardType.LogReturn
    RewardScale: float = 1.0

    _ACTION_SHAPE_: int = 1
    _RV_: str = "RV"
    _ATR_: str = "ATR"
    _MOVING_AVERAGES_: tuple = ()
    _NORMALIZE_WINDOW_: int = 200
    _DEFAULT_WEIGHTS_: Path = Path.home() / ".cache" / "cAlgo" / "models"

    def __init__(self,
                 money_management: Parameter,
                 risk_management: Parameter,
                 signal_management: Parameter) -> None:
        super().__init__(money_management, risk_management, signal_management)
        self._sizing_mode_ = SizingMode.parse(self._value_(self.MoneyManagement, "SizingMode", "Fixed"))
        self._sizing_max_ = self._value_(self.MoneyManagement, "SizingMax", 1.0)
        self._sizing_deadzone_ = self._value_(self.MoneyManagement, "SizingDeadzone", 0.0)
        self._configured_weights_ = self._value_(self.SignalManagement, "Weights", None)
        self._observation_ = ObservationAPI(sizing_max=self._sizing_max_, realized_volatility=self._RV_, atr=self._ATR_, moving_averages=self._MOVING_AVERAGES_, normalize_window=self._NORMALIZE_WINDOW_)
        self._action_ = ActionAPI(mode=self._sizing_mode_, maximum=self._sizing_max_, deadzone=self._sizing_deadzone_)
        self._reward_ = RewardAPI(kind=self.Reward, scale=self.RewardScale)
        self._agent_: AgentAPI = self.Agent if self.Agent is not None else self._create_agent_((self._observation_.shape(),), self._ACTION_SHAPE_)
        if self.Agent is None and not self.Training and (self.Weights is not None or self._configured_weights_ is not None):
            self._agent_.load()
        self._previous_observation_ = None
        self._previous_action_ = None
        self._previous_equity_: Union[float, None] = None

    @abstractmethod
    def _create_agent_(self, observation_shape: tuple, action_shape: int) -> AgentAPI:
        raise NotImplementedError

    @staticmethod
    def _value_(section: Union[Parameter, None], key: str, default: Any) -> Any:
        value = getattr(section, key, None)
        if value is None: return default
        return value[0] if isinstance(value, (list, tuple)) else value

    def _weights_path_(self) -> Path:
        if self.Weights is not None: return self.Weights
        if self._configured_weights_ is not None: return Path(self._configured_weights_)
        return self._DEFAULT_WEIGHTS_

    def risk_management(self) -> None:
        return None

    @staticmethod
    def _position_(update: BarUpdateAPI) -> Any:
        buys = update.Portfolio.BuyPositions
        if buys: return buys[0]
        sells = update.Portfolio.SellPositions
        if sells: return sells[0]
        return None

    def _open_(self, sign: int, volume: float) -> Any:
        if sign > 0:
            return OpenBuyPositionActionAPI(PositionType=PositionType.Normal, Volume=volume, StopLoss=None, TakeProfit=None)
        return OpenSellPositionActionAPI(PositionType=PositionType.Normal, Volume=volume, StopLoss=None, TakeProfit=None)

    @staticmethod
    def _close_(position: Any) -> Any:
        if position.IsLong:
            return CloseBuyPositionActionAPI(PositionID=position.UID)
        return CloseSellPositionActionAPI(PositionID=position.UID)

    @staticmethod
    def _modify_(position: Any, volume: float) -> Any:
        if position.IsLong:
            return ModifyBuyPositionVolumeActionAPI(PositionID=position.UID, Volume=volume)
        return ModifySellPositionVolumeActionAPI(PositionID=position.UID, Volume=volume)

    def _control_(self, update: BarUpdateAPI, action: float) -> Union[list, None]:
        target = self._action_.target(action, update)
        sign = 1 if target > 0.0 else -1 if target < 0.0 else 0
        magnitude = abs(target)
        position = self._position_(update)
        if position is None:
            if magnitude == 0.0: return None
            return [self._open_(sign, magnitude)]
        current_sign = 1 if position.IsLong else -1
        if magnitude == 0.0:
            return [self._close_(position)]
        if sign == current_sign:
            if magnitude < position.Volume:
                return [self._modify_(position, magnitude)]
            return None
        return [self._close_(position), self._open_(sign, magnitude)]

    def _step_(self, update: BarUpdateAPI) -> Union[list, None]:
        observation = self._observation_.encode(update)
        equity = update.Portfolio.Equity
        if self.Training and self._previous_observation_ is not None:
            reward = self._reward_.reward(equity, self._previous_equity_, update.Portfolio.EquityDrawdown)
            self._agent_.memorise(self._previous_observation_, self._previous_action_, reward, observation, False)
            self._agent_.learn()
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