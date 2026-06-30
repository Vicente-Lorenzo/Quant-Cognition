from __future__ import annotations

import math
from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import np

if TYPE_CHECKING:
    from Library.Protocol.Update import BarUpdateAPI

class _RollingNormalizer_:
    """
    Layer-2 standardization — causal EWMA z-score (no look-ahead).

    Maintains a per-feature exponential mean/variance and standardizes each value
    with statistics through the PREVIOUS step only (the current value is used after
    it is emitted). Features flagged as bounded-by-construction (sin/cos, exposure,
    drawdown) bypass this layer so their natural bounds are preserved.
    """

    _EPSILON_ = 1e-8

    def __init__(self, window: int = 200) -> None:
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
        standardized = (values - self._mean_) / np.sqrt(self._variance_ + self._EPSILON_)
        output = np.where(mask, standardized, values)
        delta = values - self._mean_
        mean = self._mean_ + self._alpha_ * delta
        variance = (1.0 - self._alpha_) * (self._variance_ + self._alpha_ * delta * delta)
        self._mean_ = np.where(mask, mean, self._mean_)
        self._variance_ = np.where(mask, variance, self._variance_)
        return output.astype(np.float32)

class ObservationAPI:
    """
    Observation encoder — the scale-free, transferable observation vector.

    The guiding principle is invariance to price level, volatility regime, and
    account size, so the agent learns patterns rather than the idiosyncrasies of one
    security. Two normalization layers achieve this: layer 1 is the per-feature
    causal encoding below (log-returns, ratios, vol-scaling, sin/cos), which makes
    every feature dimensionless; layer 2 is the optional rolling EWMA z-score
    (_RollingNormalizer_) over the unbounded features.

    Feature groups, in canonical order (essential, always present):

      Timestamp (8) — calendar cyclicality. sin/cos pairs of Month/Weekday/Hour/Minute.
                      Bounded in [-1, 1]; bypass layer 2. Constant granularities (e.g.
                      Hour/Minute on daily bars) are harmless and keep a fixed schema
                      across timeframes.
      Account (4)   — wealth trajectory, scale-free. Balance and Equity as returns from
                      initial capital; EquityDrawdown (vs running peak, bounded [-1, 0],
                      bypass) and EquityRunup (vs running trough).
      Position (4)  — open-trade state, scale-free. Signed exposure (volume / SizingMax,
                      bounded, bypass); unrealized return, max drawdown and max runup as
                      fractions of the entry balance.
      Market (5)    — bar geometry. Gap/High/Low/Close as vol-scaled log-moves vs the
                      previous close (ln(price / prev_close) / RV); Volume as ln(1 + V).
                      Price moves are already vol-scaled (bypass layer 2); volume is not.
      Indicator     — dimensionless technicals. RV as the realized volatility level
                      (return-space "true" volatility) first, then ATR as ATR/Close
                      (price-space proxy); both essential, always present. Optional
                      moving averages as (Close - MA) / ATR trend distance.

    Essential scaling denominators (RV for return-space, ATR for price-space) are
    always-on; optional features (moving averages) never appear in a denominator, so
    disabling them can never break another feature. The encoder is stateful (previous
    close + normalizer) and must be reset per episode.
    """

    def __init__(self, sizing_max: float = 1.0, realized_volatility: str = "RV", atr: str = "ATR", moving_averages: tuple = (), normalize_window: int = 200) -> None:
        self._sizing_max_ = sizing_max
        self._realized_volatility_ = realized_volatility
        self._atr_ = atr
        self._moving_averages_ = tuple(moving_averages)
        self._normalizer_ = _RollingNormalizer_(normalize_window)
        self._previous_close_: Union[float, None] = None

    def reset(self) -> None:
        self._previous_close_ = None
        self._normalizer_.reset()

    def shape(self) -> int:
        return 8 + 4 + 4 + 5 + 2 + len(self._moving_averages_)

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
            features.append((0.0, False))
            features.append((0.0, True))
            features.append((0.0, True))
            features.append((0.0, True))
            return
        signed = position.Volume if position.IsLong else -position.Volume
        entry = position.EntryBalance or 0.0
        net = position.NetPnL.PnL if position.NetPnL and position.NetPnL.PnL is not None else 0.0
        drawdown = position.MaxEquityDrawdownPnL.PnL if position.MaxEquityDrawdownPnL and position.MaxEquityDrawdownPnL.PnL is not None else 0.0
        runup = position.MaxEquityRunupPnL.PnL if position.MaxEquityRunupPnL and position.MaxEquityRunupPnL.PnL is not None else 0.0
        features.append((signed / self._sizing_max_ if self._sizing_max_ else 0.0, False))
        features.append((net / entry if entry else 0.0, True))
        features.append((drawdown / entry if entry else 0.0, True))
        features.append((runup / entry if entry else 0.0, True))

    def _market_features_(self, update: BarUpdateAPI, features: list) -> None:
        bar = update.Bar
        open_price = bar.OpenTick.Bid.Price
        high_price = bar.HighTick.Bid.Price
        low_price = bar.LowTick.Bid.Price
        close_price = bar.CloseTick.Bid.Price
        realized = self._indicator_(update, self._realized_volatility_)
        sigma = realized if realized and realized > 0.0 else 1.0
        previous = self._previous_close_
        if previous and previous > 0.0:
            features.append((math.log(open_price / previous) / sigma, False))
            features.append((math.log(high_price / previous) / sigma, False))
            features.append((math.log(low_price / previous) / sigma, False))
            features.append((math.log(close_price / previous) / sigma, False))
        else:
            features.append((0.0, False))
            features.append((0.0, False))
            features.append((0.0, False))
            features.append((0.0, False))
        features.append((math.log1p(bar.Volume or 0.0), True))
        self._previous_close_ = close_price

    def _indicator_features_(self, update: BarUpdateAPI, features: list) -> None:
        close_price = update.Bar.CloseTick.Bid.Price
        realized = self._indicator_(update, self._realized_volatility_)
        atr = self._indicator_(update, self._atr_)
        features.append((realized if realized else 0.0, True))
        features.append((atr / close_price if atr and close_price else 0.0, True))
        for name in self._moving_averages_:
            average = self._indicator_(update, name)
            features.append(((close_price - average) / atr if (average is not None and atr) else 0.0, True))

    def encode(self, update: BarUpdateAPI) -> np.ndarray:
        features: list = []
        self._timestamp_features_(update, features)
        self._account_features_(update, features)
        self._position_features_(update, features)
        self._market_features_(update, features)
        self._indicator_features_(update, features)
        values = np.array([value for value, _ in features], dtype=np.float32)
        mask = np.array([flag for _, flag in features], dtype=bool)
        return self._normalizer_.transform(values, mask)