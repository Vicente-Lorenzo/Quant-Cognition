from __future__ import annotations

import math
from datetime import date
from typing import Union

from Library.Statistic.Label import (
    BENCHMARK_ALPHA,
    BENCHMARK_ALPHASIGNIFICANCE,
    BENCHMARK_ANNUALIZEDRETURN,
    BENCHMARK_BETA,
    BENCHMARK_CORRELATION,
    BENCHMARK_DOWNSIDECAPTURE,
    BENCHMARK_INFORMATIONRATIO,
    BENCHMARK_MAXDRAWDOWN,
    BENCHMARK_TOTALRETURN,
    BENCHMARK_TRACKINGERROR,
    BENCHMARK_UPSIDECAPTURE,
    BENCHMARK_VOLATILITY,
    CALMARRATIO,
    MAXEQUITYDRAWDOWNPERC,
    MAXEQUITYDRAWDOWNVALUE,
    MAXEQUITYRUNUPPERC,
    MAXEQUITYRUNUPVALUE,
    MEANEQUITYDRAWDOWNPERC,
    MEANEQUITYDRAWDOWNVALUE,
    MEANEQUITYRUNUPPERC,
    MEANEQUITYRUNUPVALUE,
    SHARPERATIO,
    SORTINORATIO,
    STERLINGRATIO
)
from Library.Utility.Math import EPSILON

def calculate_log_value(value: float) -> Union[float, None]:
    if not value or value <= 0.0: return None
    return math.log(value)

def calculate_price_return(price: float, reference: float) -> Union[float, None]:
    if not reference: return None
    return (price / reference) - 1.0

def calculate_pnl_return(pnl: float, reference: float) -> Union[float, None]:
    if not reference: return None
    return pnl / reference

def calculate_log_return(ret: float) -> Union[float, None]:
    if ret is None or ret <= -1.0: return None
    return math.log1p(ret)

def calculate_percentage(ret: float) -> Union[float, None]:
    if ret is None: return None
    return ret * 100.0

def calculate_log_percentage(log_ret: float) -> Union[float, None]:
    if log_ret is None: return None
    return log_ret * 100.0

def calculate_duration_seconds(start: date, stop: date) -> float:
    if not start or not stop: return 0.0
    return (stop - start).days * 86400.0

def calculate_annualized_return(ret: float, duration_seconds: float, trading_days: int = 365, pct: bool = False) -> float:
    if not ret or not duration_seconds or duration_seconds <= 0.0: return 0.0
    ret = ret / 100.0 if pct else ret
    value = ((1.0 + ret) ** ((trading_days * 86400.0) / duration_seconds)) - 1.0
    return calculate_percentage(value) if pct else value

def calculate_annualized_log_return(log_ret: float, duration_seconds: float, trading_days: int = 365) -> float:
    if log_ret is None or not duration_seconds or duration_seconds <= 0.0: return 0.0
    return log_ret * ((trading_days * 86400.0) / duration_seconds)

def calculate_pnl_difference(current_price: float, entry_price: float, is_long: bool) -> float:
    return (current_price - entry_price) if is_long else (entry_price - current_price)

def calculate_gross_pnl(pnl_diff: float, volume: float, conversion: float = 1.0) -> float:
    return pnl_diff * volume * conversion

def calculate_net_pnl(gross_pnl: float, commission_pnl: float, swap_pnl: float) -> float:
    return gross_pnl + commission_pnl + swap_pnl

def calculate_rate_perc(nr_cases: int, nr_total: int) -> float:
    return (nr_cases / nr_total) * 100.0 if nr_total else 0.0

def calculate_average(net_value: float, nr_items: int) -> float:
    return net_value / nr_items if nr_items else 0.0

def calculate_expected(winning_perc: float, avg_win: float, losing_perc: float, avg_loss: float) -> float:
    return (winning_perc / 100.0 * avg_win) + (losing_perc / 100.0 * avg_loss)

