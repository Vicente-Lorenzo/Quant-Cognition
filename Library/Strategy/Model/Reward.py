from __future__ import annotations

import math

from Library.Utility.Enumeration import EnumerationAPI
from Library.Utility.Math import EPSILON

class RewardType(EnumerationAPI):
    LogReturn = 0
    DifferentialSharpe = 1
    DifferentialSortino = 2

class RewardAPI:
    """
    Per-step reward encoder for direct-reinforcement trading agents.

    Every reward is built on the equity log-return r_t = ln(E_t / E_{t-1}), which
    is scale-free (independent of account size) and additive over time. Summing the
    per-step log returns telescopes to ln(E_T / E_0), so maximizing their (discounted)
    sum maximizes terminal compounded wealth. The family spans two categories:

      - Return type:
          LogReturn        r_t                                  (raw growth)
      - Ratio type (online "differential" risk-adjusted ratios). Both share the same
        machine: an EWMA estimate of the return numerator A_t with the risk measure
        swapped in the denominator. Accumulating the per-step reward drives the
        corresponding ratio upward.
          DifferentialSharpe   risk = standard deviation       (Moody & Saffell 2001 DSR)
          DifferentialSortino  risk = downside deviation        (Moody & Saffell DDR)

    Moody & Saffell, "Learning to Trade via Direct Reinforcement" (2001):
      A_t = A_{t-1} + eta (r_t - A_{t-1}) · B_t = B_{t-1} + eta (r_t^2 - B_{t-1})
      DSR_t = (B_{t-1} dA - 0.5 A_{t-1} dB) / (B_{t-1} - A_{t-1}^2)^{3/2}
    with dA = r_t - A_{t-1}, dB = r_t^2 - B_{t-1}. The Sharpe/Sortino forms below
    follow the paper and must be validated against it for thesis use.

    The reward is stateful (EWMA accumulators) and must be reset per episode.

    Optional market-neutralization (hedge, default 0.0 = exact formulas above): the
    caller may pass the exposure-weighted market log-return of the elapsed step as
    `hedge`, which is subtracted from the equity log-return BEFORE the encoding.
    A statically-directional policy then earns ~zero reward and only conditional
    timing (directional exposure that predicts the next step) is reinforced; this
    removes the incentive to collapse onto the training set's dominant drift.
    """

    def __init__(self, kind: RewardType = RewardType.LogReturn, scale: float = 1.0, clip: float = 1.0, decay: float = 0.01) -> None:
        self._kind_ = kind
        self._scale_ = scale
        self._clip_ = clip
        self._decay_ = decay
        self.reset()

    def reset(self) -> None:
        self._mean_ = 0.0
        self._square_ = 0.0
        self._downside_ = 0.0

    def reward(self, equity: float, previous_equity: float, hedge: float = 0.0) -> float:
        if previous_equity is None or previous_equity <= 0.0 or equity is None or equity <= 0.0:
            log_return = 0.0
        else:
            log_return = math.log(equity / previous_equity) - hedge
        value = self._scale_ * self._encode_(log_return)
        # Reward clipping (Mnih et al. 2015) — a numerical safeguard on the learning
        # signal, applied AFTER the (bit-exact) reward encoding: the differential
        # ratios have a near-zero-risk singularity (a sustained winning streak decays
        # the downside/variance EWMA toward 0, so the cubic denominator turns a tiny
        # loss into a huge spike that diverges the critic). This does not alter the
        # Moody & Saffell formulas above nor the DDPG/SAC algorithms. clip <= 0 disables.
        if self._clip_ > 0.0:
            value = self._clip_ if value > self._clip_ else -self._clip_ if value < -self._clip_ else value
        return value

    def _encode_(self, log_return: float) -> float:
        if self._kind_ == RewardType.LogReturn: return log_return
        if self._kind_ == RewardType.DifferentialSharpe: return self._sharpe_(log_return)
        if self._kind_ == RewardType.DifferentialSortino: return self._sortino_(log_return)
        return log_return

    def _sharpe_(self, log_return: float) -> float:
        variance = self._square_ - self._mean_ * self._mean_
        if variance > EPSILON:
            differential = (self._square_ * (log_return - self._mean_) - 0.5 * self._mean_ * (log_return * log_return - self._square_)) / (variance ** 1.5)
        else:
            differential = 0.0
        self._mean_ += self._decay_ * (log_return - self._mean_)
        self._square_ += self._decay_ * (log_return * log_return - self._square_)
        return differential

    def _sortino_(self, log_return: float) -> float:
        downside = math.sqrt(self._downside_)
        if downside > EPSILON:
            if log_return > 0.0:
                differential = (log_return - 0.5 * self._mean_) / downside
            else:
                differential = (self._downside_ * (log_return - 0.5 * self._mean_) - 0.5 * self._mean_ * log_return * log_return) / (self._downside_ * downside)
        else:
            differential = 0.0
        self._mean_ += self._decay_ * (log_return - self._mean_)
        self._downside_ += self._decay_ * (min(log_return, 0.0) ** 2 - self._downside_)
        return differential