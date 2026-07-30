from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Union, TYPE_CHECKING

from Library.Database.Dataframe import np
from Library.Engine import MachineAPI
from Library.Indicator.Indicator import parse_technical
from Library.Indicator.Technical.Technical import TechnicalType
from Library.Portfolio import PositionType
from Library.Portfolio.Sizing import SizingMode, calculate_fixed_fractional_volume, calculate_normalized_volume
from Library.Protocol.Action import Stream, OpenBuyPositionActionAPI, OpenSellPositionActionAPI
from Library.Protocol.Update import UpdateID, BarUpdateAPI
from Library.Strategy.Model.Action import ActionAPI
from Library.Strategy.Model.Normalizer import NormalizerAPI
from Library.Strategy.Model.Observation import ObservationAPI
from Library.Strategy.Model.Reward import RewardAPI, RewardType
from Library.Strategy.Strategy import StrategyAPI
from Library.Utility.Math import EPSILON

if TYPE_CHECKING:
    from Library.Parameter import Parameter
    from Library.Model.Core.Agent import AgentAPI

class DDPGNormalizationAPI(NormalizerAPI):
    """
    DDPG normalizer — causal EWMA z-score (no look-ahead).

    Maintains a per-feature exponential mean/variance and standardizes each flagged
    value with statistics through the PREVIOUS step only (the current value is folded
    in after it is emitted). Features flagged False by the encoder (sin/cos, exposure,
    drawdown) bypass this layer so their natural bounds are preserved.
    """

    def __init__(self, window: int) -> None:
        self._alpha_ = 1.0 / window if window else 0.0
        self._mean_: Union[np.ndarray, None] = None
        self._variance_: Union[np.ndarray, None] = None

    def reset(self) -> None:
        self._mean_ = None
        self._variance_ = None

    def transform(self, values: np.ndarray, mask: np.ndarray) -> np.ndarray:
        if self._mean_ is None:
            self._mean_ = values.copy()
            self._variance_ = np.zeros_like(values)
            return np.where(mask, 0.0, values).astype(np.float32)
        standardized = (values - self._mean_) / np.sqrt(self._variance_ + EPSILON)
        output = np.where(mask, standardized, values)
        delta = values - self._mean_
        mean = self._mean_ + self._alpha_ * delta
        variance = (1.0 - self._alpha_) * (self._variance_ + self._alpha_ * delta * delta)
        self._mean_ = np.where(mask, mean, self._mean_)
        self._variance_ = np.where(mask, variance, self._variance_)
        return output.astype(np.float32)