def calculate_annualized_volatility(vol: float, nr_trades: int, duration_seconds: float, trading_days: int = 365, pct: bool = False) -> float:
    if not vol or not nr_trades or not duration_seconds or duration_seconds <= 0.0: return 0.0
    vol = vol / 100.0 if pct else vol
    value = vol * math.sqrt(nr_trades * (trading_days * 86400.0) / duration_seconds)
    return calculate_percentage(value) if pct else value

def calculate_risk_to_reward(avg_win: float, avg_loss: float) -> float:
    if avg_win: return abs(avg_loss) / avg_win
    return math.inf if avg_loss else 0.0

def calculate_profit_factor(win_pnl: float, loss_pnl: float) -> float:
    if loss_pnl: return win_pnl / abs(loss_pnl)
    return math.inf if win_pnl > 0 else 0.0

def calculate_ratio(ann_ret_pct: float, risk_pct: float, rfr: float = 0.0) -> float:
    risk_pct = abs(risk_pct) if risk_pct else 1e-2
    return (ann_ret_pct - rfr) / risk_pct

def calculate_sharpe(ann_ret_pct: float, ann_vol_pct: float, rfr: float = 0.0) -> float:
    return calculate_ratio(ann_ret_pct, ann_vol_pct, rfr)

def calculate_sortino(ann_ret_pct: float, down_vol_pct: float, rfr: float = 0.0) -> float:
    return calculate_ratio(ann_ret_pct, down_vol_pct, rfr)

def calculate_calmar(ann_ret_pct: float, max_dd_pct: float, rfr: float = 0.0) -> float:
    return calculate_ratio(ann_ret_pct, max_dd_pct, rfr)

def calculate_sterling(ann_ret_pct: float, mean_dd_pct: float, rfr: float = 0.0) -> float:
    return calculate_ratio(ann_ret_pct, mean_dd_pct, rfr)

def equity_curve_ratios(curve: Union[list, None], start: date, stop: date, trading_days: int = 365, max_drawdown: Union[float, None] = None, mean_drawdown: Union[float, None] = None) -> Union[dict, None]:
    if not curve or len(curve) < 2: return None
    returns = [(curve[i] / curve[i - 1] - 1.0) if curve[i - 1] else 0.0 for i in range(1, len(curve))]
    n = len(returns)
    duration_seconds = calculate_duration_seconds(start, stop)
    years = duration_seconds / (trading_days * 86400.0) if duration_seconds and duration_seconds > 0.0 else 0.0
    periods = n / years if years > 0.0 else 0.0
    annualize = math.sqrt(periods) if periods > 0.0 else 0.0
    mean = sum(returns) / n
    variance = sum((value - mean) ** 2 for value in returns) / (n - 1) if n > 1 else 0.0
    deviation = math.sqrt(variance)
    downside = math.sqrt(sum(value ** 2 for value in returns if value < 0.0) / n)
    sharpe = (mean / deviation) * annualize if deviation > 0.0 else 0.0
    sortino = (mean / downside) * annualize if downside > 0.0 else 0.0
    if max_drawdown is None or mean_drawdown is None:
        peak, curve_max, curve_sum = curve[0], 0.0, 0.0
        for value in curve:
            if value > peak: peak = value
            drawdown = (peak - value) / peak if peak else 0.0
            if drawdown > curve_max: curve_max = drawdown
            curve_sum += drawdown
        max_drawdown = curve_max if max_drawdown is None else max_drawdown
        mean_drawdown = curve_sum / len(curve) if mean_drawdown is None else mean_drawdown
    total_return = (curve[-1] / curve[0] - 1.0) if curve[0] else 0.0
    annualized_return = ((1.0 + total_return) ** (1.0 / years) - 1.0) if years > 0.0 and (1.0 + total_return) > 0.0 else 0.0
    calmar = annualized_return / max_drawdown if max_drawdown > 0.0 else 0.0
    sterling = annualized_return / mean_drawdown if mean_drawdown > 0.0 else 0.0
    return {SHARPERATIO: sharpe, SORTINORATIO: sortino, CALMARRATIO: calmar, STERLINGRATIO: sterling}

