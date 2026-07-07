from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Union, TYPE_CHECKING

from Library.Database.Dataframe import np
from Library.Engine import MachineAPI
from Library.Indicator.Indicator import parse_technical
from Library.Indicator.Technical.Technical import TechnicalType
from Library.Portfolio import PositionType
from Library.Portfolio.Sizing import SizingMode
from Library.Protocol.Update import UpdateID, BarUpdateAPI
from Library.Strategy.Model.Action import ActionAPI
from Library.Strategy.Model.Normalizer import NormalizerAPI
from Library.Strategy.Model.Observation import ObservationAPI
from Library.Strategy.Model.Reward import RewardAPI, RewardType
from Library.Strategy.Rule.NNFX import NNFXStrategyAPI
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
      Indicator     — dimensionless technicals: ATR/Close, the RV_fast level, and the
                      volatility regime ln(RV_fast / RV_slow); then one momentum feature
                      per momentum indicator (value / (RV_fast * sqrt(lookback))) and one
                      overlap feature per overlap indicator ((Close - value) / ATR).
    """

    _REALIZED_FAST_ = "RVFast"
    _REALIZED_SLOW_ = "RVSlow"
    _ATR_ = "ATR"

    def __init__(self, action: ActionAPI, momentum_features: tuple, overlap_features: tuple, normalize_window: int, window: int) -> None:
        super().__init__(normalizer=DDPGNormalizationAPI(normalize_window), window=window)
        self._action_ = action
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
        return 8 + 4 + 5 + 6 + 3 + len(self._momentum_features_) + len(self._overlap_features_)

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
        signed = position.Volume if position.IsLong else -position.Volume
        maximum = self._action_.maximum_volume(update)
        entry = position.EntryBalance or 0.0
        net = position.NetPnL.PnL if position.NetPnL and position.NetPnL.PnL is not None else 0.0
        drawdown = position.MaxEquityDrawdownPnL.PnL if position.MaxEquityDrawdownPnL and position.MaxEquityDrawdownPnL.PnL is not None else 0.0
        runup = position.MaxEquityRunupPnL.PnL if position.MaxEquityRunupPnL and position.MaxEquityRunupPnL.PnL is not None else 0.0
        features.append((max(-1.0, min(1.0, signed / maximum)) if maximum else 0.0, False))
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
        for name in self._momentum_features_:
            indicator = getattr(update.Technical, name, None)
            momentum = indicator.Result.last() if indicator is not None else None
            span = (getattr(indicator, "Window", 1) or 1) if indicator is not None else 1
            features.append((momentum / (sigma * math.sqrt(span)) if momentum is not None and math.isfinite(momentum) else 0.0, False))
        for name in self._overlap_features_:
            indicator = getattr(update.Technical, name, None)
            average = indicator.Result.last() if indicator is not None else None
            features.append(((close_price - average) / scale if (average is not None and math.isfinite(average) and scale) else 0.0, True))

    def _features_(self, update: BarUpdateAPI) -> list:
        features: list = []
        self._timestamp_features_(update, features)
        self._account_features_(update, features)
        self._position_features_(update, features)
        self._market_features_(update, features)
        self._indicator_features_(update, features)
        return features

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
                 signal_management: Parameter,
                 technical_management: Parameter,
                 fundamental_management: Parameter,
                 sentimental_management: Parameter,
                 portfolio_management: Parameter) -> None:
        super().__init__(money_management, risk_management, signal_management, technical_management, fundamental_management, sentimental_management, portfolio_management)
        self._entry_threshold_ = tuple(self.SignalManagement.NormalEntryThreshold)
        self._exit_threshold_ = tuple(self.SignalManagement.NormalExitThreshold)
        self._continuation_entry_ = tuple(self.SignalManagement.ContinuationEntryThreshold)
        self._continuation_exit_ = tuple(self.SignalManagement.ContinuationExitThreshold)
        self._continuation_delay_, = self.SignalManagement.ContinuationDelay
        self._sizing_min_, = self.MoneyManagement.SizingMin
        self._sizing_max_, = self.MoneyManagement.SizingMax
        weights = self.SignalManagement.Weights
        self._configured_weights_ = weights[0] if weights else None
        momentum, overlap = self._observation_features_()
        self._action_ = ActionAPI(mode=SizingMode.Balance, maximum=self._EXPOSURE_REFERENCE_, deadzone=0.0)
        self._observation_ = DDPGObservationAPI(action=self._action_, momentum_features=momentum, overlap_features=overlap, normalize_window=self.SignalManagement.NormalizeWindow[0], window=self.SignalManagement.ObservationWindow[0])
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
            reward = self._reward_.reward(equity, self._previous_equity_)
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