class DDPGObservationAPI(ObservationAPI):
    """
    DDPG observation encoder — the scale-free, transferable observation vector.

    Defines the DDPG feature design (calendar, wealth trajectory, open-trade state,
    bar geometry, and dimensionless technicals) with two normalization layers. The
    guiding principle is invariance to price level, volatility regime, and account
    size, so the agent learns patterns rather than the idiosyncrasies of one security.
    Layer 1 is the per-feature causal encoding below (log-returns, ratios, vol-scaling,
    sin/cos), which makes every feature dimensionless; layer 2 is the rolling EWMA
    z-score (DDPGNormalizationAPI) applied by the base over the unbounded features.

    The encoder consumes technical primitives by role. The realized-volatility and
    ATR proxies (_REALIZED_FAST_, _REALIZED_SLOW_, _ATR_) are its fixed contract with
    the technical layer. The momentum and overlap features are the strategy's momentum
    and overlap indicators (discovered from TechnicalManagement by type), each read by
    name; the momentum lookback is read from the indicator itself.

    Feature groups, in canonical order:

      Timestamp (8) — calendar cyclicality. sin/cos pairs of Month/Weekday/Hour/Minute.
      Account (4)   — wealth trajectory, scale-free. Balance and Equity as returns from
                      initial capital; EquityDrawdown (bounded [-1, 0], bypass) and
                      EquityRunup.
      Position (5)  — open-trade state, scale-free. Signed exposure (volume divided by
                      the exposure-reference MaxVolume, bounded [-1, 1], bypass);
                      unrealized return, max drawdown and max runup as fractions of the
                      entry balance; duration as ln(1 + bars held).
      Market (6)    — bar geometry and microstructure, Bid series. Gap/High/Low/Close as
                      vol-scaled log-moves vs the previous close; Volume as ln(1 + V);
                      Spread as the relative quote spread of the close tick.
      Indicator     — dimensionless technicals: ATR/Close, the RV_fast level, the
                      volatility regime ln(RV_fast / RV_slow), and the Efficiency Ratio
                      (net move over summed absolute moves, bounded [0, 1], bypass — it
                      separates trending from ranging regimes); then one momentum feature
                      per momentum indicator (value / (RV_fast * sqrt(lookback))) and one
                      feature pair per overlap indicator: the distance
                      (Close - value) / ATR and the differential slope
                      (value - value_prev) / ATR (the trend state and its drift).
    """

    _REALIZED_FAST_ = "RVFast"
    _REALIZED_SLOW_ = "RVSlow"
    _ATR_ = "ATR"
    _EFFICIENCY_ = "ER"

    def __init__(self, action: ActionAPI, momentum_features: tuple, overlap_features: tuple, normalize_window: int, window: int, account: bool = True) -> None:
        super().__init__(normalizer=DDPGNormalizationAPI(normalize_window), window=window)
        self._action_ = action
        self._account_state_ = account
        self._momentum_features_ = tuple(momentum_features)
        self._overlap_features_ = tuple(overlap_features)
        self._previous_close_: Union[float, None] = None
        self._position_uid_ = None
        self._position_bars_: int = 0

    def _reset_state_(self) -> None:
        self._previous_close_ = None
        self._position_uid_ = None
        self._position_bars_ = 0

    def _frame_size_(self) -> int:
        return 8 + (4 if self._account_state_ else 0) + (5 if self._account_state_ else 1) + 6 + 4 + len(self._momentum_features_) + 2 * len(self._overlap_features_)

    @staticmethod
    def _indicator_(update: BarUpdateAPI, name: str):
        indicator = getattr(update.Technical, name, None)
        return indicator.Result.last() if indicator is not None else None

    @staticmethod
    def _open_position_(update: BarUpdateAPI):
        buys = update.Portfolio.BuyPositions
        if buys: return buys[0]
        sells = update.Portfolio.SellPositions
        if sells: return sells[0]
        return None

    def _timestamp_features_(self, update: BarUpdateAPI, features: list) -> None:
        moment = update.Bar.Timestamp.DateTime
        for value, period in ((moment.month - 1, 12), (moment.weekday(), 7), (moment.hour, 24), (moment.minute, 60)):
            angle = 2.0 * math.pi * value / period
            features.append((math.sin(angle), False))
            features.append((math.cos(angle), False))

    def _account_features_(self, update: BarUpdateAPI, features: list) -> None:
        portfolio = update.Portfolio
        initial = portfolio.InitialBalance or 0.0
        balance = portfolio.Account.Balance if portfolio.Account and portfolio.Account.Balance is not None else 0.0
        features.append((balance / initial - 1.0 if initial else 0.0, True))
        features.append((portfolio.Equity / initial - 1.0 if initial else 0.0, True))
        features.append((portfolio.EquityDrawdown, False))
        features.append((portfolio.EquityRunup, True))

    def _position_features_(self, update: BarUpdateAPI, features: list) -> None:
        position = self._open_position_(update)
        if position is None:
            self._position_uid_ = None
            self._position_bars_ = 0
            features.append((0.0, False))
            if not self._account_state_: return
            features.append((0.0, True))
            features.append((0.0, True))
            features.append((0.0, True))
            features.append((0.0, True))
            return
        if position.UID != self._position_uid_:
            self._position_uid_ = position.UID
            self._position_bars_ = 1
        else:
            self._position_bars_ += 1
        signed = position.Direction.value * position.Volume
        maximum = self._action_.maximum_volume(update)
        entry = position.EntryBalance or 0.0
        net = position.NetPnL.PnL if position.NetPnL and position.NetPnL.PnL is not None else 0.0
        drawdown = position.MaxEquityDrawdownPnL.PnL if position.MaxEquityDrawdownPnL and position.MaxEquityDrawdownPnL.PnL is not None else 0.0
        runup = position.MaxEquityRunupPnL.PnL if position.MaxEquityRunupPnL and position.MaxEquityRunupPnL.PnL is not None else 0.0
        features.append((max(-1.0, min(1.0, signed / maximum)) if maximum else 0.0, False))
        if not self._account_state_: return
        features.append((net / entry if entry else 0.0, True))
        features.append((drawdown / entry if entry else 0.0, True))
        features.append((runup / entry if entry else 0.0, True))
        features.append((math.log1p(self._position_bars_), True))

    def _market_features_(self, update: BarUpdateAPI, features: list) -> None:
        bar = update.Bar
        close_price = bar.CloseTick.Bid.Price
        realized = self._indicator_(update, self._REALIZED_FAST_)
        sigma = realized if realized and realized > 0.0 else 1.0
        previous = self._previous_close_
        if previous and previous > 0.0:
            features.append((math.log(bar.OpenTick.Bid.Price / previous) / sigma, False))
            features.append((math.log(bar.HighTick.Bid.Price / previous) / sigma, False))
            features.append((math.log(bar.LowTick.Bid.Price / previous) / sigma, False))
            features.append((math.log(close_price / previous) / sigma, False))
        else:
            features.append((0.0, False))
            features.append((0.0, False))
            features.append((0.0, False))
            features.append((0.0, False))
        volume = bar.Volume
        features.append((math.log1p(volume) if volume and volume > 0.0 else 0.0, True))
        ask = getattr(bar.CloseTick, "Ask", None)
        ask_price = ask.Price if ask is not None else None
        features.append(((ask_price - close_price) / close_price if ask_price and close_price and close_price > 0.0 else 0.0, True))
        self._previous_close_ = close_price

    def _indicator_features_(self, update: BarUpdateAPI, features: list) -> None:
        close_price = update.Bar.CloseTick.Bid.Price
        realized = self._indicator_(update, self._REALIZED_FAST_)
        realized_slow = self._indicator_(update, self._REALIZED_SLOW_)
        atr = self._indicator_(update, self._ATR_)
        sigma = realized if realized and realized > 0.0 else 1.0
        scale = atr if atr and atr > 0.0 else None
        features.append((scale / close_price if scale and close_price and close_price > 0.0 else 0.0, True))
        features.append((realized if realized and realized > 0.0 else 0.0, True))
        features.append((math.log(realized / realized_slow) if realized and realized > 0.0 and realized_slow and realized_slow > 0.0 else 0.0, False))
        efficiency = self._indicator_(update, self._EFFICIENCY_)
        features.append((efficiency if efficiency is not None else 0.0, False))
        for name in self._momentum_features_:
            indicator = getattr(update.Technical, name, None)
            momentum = indicator.Result.last() if indicator is not None else None
            span = (getattr(indicator, "Window", 1) or 1) if indicator is not None else 1
            features.append((momentum / (sigma * math.sqrt(span)) if momentum is not None and math.isfinite(momentum) else 0.0, False))
        for name in self._overlap_features_:
            indicator = getattr(update.Technical, name, None)
            average = indicator.Result.last() if indicator is not None else None
            previous = indicator.Result.last(1) if indicator is not None else None
            valid = average is not None and math.isfinite(average) and scale
            features.append(((close_price - average) / scale if valid else 0.0, True))
            features.append(((average - previous) / scale if valid and previous is not None and math.isfinite(previous) else 0.0, True))

    def _features_(self, update: BarUpdateAPI) -> list:
        features: list = []
        self._timestamp_features_(update, features)
        if self._account_state_: self._account_features_(update, features)
        self._position_features_(update, features)
        self._market_features_(update, features)
        self._indicator_features_(update, features)
        return features

