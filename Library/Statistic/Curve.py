import math
from array import array
from datetime import datetime
from typing import Union

from Library.Database.Dataframe import np
from Library.Statistic.Label import (
    CALMARRATIO,
    CALMARRATIOANN,
    DOWNSIDEVOLATILITYANNPERC,
    DOWNSIDEVOLATILITYPERC,
    MAXEQUITYDRAWDOWNPERC,
    MAXEQUITYDRAWDOWNVALUE,
    MAXEQUITYRUNUPPERC,
    MAXEQUITYRUNUPVALUE,
    MEANEQUITYDRAWDOWNPERC,
    MEANEQUITYDRAWDOWNVALUE,
    MEANEQUITYRUNUPPERC,
    MEANEQUITYRUNUPVALUE,
    NETVOLATILITYANNPERC,
    NETVOLATILITYPERC,
    RISKFREERATEPERC,
    SHARPERATIO,
    SHARPERATIOANN,
    SORTINORATIO,
    SORTINORATIOANN,
    STERLINGRATIO,
    STERLINGRATIOANN,
    UPSIDEVOLATILITYANNPERC,
    UPSIDEVOLATILITYPERC
)
from Library.Statistic.Metric import calculate_annualized_return, calculate_annualized_volatility, calculate_duration_seconds
from Library.Utility.Math import EPSILON
from Library.Utility.Typing import MISSING