def equity_excursion(excursions: dict) -> dict:
    return {
        MAXEQUITYDRAWDOWNVALUE: excursions["max_drawdown_value"],
        MAXEQUITYDRAWDOWNPERC: excursions["max_drawdown"] * 100.0,
        MEANEQUITYDRAWDOWNVALUE: excursions["mean_drawdown_value"],
        MEANEQUITYDRAWDOWNPERC: excursions["mean_drawdown"] * 100.0,
        MAXEQUITYRUNUPVALUE: excursions["max_runup_value"],
        MAXEQUITYRUNUPPERC: excursions["max_runup"] * 100.0,
        MEANEQUITYRUNUPVALUE: excursions["mean_runup_value"],
        MEANEQUITYRUNUPPERC: excursions["mean_runup"] * 100.0
    }

def align_series(spine: list, series: list) -> list:
    if not spine or not series: return []
    aligned, index, current = [], 0, None
    for stamp in spine:
        while index < len(series) and series[index][0] <= stamp:
            current = series[index][1]
            index += 1
        aligned.append(current)
    return aligned

def series_returns(values: list) -> list:
    return [(values[i] / values[i - 1] - 1.0) if values[i - 1] and values[i] is not None and values[i - 1] is not None else None for i in range(1, len(values))]

def standalone_metrics(values: list, start: date, stop: date, trading_days: int = 365, risk_free: float = 0.0) -> dict:
    clean = [value for value in values if value]
    if len(clean) < 2: return {}
    returns = [value for value in series_returns(values) if value is not None]
    count = len(returns)
    duration_seconds = calculate_duration_seconds(start, stop)
    years = duration_seconds / (trading_days * 86400.0) if duration_seconds and duration_seconds > 0.0 else 0.0
    periods = count / years if years > 0.0 else 0.0
    mean = sum(returns) / count if count else 0.0
    variance = sum((value - mean) ** 2 for value in returns) / (count - 1) if count > 1 else 0.0
    deviation = math.sqrt(variance)
    total_return = clean[-1] / clean[0] - 1.0 if clean[0] else 0.0
    annualized = ((1.0 + total_return) ** (1.0 / years) - 1.0) if years > 0.0 and (1.0 + total_return) > 0.0 else 0.0
    peak, drawdown_max, drawdown_sum = clean[0], 0.0, 0.0
    for value in clean:
        if value > peak: peak = value
        drawdown = (peak - value) / peak if peak else 0.0
        drawdown_sum += drawdown
        if drawdown > drawdown_max: drawdown_max = drawdown
    drawdown_mean = drawdown_sum / len(clean)
    downside = math.sqrt(sum(value ** 2 for value in returns if value < 0.0) / count) if count else 0.0
    annualize = math.sqrt(periods) if periods > 0.0 else 0.0
    rate = ((1.0 + risk_free) ** (1.0 / periods) - 1.0) if periods > 0.0 and risk_free else 0.0
    sharpe = ((mean - rate) / deviation) * annualize if deviation > EPSILON and periods > 0.0 else 0.0
    sortino = ((mean - rate) / downside) * annualize if downside > EPSILON and periods > 0.0 else 0.0
    calmar = (annualized - risk_free) / drawdown_max if drawdown_max > EPSILON else 0.0
    sterling = (annualized - risk_free) / drawdown_mean if drawdown_mean > EPSILON else 0.0
    return {
        BENCHMARK_TOTALRETURN: total_return * 100.0, BENCHMARK_ANNUALIZEDRETURN: annualized * 100.0,
        BENCHMARK_VOLATILITY: deviation * annualize * 100.0 if periods > 0.0 else 0.0,
        BENCHMARK_MAXDRAWDOWN: drawdown_max * 100.0,
        SHARPERATIO: sharpe, SORTINORATIO: sortino, CALMARRATIO: calmar, STERLINGRATIO: sterling,
        "_periods_": periods, "_total_": total_return
    }

