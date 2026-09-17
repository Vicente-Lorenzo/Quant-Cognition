import math
import random
from datetime import date, datetime, timedelta

from Library.Statistic.Curve import CurveAPI
from Library.Statistic.Label import (
    CALMARRATIO,
    CALMARRATIOANN,
    MAXEQUITYDRAWDOWNPERC,
    NETVOLATILITYANNPERC,
    NETVOLATILITYPERC,
    RISKFREERATEPERC,
    SHARPERATIO,
    SHARPERATIOANN,
    SORTINORATIO,
    SORTINORATIOANN,
    STERLINGRATIO,
    STERLINGRATIOANN
)

START = datetime(2021, 1, 1)

def _curve_(values, spacing=timedelta(days=365) / 2, risk_free=0.0):
    curve = CurveAPI(risk_free=risk_free)
    for index, value in enumerate(values):
        curve.record(START + spacing * index, value)
        curve.observe(value)
    return curve

def _walk_(bars=5000, seed=7):
    generator = random.Random(seed)
    equity, rows = 10000.0, []
    for index in range(bars):
        equity *= 1.0 + generator.gauss(0.00002, 0.002)
        rows.append((START + timedelta(hours=index), equity, equity * (1.0 + abs(generator.gauss(0.0, 0.001))), equity * (1.0 - abs(generator.gauss(0.0, 0.001)))))
    return rows

def _state_(curve):
    return (curve.MaxDrawdown, curve.MaxDrawdownValue, curve.MeanDrawdown, curve.MeanDrawdownValue, curve.MaxRunup, curve.MaxRunupValue, curve.MeanRunup, curve.MeanRunupValue, curve.Peak, curve.Trough, curve.Mean, curve.Volatility, curve.UpsideVolatility, curve.DownsideVolatility)

def _replay_(rows, batch, reads):
    curve = CurveAPI()
    curve._BATCH_ = batch
    for index, (stamp, close, high, low) in enumerate(rows):
        curve.record(stamp, close * 1.001)
        curve.record(stamp, close)
        curve.observe(high, low, close)
        if reads and index % reads == 0: _state_(curve)
    return curve

def test_an_empty_or_flat_curve_reports_zeros():
    assert all(value == 0.0 for value in CurveAPI().metrics(date(2021, 1, 1), date(2022, 1, 1)).values())
    flat = _curve_([100.0, 100.0, 100.0])
    assert flat.SharpeRatioAnnualized == 0.0 and flat.SortinoRatioAnnualized == 0.0 and flat.CalmarRatioAnnualized == 0.0
    assert flat.Volatility == 0.0 and flat.MaxDrawdown == 0.0

def test_ratios_over_exactly_one_year():
    metrics = _curve_([100.0, 80.0, 160.0]).metrics(date(2021, 1, 1), date(2022, 1, 1))
    assert abs(metrics[SHARPERATIOANN] - 2.0 / 3.0) < 1e-9
    assert abs(metrics[SHARPERATIO] - 2.0 / 3.0 / math.sqrt(2.0)) < 1e-9
    assert abs(metrics[SORTINORATIOANN] - 4.0) < 1e-9
    assert abs(metrics[SORTINORATIO] - 4.0 / math.sqrt(2.0)) < 1e-9
    assert abs(metrics[CALMARRATIOANN] - 3.0) < 1e-9 and abs(metrics[CALMARRATIO] - 3.0) < 1e-9
    assert abs(metrics[STERLINGRATIOANN] - 9.0) < 1e-9 and abs(metrics[STERLINGRATIO] - 9.0) < 1e-9
    assert abs(metrics[MAXEQUITYDRAWDOWNPERC] - 20.0) < 1e-9
    assert abs(metrics[NETVOLATILITYPERC] - math.sqrt(0.72) * 100.0) < 1e-9
    assert abs(metrics[NETVOLATILITYANNPERC] - math.sqrt(0.72) * math.sqrt(2.0) * 100.0) < 1e-9