class CurveAPI:

    _YEAR_ = 365 * 86400.0
    _BATCH_ = 64

    def __init__(self, risk_free: float = 0.0) -> None:
        self._risk_free_: float = risk_free
        self._stamps_: list = []
        self._values_: array = array("d")
        self._points_: array = array("d")
        self._observed_: int = 0
        self._counted_: int = 0
        self._peak_: Union[float, None] = None
        self._trough_: Union[float, None] = None
        self._max_drawdown_: float = 0.0
        self._max_drawdown_value_: float = 0.0
        self._max_runup_: float = 0.0
        self._max_runup_value_: float = 0.0
        self._drawdown_sum_: float = 0.0
        self._drawdown_value_sum_: float = 0.0
        self._runup_sum_: float = 0.0
        self._runup_value_sum_: float = 0.0
        self._settled_: int = 0
        self._sum_: float = 0.0
        self._squares_: float = 0.0
        self._gains_: float = 0.0
        self._losses_: float = 0.0

    @staticmethod
    def _largest_(current: float, values) -> float:
        largest = float(values.max())
        return largest if largest > current else current

    @staticmethod
    def _summed_(current: float, values) -> float:
        return float(np.add.accumulate(np.concatenate(((current,), values)))[-1])

    @staticmethod
    def _ratio_(numerator: float, denominator: float) -> float:
        return numerator / denominator if denominator > EPSILON else 0.0

    def _accumulate_(self, value: float) -> None:
        if not math.isfinite(value): return
        self._counted_ += 1
        if self._peak_ is None or value > self._peak_: self._peak_ = value
        if self._trough_ is None or value < self._trough_: self._trough_ = value
        drawdown_value = self._peak_ - value
        runup_value = value - self._trough_
        drawdown = drawdown_value / self._peak_ if self._peak_ else 0.0
        runup = runup_value / self._trough_ if self._trough_ else 0.0
        if drawdown > self._max_drawdown_: self._max_drawdown_ = drawdown
        if drawdown_value > self._max_drawdown_value_: self._max_drawdown_value_ = drawdown_value
        if runup > self._max_runup_: self._max_runup_ = runup
        if runup_value > self._max_runup_value_: self._max_runup_value_ = runup_value
        self._drawdown_sum_ += drawdown
        self._drawdown_value_sum_ += drawdown_value
        self._runup_sum_ += runup
        self._runup_value_sum_ += runup_value

    def _vectorize_(self, count: int) -> None:
        points = np.frombuffer(self._points_[self._observed_:count], dtype=np.float64)
        points = points[np.isfinite(points)]
        if not points.size: return
        self._counted_ += points.size
        peaks, troughs = np.maximum.accumulate(points), np.minimum.accumulate(points)
        if self._peak_ is not None:
            np.maximum(peaks, self._peak_, out=peaks)
            np.minimum(troughs, self._trough_, out=troughs)
        drawdown_values, runup_values = peaks - points, points - troughs
        drawdowns = np.divide(drawdown_values, peaks, out=np.zeros_like(points), where=peaks != 0.0)
        runups = np.divide(runup_values, troughs, out=np.zeros_like(points), where=troughs != 0.0)
        self._peak_, self._trough_ = float(peaks[-1]), float(troughs[-1])
        self._max_drawdown_ = self._largest_(self._max_drawdown_, drawdowns)
        self._max_drawdown_value_ = self._largest_(self._max_drawdown_value_, drawdown_values)
        self._max_runup_ = self._largest_(self._max_runup_, runups)
        self._max_runup_value_ = self._largest_(self._max_runup_value_, runup_values)
        self._drawdown_sum_ = self._summed_(self._drawdown_sum_, drawdowns)
        self._drawdown_value_sum_ = self._summed_(self._drawdown_value_sum_, drawdown_values)
        self._runup_sum_ = self._summed_(self._runup_sum_, runups)
        self._runup_value_sum_ = self._summed_(self._runup_value_sum_, runup_values)

    def _excurse_(self) -> None:
        count = len(self._points_)
        if count == self._observed_: return
        if count - self._observed_ > self._BATCH_: self._vectorize_(count)
        else:
            for index in range(self._observed_, count): self._accumulate_(self._points_[index])
        self._observed_ = count

    def _return_(self, index: int) -> float:
        previous = self._values_[index - 1]
        return self._values_[index] / previous - 1.0 if previous else 0.0

    def _commit_(self, value: float) -> None:
        self._sum_ += value
        self._squares_ += value * value
        if value > 0.0: self._gains_ += value * value
        elif value < 0.0: self._losses_ += value * value

    def _settle_(self) -> None:
        target = len(self._values_) - 2
        if target <= self._settled_: return
        if target - self._settled_ > self._BATCH_:
            values = np.frombuffer(self._values_[self._settled_:target + 1], dtype=np.float64)
            previous, current = values[:-1], values[1:]
            returns = np.divide(current, previous, out=np.ones_like(current), where=previous != 0.0) - 1.0
            squares = returns * returns
            self._sum_ = self._summed_(self._sum_, returns)
            self._squares_ = self._summed_(self._squares_, squares)
            self._gains_ = self._summed_(self._gains_, np.where(returns > 0.0, squares, 0.0))
            self._losses_ = self._summed_(self._losses_, np.where(returns < 0.0, squares, 0.0))
        else:
            for index in range(self._settled_ + 1, target + 1): self._commit_(self._return_(index))
        self._settled_ = target

    def _dispersion_(self) -> tuple[int, float, float, float, float]:
        self._settle_()
        count, total, squares, gains, losses = self._settled_, self._sum_, self._squares_, self._gains_, self._losses_
        if len(self._values_) - 1 > count:
            value = self._return_(len(self._values_) - 1)
            count, total, squares = count + 1, total + value, squares + value * value
            if value > 0.0: gains += value * value
            elif value < 0.0: losses += value * value
        if not count: return 0, 0.0, 0.0, 0.0, 0.0
        mean = total / count
        variance = (squares - total * mean) / (count - 1) if count > 1 else 0.0
        return count, mean, math.sqrt(variance) if variance > 0.0 else 0.0, math.sqrt(gains / count), math.sqrt(losses / count)

    def _periods_(self, count: int, duration: float) -> float:
        return count * self._YEAR_ / duration if duration > 0.0 else 0.0

    def _rate_(self, periods: float) -> float:
        return (1.0 + self._risk_free_) ** (1.0 / periods) - 1.0 if periods > 0.0 and self._risk_free_ else 0.0

    def _excess_(self, duration: float, annualized: bool) -> float:
        if annualized: return calculate_annualized_return(self.Return, duration) - self._risk_free_
        growth = (1.0 + self._risk_free_) ** (duration / self._YEAR_) - 1.0 if duration > 0.0 and self._risk_free_ else 0.0
        return self.Return - growth

    def _sharpe_(self, duration: float, annualized: bool) -> float:
        count, mean, volatility, _, _ = self._dispersion_()
        periods = self._periods_(count, duration)
        return self._ratio_(mean - self._rate_(periods), volatility) * (math.sqrt(periods) if annualized else 1.0)

    def _sortino_(self, duration: float, annualized: bool) -> float:
        count, mean, _, _, downside = self._dispersion_()
        periods = self._periods_(count, duration)
        return self._ratio_(mean - self._rate_(periods), downside) * (math.sqrt(periods) if annualized else 1.0)

    def _calmar_(self, duration: float, annualized: bool) -> float:
        return self._ratio_(self._excess_(duration, annualized), self.MaxDrawdown)

    def _sterling_(self, duration: float, annualized: bool) -> float:
        return self._ratio_(self._excess_(duration, annualized), self.MeanDrawdown)

    @property
    def RiskFree(self) -> float:
        return self._risk_free_
    @RiskFree.setter
    def RiskFree(self, value: float) -> None:
        self._risk_free_ = value or 0.0

    @property
    def Count(self) -> int:
        return max(len(self._values_) - 1, 0)

    @property
    def Stamps(self) -> list:
        return list(self._stamps_)

    @property
    def Values(self) -> list:
        return self._values_.tolist()

    @property
    def Track(self) -> list:
        return list(zip(self._stamps_, self._values_))

    @property
    def Start(self) -> Union[datetime, None]:
        return self._stamps_[0] if self._stamps_ else None

    @property
    def Stop(self) -> Union[datetime, None]:
        return self._stamps_[-1] if self._stamps_ else None

    @property
    def Duration(self) -> float:
        return calculate_duration_seconds(self._stamps_[0], self._stamps_[-1]) if len(self._stamps_) > 1 else 0.0

    @property
    def Origin(self) -> Union[float, None]:
        return self._values_[0] if self._values_ else None

    @property
    def Value(self) -> Union[float, None]:
        return self._values_[-1] if self._values_ else None

    @property
    def Return(self) -> float:
        return self._values_[-1] / self._values_[0] - 1.0 if self._values_ and self._values_[0] else 0.0

    @property
    def AnnualizedReturn(self) -> float:
        return calculate_annualized_return(self.Return, self.Duration)

    @property
    def Peak(self) -> Union[float, None]:
        self._excurse_()
        return self._peak_

    @property
    def Trough(self) -> Union[float, None]:
        self._excurse_()
        return self._trough_

    @property
    def Drawdown(self) -> float:
        peak, value = self.Peak, self.Value
        return (peak - value) / peak if peak and value is not None and value < peak else 0.0

    @property
    def Runup(self) -> float:
        trough, value = self.Trough, self.Value
        return (value - trough) / trough if trough and value is not None and value > trough else 0.0

    @property
    def MaxDrawdown(self) -> float:
        self._excurse_()
        return self._max_drawdown_

    @property
    def MaxDrawdownValue(self) -> float:
        self._excurse_()
        return self._max_drawdown_value_

    @property
    def MeanDrawdown(self) -> float:
        self._excurse_()
        return self._drawdown_sum_ / self._counted_ if self._counted_ else 0.0

    @property
    def MeanDrawdownValue(self) -> float:
        self._excurse_()
        return self._drawdown_value_sum_ / self._counted_ if self._counted_ else 0.0

    @property
    def MaxRunup(self) -> float:
        self._excurse_()
        return self._max_runup_

    @property
    def MaxRunupValue(self) -> float:
        self._excurse_()
        return self._max_runup_value_

    @property
    def MeanRunup(self) -> float:
        self._excurse_()
        return self._runup_sum_ / self._counted_ if self._counted_ else 0.0

    @property
    def MeanRunupValue(self) -> float:
        self._excurse_()
        return self._runup_value_sum_ / self._counted_ if self._counted_ else 0.0

    @property
    def Periods(self) -> float:
        return self._periods_(self.Count, self.Duration)

    @property
    def Mean(self) -> float:
        return self._dispersion_()[1]

    @property
    def Volatility(self) -> float:
        return self._dispersion_()[2]

    @property
    def UpsideVolatility(self) -> float:
        return self._dispersion_()[3]

    @property
    def DownsideVolatility(self) -> float:
        return self._dispersion_()[4]

    @property
    def AnnualizedVolatility(self) -> float:
        return calculate_annualized_volatility(self.Volatility, self.Count, self.Duration)

    @property
    def AnnualizedUpsideVolatility(self) -> float:
        return calculate_annualized_volatility(self.UpsideVolatility, self.Count, self.Duration)

    @property
    def AnnualizedDownsideVolatility(self) -> float:
        return calculate_annualized_volatility(self.DownsideVolatility, self.Count, self.Duration)

    @property
    def SharpeRatio(self) -> float:
        return self._sharpe_(self.Duration, False)

    @property
    def SharpeRatioAnnualized(self) -> float:
        return self._sharpe_(self.Duration, True)

    @property
    def SortinoRatio(self) -> float:
        return self._sortino_(self.Duration, False)

    @property
    def SortinoRatioAnnualized(self) -> float:
        return self._sortino_(self.Duration, True)

    @property
    def CalmarRatio(self) -> float:
        return self._calmar_(self.Duration, False)

    @property
    def CalmarRatioAnnualized(self) -> float:
        return self._calmar_(self.Duration, True)

    @property
    def SterlingRatio(self) -> float:
        return self._sterling_(self.Duration, False)

    @property
    def SterlingRatioAnnualized(self) -> float:
        return self._sterling_(self.Duration, True)

    def record(self, stamp: datetime, value: float) -> None:
        if self._stamps_ and self._stamps_[-1] == stamp: self._values_[-1] = value
        else:
            self._stamps_.append(stamp)
            self._values_.append(value)

    def observe(self, *values: float) -> None:
        self._points_.extend(values)

    def metrics(self, start: datetime = MISSING, stop: datetime = MISSING) -> dict:
        duration = calculate_duration_seconds(start, stop) if start and stop else self.Duration
        count, _, volatility, upside, downside = self._dispersion_()
        scale = math.sqrt(self._periods_(count, duration))
        return {
            UPSIDEVOLATILITYPERC: upside * 100.0,
            UPSIDEVOLATILITYANNPERC: upside * scale * 100.0,
            DOWNSIDEVOLATILITYPERC: downside * 100.0,
            DOWNSIDEVOLATILITYANNPERC: downside * scale * 100.0,
            NETVOLATILITYPERC: volatility * 100.0,
            NETVOLATILITYANNPERC: volatility * scale * 100.0,
            MAXEQUITYDRAWDOWNVALUE: self.MaxDrawdownValue,
            MAXEQUITYDRAWDOWNPERC: self.MaxDrawdown * 100.0,
            MEANEQUITYDRAWDOWNVALUE: self.MeanDrawdownValue,
            MEANEQUITYDRAWDOWNPERC: self.MeanDrawdown * 100.0,
            MAXEQUITYRUNUPVALUE: self.MaxRunupValue,
            MAXEQUITYRUNUPPERC: self.MaxRunup * 100.0,
            MEANEQUITYRUNUPVALUE: self.MeanRunupValue,
            MEANEQUITYRUNUPPERC: self.MeanRunup * 100.0,
            RISKFREERATEPERC: self._risk_free_ * 100.0,
            SHARPERATIO: self._sharpe_(duration, False),
            SHARPERATIOANN: self._sharpe_(duration, True),
            SORTINORATIO: self._sortino_(duration, False),
            SORTINORATIOANN: self._sortino_(duration, True),
            CALMARRATIO: self._calmar_(duration, False),
            CALMARRATIOANN: self._calmar_(duration, True),
            STERLINGRATIO: self._sterling_(duration, False),
            STERLINGRATIOANN: self._sterling_(duration, True)
        }

__all__ = ["CurveAPI"]