def daily_series(spine: list, values: list) -> list:
    closes = {}
    for stamp, value in zip(spine, values):
        if value is None: continue
        moment = getattr(stamp, "date", None)
        closes[moment() if callable(moment) else stamp] = value
    return [closes[key] for key in sorted(closes)]

def relative_metrics(strategy: list, benchmark: list, periods: float, risk_free: float = 0.0, annual: float = None, reference: float = None) -> dict:
    pairs = [(first, second) for first, second in zip(series_returns(strategy), series_returns(benchmark)) if first is not None and second is not None]
    count = len(pairs)
    if count < 2: return {}
    rate = ((1.0 + risk_free) ** (1.0 / periods) - 1.0) if periods > 0.0 and risk_free else 0.0
    strategy_returns = [first for first, _ in pairs]
    benchmark_returns = [second for _, second in pairs]
    strategy_mean = sum(strategy_returns) / count
    benchmark_mean = sum(benchmark_returns) / count
    covariance = sum((first - strategy_mean) * (second - benchmark_mean) for first, second in pairs) / (count - 1)
    strategy_variance = sum((value - strategy_mean) ** 2 for value in strategy_returns) / (count - 1)
    benchmark_variance = sum((value - benchmark_mean) ** 2 for value in benchmark_returns) / (count - 1)
    deviation = math.sqrt(strategy_variance * benchmark_variance)
    correlation = covariance / deviation if deviation > EPSILON else 0.0
    beta = covariance / benchmark_variance if benchmark_variance > EPSILON else 0.0
    excess = (strategy_mean - rate) - beta * (benchmark_mean - rate)
    alpha = (annual - (risk_free + beta * (reference - risk_free))) if annual is not None and reference is not None else excess * periods
    residuals = [(first - rate) - excess - beta * (second - rate) for first, second in pairs]
    residual_mean = sum(residuals) / count
    residual_deviation = math.sqrt(sum((value - residual_mean) ** 2 for value in residuals) / (count - 1))
    significance = excess / (residual_deviation / math.sqrt(count)) if residual_deviation > EPSILON else 0.0
    differences = [first - second for first, second in pairs]
    difference_mean = sum(differences) / count
    difference_deviation = math.sqrt(sum((value - difference_mean) ** 2 for value in differences) / (count - 1))
    tracking = difference_deviation * math.sqrt(periods) if periods > 0.0 else 0.0
    information = (difference_mean / difference_deviation) * math.sqrt(periods) if difference_deviation > EPSILON and periods > 0.0 else 0.0
    upside = [(first, second) for first, second in pairs if second > 0.0]
    downside = [(first, second) for first, second in pairs if second < 0.0]
    def capture(sample: list) -> Union[float, None]:
        if not sample: return None
        reference = sum(second for _, second in sample) / len(sample)
        return (sum(first for first, _ in sample) / len(sample)) / reference * 100.0 if abs(reference) > EPSILON else None
    return {
        BENCHMARK_CORRELATION: correlation, BENCHMARK_BETA: beta, BENCHMARK_ALPHA: alpha * 100.0,
        BENCHMARK_ALPHASIGNIFICANCE: significance,
        BENCHMARK_TRACKINGERROR: tracking * 100.0, BENCHMARK_INFORMATIONRATIO: information,
        BENCHMARK_UPSIDECAPTURE: capture(upside), BENCHMARK_DOWNSIDECAPTURE: capture(downside)
    }

__all__ = ["calculate_log_value", "calculate_price_return", "calculate_pnl_return", "calculate_log_return", "calculate_percentage", "calculate_log_percentage", "calculate_duration_seconds", "calculate_annualized_return", "calculate_annualized_log_return", "calculate_pnl_difference", "calculate_gross_pnl", "calculate_net_pnl", "calculate_rate_perc", "calculate_average", "calculate_expected", "calculate_annualized_volatility", "calculate_risk_to_reward", "calculate_profit_factor", "calculate_ratio", "calculate_sharpe", "calculate_sortino", "calculate_calmar", "calculate_sterling", "equity_curve_ratios", "equity_excursion", "align_series", "series_returns", "standalone_metrics", "daily_series", "relative_metrics"]