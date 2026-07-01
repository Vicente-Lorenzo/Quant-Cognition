from __future__ import annotations

import math

from Library.Utility.Enumeration import EnumerationAPI

class RewardType(EnumerationAPI):
    LogReturn = 0
    VolScaledReturn = 1
    DifferentialSharpe = 2
    DifferentialSortino = 3
    DifferentialCalmar = 4

class RewardAPI:
    """
    Per-step reward encoder for the model strategies.

    Every reward is built on the equity log-return r_t = ln(E_t / E_{t-1}), which
    is scale-free (independent of account size) and additive over time. The family
    spans three categories:

      - Return type:
          LogReturn        r_t                                  (raw growth)
          VolScaledReturn  r_t / sigma_t                        (return per unit risk;
                           sigma_t = sqrt(EWMA variance of r))
      - Ratio type (online "differential" risk-adjusted ratios). All share the same
        machine: an EWMA estimate of the return numerator A_t with the risk measure
        swapped in the denominator. Accumulating the per-step reward drives the
        corresponding ratio upward.
          DifferentialSharpe   risk = standard deviation       (Moody & Saffell 2001 DSR)
          DifferentialSortino  risk = downside deviation        (Moody & Saffell DDR)
          DifferentialCalmar   risk = running max drawdown      (our extension; no paper)

    Moody & Saffell, "Learning to Trade via Direct Reinforcement" (2001):
      A_t = A_{t-1} + eta (r_t - A_{t-1}) · B_t = B_{t-1} + eta (r_t^2 - B_{t-1})
      DSR_t = (B_{t-1} dA - 0.5 A_{t-1} dB) / (B_{t-1} - A_{t-1}^2)^{3/2}
    with dA = r_t - A_{t-1}, dB = r_t^2 - B_{t-1}. The Sharpe/Sortino forms below
    follow the paper and must be validated against it for thesis use; the Calmar
    form (first difference of the online ratio A_t / |maxDD|) is our own design.

    The reward is stateful (EWMA accumulators) and must be reset per episode.
    """

    _EPSILON_ = 1e-8

    def __init__(self, kind: RewardType = RewardType.LogReturn, scale: float = 1.0, clip: float = 1.0, decay: float = 0.01, volatility_decay: float = 0.06) -> None:
        self._kind_ = kind
        self._scale_ = scale
        self._clip_ = clip
        self._decay_ = decay
        self._volatility_decay_ = volatility_decay
        self.reset()

    def reset(self) -> None:
        self._mean_ = 0.0
        self._square_ = 0.0
        self._downside_ = 0.0
        self._return_mean_ = 0.0
        self._variance_ = 0.0
        self._max_drawdown_ = 0.0
        self._calmar_value_ = 0.0
        self._initialized_ = False

    def reward(self, equity: float, previous_equity: float, drawdown: float) -> float:
        if previous_equity is None or previous_equity <= 0.0 or equity is None or equity <= 0.0:
            log_return = 0.0
        else:
            log_return = math.log(equity / previous_equity)
        value = self._scale_ * self._encode_(log_return, drawdown)
        # Reward clipping (Mnih et al. 2015) — a numerical safeguard on the learning
        # signal, applied AFTER the (bit-exact) reward encoding: the differential
        # ratios have a near-zero-risk singularity (a sustained winning streak decays
        # the downside/variance EWMA toward 0, so the cubic denominator turns a tiny
        # loss into a huge spike that diverges the critic). This does not alter the
        # Moody & Saffell formulas above nor the DDPG/SAC algorithms. clip <= 0 disables.
        if self._clip_ > 0.0:
            value = self._clip_ if value > self._clip_ else -self._clip_ if value < -self._clip_ else value
        return value

    def _encode_(self, log_return: float, drawdown: float) -> float:
        if self._kind_ == RewardType.LogReturn: return log_return
        if self._kind_ == RewardType.VolScaledReturn: return self._vol_scaled_(log_return)
        if self._kind_ == RewardType.DifferentialSharpe: return self._sharpe_(log_return)
        if self._kind_ == RewardType.DifferentialSortino: return self._sortino_(log_return)
        if self._kind_ == RewardType.DifferentialCalmar: return self._calmar_(log_return, drawdown)
        return log_return

    def _vol_scaled_(self, log_return: float) -> float:
        standardized = log_return / math.sqrt(self._variance_ + self._EPSILON_) if self._initialized_ else 0.0
        delta = log_return - self._return_mean_
        self._return_mean_ += self._volatility_decay_ * delta
        self._variance_ = (1.0 - self._volatility_decay_) * (self._variance_ + self._volatility_decay_ * delta * delta)
        self._initialized_ = True
        return standardized

    def _sharpe_(self, log_return: float) -> float:
        variance = self._square_ - self._mean_ * self._mean_
        if variance > self._EPSILON_:
            differential = (self._square_ * (log_return - self._mean_) - 0.5 * self._mean_ * (log_return * log_return - self._square_)) / (variance ** 1.5)
        else:
            differential = 0.0
        self._mean_ += self._decay_ * (log_return - self._mean_)
        self._square_ += self._decay_ * (log_return * log_return - self._square_)
        return differential

    def _sortino_(self, log_return: float) -> float:
        downside = math.sqrt(self._downside_)
        if downside > self._EPSILON_:
            if log_return > 0.0:
                differential = (log_return - 0.5 * self._mean_) / downside
            else:
                differential = (self._downside_ * (log_return - 0.5 * self._mean_) - 0.5 * self._mean_ * log_return * log_return) / (self._downside_ * downside)
        else:
            differential = 0.0
        self._mean_ += self._decay_ * (log_return - self._mean_)
        self._downside_ += self._decay_ * (min(log_return, 0.0) ** 2 - self._downside_)
        return differential

    def _calmar_(self, log_return: float, drawdown: float) -> float:
        self._mean_ += self._decay_ * (log_return - self._mean_)
        self._max_drawdown_ = min(self._max_drawdown_, drawdown)
        calmar = self._mean_ / (abs(self._max_drawdown_) + self._EPSILON_)
        differential = calmar - self._calmar_value_
        self._calmar_value_ = calmar
        return differential