def test_non_annualized_calmar_uses_the_whole_period_return():
    metrics = _curve_([100.0, 80.0, 160.0]).metrics(date(2021, 1, 1), date(2023, 1, 1))
    assert abs(metrics[CALMARRATIO] - 0.6 / 0.2) < 1e-9
    years = 730.0 / 365.0
    assert abs(metrics[CALMARRATIOANN] - (1.6 ** (1.0 / years) - 1.0) / 0.2) < 1e-9

def test_mid_session_properties_use_the_elapsed_stamps():
    curve = _curve_([100.0, 80.0, 160.0])
    assert curve.Duration == 365 * 86400.0
    assert abs(curve.SharpeRatioAnnualized - 2.0 / 3.0) < 1e-9
    assert abs(curve.CalmarRatioAnnualized - 3.0) < 1e-9
    assert abs(curve.AnnualizedReturn - 0.6) < 1e-9
    assert abs(curve.Periods - 2.0) < 1e-9

def test_risk_free_is_deducted_per_period_and_per_year():
    rate = 0.05
    curve = _curve_([100.0, 80.0, 160.0], risk_free=rate)
    metrics = curve.metrics(date(2021, 1, 1), date(2022, 1, 1))
    per_period = (1.0 + rate) ** 0.5 - 1.0
    assert abs(metrics[RISKFREERATEPERC] - 5.0) < 1e-12
    assert abs(metrics[SHARPERATIO] - (0.4 - per_period) / math.sqrt(0.72)) < 1e-9
    assert abs(metrics[CALMARRATIOANN] - (0.6 - rate) / 0.2) < 1e-9
    assert abs(metrics[CALMARRATIO] - (0.6 - rate) / 0.2) < 1e-9

def test_a_restamped_value_replaces_the_last_point():
    curve = CurveAPI()
    curve.record(START, 100.0)
    curve.record(START + timedelta(hours=1), 110.0)
    assert abs(curve.Mean - 0.1) < 1e-12
    curve.record(START + timedelta(hours=1), 90.0)
    assert curve.Count == 1 and curve.Values == [100.0, 90.0]
    assert abs(curve.Mean + 0.1) < 1e-12 and abs(curve.Return + 0.1) < 1e-12

def test_current_drawdown_and_runup_follow_the_last_value():
    curve = _curve_([100.0, 120.0, 90.0])
    assert abs(curve.Drawdown - 30.0 / 120.0) < 1e-12
    assert abs(curve.Runup) < 1e-12
    assert curve.Peak == 120.0 and curve.Trough == 90.0

def test_catching_up_is_bit_identical_however_it_is_read():
    rows = _walk_()
    reference = _state_(_replay_(rows, 10 ** 9, 0))
    assert _state_(_replay_(rows, 0, 0)) == reference
    assert _state_(_replay_(rows, 64, 37)) == reference
    assert _state_(_replay_(rows, 64, 1)) == reference

def test_drawdowns_match_a_sequential_running_peak():
    rows = _walk_(2000, 11)
    curve = _replay_(rows, 64, 0)
    peak, maximum, total, count = None, 0.0, 0.0, 0
    for _, close, high, low in rows:
        for point in (high, low, close):
            peak = point if peak is None or point > peak else peak
            drawdown = (peak - point) / peak
            maximum = drawdown if drawdown > maximum else maximum
            total += drawdown
            count += 1
    assert curve.MaxDrawdown == maximum and curve.MeanDrawdown == total / count

def test_bar_statistics_match_a_direct_computation():
    rows = _walk_(3000, 3)
    curve = _replay_(rows, 64, 0)
    closes = [close for _, close, _, _ in rows]
    returns = [closes[index] / closes[index - 1] - 1.0 for index in range(1, len(closes))]
    mean = sum(returns) / len(returns)
    deviation = math.sqrt(sum((value - mean) ** 2 for value in returns) / (len(returns) - 1))
    downside = math.sqrt(sum(value * value for value in returns if value < 0.0) / len(returns))
    assert abs(curve.Mean - mean) < 1e-15
    assert abs(curve.Volatility - deviation) < 1e-12
    assert abs(curve.DownsideVolatility - downside) < 1e-12
    assert abs(curve.SharpeRatio - mean / deviation) < 1e-9