class DDPGStrategyAPI(StrategyAPI):

    Subscription = Stream.All & ~Stream.Tick

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
                 signal_management: Parameter,
                 technical_management: Parameter,
                 fundamental_management: Parameter,
                 sentimental_management: Parameter,
                 portfolio_management: Parameter) -> None:
        super().__init__(money_management, risk_management, signal_management, technical_management, fundamental_management, sentimental_management, portfolio_management)
        self._risk_percentage_, = self.MoneyManagement.RiskPercentage
        self._atr_scale_, = self.MoneyManagement.ATRScale
        weights = self.SignalManagement.Weights
        self._configured_weights_ = weights[0] if weights else None
        neutralize = self.SignalManagement.NeutralizeReward
        self._neutralize_reward_ = bool(neutralize[0]) if neutralize else False
        neutralize_scale = self.SignalManagement.NeutralizeScale
        self._neutralize_scale_ = float(neutralize_scale[0]) if neutralize_scale else 1.0
        turnover = self.SignalManagement.TurnoverCost
        self._turnover_cost_ = float(turnover[0]) if turnover else 0.0
        smoothing = self.SignalManagement.SignalSmoothing
        self._signal_smoothing_ = float(smoothing[0]) if smoothing else 0.0
        interval = self.SignalManagement.DecisionInterval
        self._decision_interval_ = max(1, int(interval[0])) if interval else 1
        schedule = self.SignalManagement.DecisionSchedule
        self._decision_schedule_ = str(schedule[0]).upper() if schedule else None
        rebalance = self.SignalManagement.RebalanceThreshold
        self._rebalance_threshold_ = float(rebalance[0]) if rebalance else 0.0
        account = self.SignalManagement.AccountFeatures
        self._account_features_enabled_ = bool(account[0]) if account else True
        momentum, overlap = self._observation_features_()
        self._action_ = ActionAPI(mode=SizingMode.Balance, maximum=self._EXPOSURE_REFERENCE_, deadzone=0.0)
        self._observation_ = DDPGObservationAPI(action=self._action_, momentum_features=momentum, overlap_features=overlap, normalize_window=self.SignalManagement.NormalizeWindow[0], window=self.SignalManagement.ObservationWindow[0], account=self._account_features_enabled_)
        scale = self.SignalManagement.RewardScale
        clip = self.SignalManagement.RewardClip
        self._reward_ = RewardAPI(kind=self.Reward, scale=float(scale[0]) if scale else self.RewardScale, clip=float(clip[0]) if clip else self.RewardClip)
        self._agent_: AgentAPI = self.Agent if self.Agent is not None else self._create_agent_((self._observation_.shape(),), self._ACTION_SHAPE_)
        if self.Agent is None and not self.Training and (self.Weights is not None or self._configured_weights_ is not None):
            self._agent_.load()
        self._previous_observation_ = None
        self._previous_action_ = None
        self._previous_equity_: Union[float, None] = None
        self._previous_bar_close_: Union[float, None] = None
        self._previous_exposure_: float = 0.0
        self._smoothed_signal_: Union[float, None] = None
        self._current_action_ = None
        self._pending_reward_: float = 0.0
        self._decision_index_: int = 0
        self._decision_bucket_ = None
        self._step_index_: int = 0

    def _observation_features_(self) -> tuple:
        technical = parse_technical(self.TechnicalManagement.data)
        momentum, overlap = [], []
        for name in self.TechnicalManagement.data:
            indicator = getattr(technical, name, None)
            if indicator is None: continue
            if indicator.Type == TechnicalType.Momentum: momentum.append(name)
            elif indicator.Type in (TechnicalType.Overlap, TechnicalType.Baseline): overlap.append(name)
        return tuple(momentum), tuple(overlap)

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
            warmup=self.SignalManagement.WarmupSteps[0] if self.SignalManagement.WarmupSteps else 0,
            seed=self.Seed
        )

    def _weights_path_(self) -> Path:
        if self.Weights is not None: return self.Weights
        if self._configured_weights_ is not None: return Path(self._configured_weights_)
        return self._DEFAULT_WEIGHTS_

    def _exposure_(self, update: BarUpdateAPI) -> float:
        return sum(position.Volume for position in update.Portfolio.BuyPositions) - sum(position.Volume for position in update.Portfolio.SellPositions)

    def _reference_volume_(self, update: BarUpdateAPI) -> float:
        atr = update.Technical.ATR.Result.last()
        contract = update.Portfolio.Security.Contract
        if not atr or atr <= 0.0 or not contract or not contract.PipSize: return 0.0
        return calculate_fixed_fractional_volume(self._risk_percentage_, self._atr_scale_ * atr / contract.PipSize, update.Portfolio.Account, contract)

    def _target_(self, update: BarUpdateAPI, action: float) -> Union[float, None]:
        if self._neutral_(action, self.DirectionalEntryThreshold): return None
        reference = self._reference_volume_(update)
        if not reference: return None
        return reference * max(-1.0, min(1.0, action))

    def _control_(self, update: BarUpdateAPI, action: float) -> Union[list, None]:
        if self._neutral_(action, self.DirectionalExitThreshold) and self._exposure_(update): target = 0.0
        else: target = self._target_(update, action)
        if target is None: return None
        contract = update.Portfolio.Security.Contract
        delta = target - self._exposure_(update)
        floor = contract.VolumeMin
        if self._rebalance_threshold_ > 0.0:
            reference = self._reference_volume_(update)
            if reference: floor = max(floor, self._rebalance_threshold_ * abs(reference))
        volume = calculate_normalized_volume(abs(delta), contract)
        if abs(delta) < floor or not volume: return None
        return [OpenBuyPositionActionAPI(PositionType=PositionType.Normal, Volume=volume, StopLoss=None, TakeProfit=None)] if delta > 0.0 else \
               [OpenSellPositionActionAPI(PositionType=PositionType.Normal, Volume=volume, StopLoss=None, TakeProfit=None)]

    def risk_management(self) -> None:
        return None

    def _hedge_(self, update: BarUpdateAPI, close: float) -> float:
        if not self._neutralize_reward_: return 0.0
        held = self._previous_exposure_
        previous_close = self._previous_bar_close_
        if not held or not previous_close or not close or previous_close <= 0.0 or close <= 0.0: return 0.0
        return self._neutralize_scale_ * held * math.log(close / previous_close)

    def _turnover_(self, update: BarUpdateAPI, close: float) -> float:
        if self._turnover_cost_ <= 0.0: return 0.0
        return self._turnover_cost_ * abs(self._held_exposure_(update, close) - self._previous_exposure_)

    def _held_exposure_(self, update: BarUpdateAPI, close: float) -> float:
        equity = update.Portfolio.Equity
        if not equity or not close: return 0.0
        return self._exposure_(update) * close / equity

    def _bucket_(self, update: BarUpdateAPI) -> Union[tuple, None]:
        if not self._decision_schedule_: return None
        moment = update.Bar.Timestamp.DateTime
        if self._decision_schedule_ == "W1": return moment.isocalendar()[:2]
        if self._decision_schedule_ == "D1": return (moment.year, moment.month, moment.day)
        span = 4 if self._decision_schedule_ == "H4" else 8 if self._decision_schedule_ == "H8" else 12 if self._decision_schedule_ == "H12" else 1
        return (moment.year, moment.month, moment.day, moment.hour // span)

    def _step_(self, update: BarUpdateAPI) -> Union[list, None]:
        observation = self._observation_.encode(update)
        equity = update.Portfolio.Equity
        close = update.Bar.CloseTick.Bid.Price
        if self.Training and self._previous_observation_ is not None:
            self._pending_reward_ += self._reward_.reward(equity, self._previous_equity_, self._hedge_(update, close) + self._turnover_(update, close))
        bucket = self._bucket_(update)
        decide = bucket != self._decision_bucket_ if bucket is not None else self._decision_index_ % self._decision_interval_ == 0
        if decide:
            self._decision_bucket_ = bucket
            if self.Training and self._previous_observation_ is not None:
                self._agent_.memorize(self._previous_observation_, self._previous_action_, self._pending_reward_, observation, False)
                self._step_index_ += 1
                if self._step_index_ % self.TrainFrequency == 0:
                    for _ in range(self.GradientSteps): self._agent_.learn()
            self._pending_reward_ = 0.0
            action = self._agent_.decide(observation, explore=self.Training)
            self._previous_observation_ = observation
            self._previous_action_ = action
            self._current_action_ = action
        else:
            action = self._current_action_
        self._decision_index_ += 1
        self._previous_equity_ = equity
        self._previous_bar_close_ = close
        self._previous_exposure_ = self._held_exposure_(update, close)
        signal = float(action[0])
        if self._signal_smoothing_ > 0.0:
            previous = self._smoothed_signal_
            signal = signal if previous is None else previous + self._signal_smoothing_ * (signal - previous)
            self._smoothed_signal_ = signal
        return self._emit_(update, self._control_(update, signal), signal)

    def _initialize_(self, _: Any) -> None:
        self._agent_.reset()
        self._observation_.reset()
        self._reward_.reset()
        self._previous_observation_ = None
        self._previous_action_ = None
        self._previous_equity_ = None
        self._previous_bar_close_ = None
        self._previous_exposure_ = 0.0
        self._smoothed_signal_ = None
        self._current_action_ = None
        self._pending_reward_ = 0.0
        self._decision_index_ = 0
        self._decision_bucket_ = None
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