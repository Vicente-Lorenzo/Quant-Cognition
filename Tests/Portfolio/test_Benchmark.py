import math
from datetime import date, datetime, timedelta

from Library.Statistic.Label import (
    BENCHMARK_ALPHA,
    BENCHMARK_ALPHASIGNIFICANCE,
    BENCHMARK_ANNUALIZEDRETURN,
    BENCHMARK_BETA,
    BENCHMARK_CORRELATION,
    BENCHMARK_DOWNSIDECAPTURE,
    BENCHMARK_EXCESSRETURN,
    BENCHMARK_INFORMATIONRATIO,
    BENCHMARK_LABEL,
    BENCHMARK_MAXDRAWDOWN,
    BENCHMARK_TOTALRETURN,
    BENCHMARK_TRACKINGERROR,
    BENCHMARK_UPSIDECAPTURE,
    BENCHMARK_VOLATILITY,
    CALMARRATIO,
    SHARPERATIO,
    SORTINORATIO,
    STERLINGRATIO
)
from Library.Statistic.Metric import (
    align_series,
    series_returns
)
from Library.Portfolio.Statistic import (
    generate_benchmark_report
)

def _series_(values, step=1):
    return [(datetime(2020, 1, 1) + timedelta(days=index * step), value) for index, value in enumerate(values)]

def test_align_series_forward_fills_on_spine():
    spine = [datetime(2020, 1, day) for day in (1, 2, 3, 4)]
    series = [(datetime(2020, 1, 1), 10.0), (datetime(2020, 1, 3), 30.0)]
    assert align_series(spine, series) == [10.0, 10.0, 30.0, 30.0]

def test_align_series_leaves_none_before_first_point():
    spine = [datetime(2020, 1, day) for day in (1, 2, 3)]
    series = [(datetime(2020, 1, 3), 30.0)]
    assert align_series(spine, series) == [None, None, 30.0]

def test_series_returns_skips_missing_points():
    returns = series_returns([100.0, 110.0, None])
    assert abs(returns[0] - 0.1) < 1e-9 and returns[1] is None

def test_report_is_empty_without_equity():
    assert generate_benchmark_report(None, {}, date(2020, 1, 1), date(2021, 1, 1)).is_empty()
    assert generate_benchmark_report([(datetime(2020, 1, 1), 100.0)], {}, date(2020, 1, 1), date(2021, 1, 1)).is_empty()

def test_strategy_row_has_no_relative_metrics():
    report = generate_benchmark_report(_series_([100.0, 110.0, 120.0]), {}, date(2020, 1, 1), date(2020, 1, 4))
    assert report.height == 1
    row = report.rows(named=True)[0]
    assert row[BENCHMARK_LABEL] == "Strategy"
    assert abs(row[BENCHMARK_TOTALRETURN] - 20.0) < 1e-9
    assert all(row[column] is None for column in (BENCHMARK_CORRELATION, BENCHMARK_BETA, BENCHMARK_ALPHA, BENCHMARK_EXCESSRETURN))

def test_identical_series_have_unit_beta_and_zero_alpha():
    equity = _series_([100.0, 104.0, 101.0, 107.0, 103.0, 111.0])
    report = generate_benchmark_report(equity, {"Mirror": _series_([50.0, 52.0, 50.5, 53.5, 51.5, 55.5])}, date(2020, 1, 1), date(2020, 1, 7))
    row = report.rows(named=True)[1]
    assert abs(row[BENCHMARK_CORRELATION] - 1.0) < 1e-9
    assert abs(row[BENCHMARK_BETA] - 1.0) < 1e-9
    assert abs(row[BENCHMARK_ALPHA]) < 1e-9
    assert abs(row[BENCHMARK_TRACKINGERROR]) < 1e-9
    assert abs(row[BENCHMARK_EXCESSRETURN]) < 1e-9

def test_excess_return_is_strategy_minus_benchmark():
    report = generate_benchmark_report(_series_([100.0, 105.0, 120.0]), {"Flat": _series_([10.0, 10.5, 11.0])}, date(2020, 1, 1), date(2020, 1, 4))
    row = report.rows(named=True)[1]
    assert abs(row[BENCHMARK_TOTALRETURN] - 10.0) < 1e-9
    assert abs(row[BENCHMARK_EXCESSRETURN] - 10.0) < 1e-9

def test_max_drawdown_is_positive_percentage():
    report = generate_benchmark_report(_series_([100.0, 120.0, 60.0, 90.0]), {}, date(2020, 1, 1), date(2020, 1, 5))
    assert abs(report.rows(named=True)[0][BENCHMARK_MAXDRAWDOWN] - 50.0) < 1e-9

def test_flat_benchmark_yields_zero_ratios_not_infinities():
    report = generate_benchmark_report(_series_([100.0, 101.0, 102.0]), {"Flat": _series_([10.0, 10.0, 10.0])}, date(2020, 1, 1), date(2020, 1, 4))
    row = report.rows(named=True)[1]
    assert row[BENCHMARK_BETA] == 0.0 and row[BENCHMARK_CORRELATION] == 0.0
    assert all(value is None or math.isfinite(value) for value in row.values() if isinstance(value, float))

def test_capture_ratios_reflect_participation():
    equity = _series_([100.0, 110.0, 99.0, 108.9])
    report = generate_benchmark_report(equity, {"Market": _series_([100.0, 105.0, 99.75, 104.7375])}, date(2020, 1, 1), date(2020, 1, 5))
    row = report.rows(named=True)[1]
    assert row[BENCHMARK_UPSIDECAPTURE] > 100.0
    assert row[BENCHMARK_DOWNSIDECAPTURE] > 100.0
    assert math.isfinite(row[BENCHMARK_INFORMATIONRATIO])

def test_column_order_groups_returns_ratios_then_relative():
    report = generate_benchmark_report(_series_([100.0, 110.0, 105.0, 120.0]), {"Market": _series_([100.0, 104.0, 102.0, 109.0])}, date(2020, 1, 1), date(2020, 1, 5))
    assert report.columns == [
        BENCHMARK_LABEL, BENCHMARK_TOTALRETURN, BENCHMARK_ANNUALIZEDRETURN, BENCHMARK_VOLATILITY, BENCHMARK_MAXDRAWDOWN,
        SHARPERATIO, SORTINORATIO, CALMARRATIO, STERLINGRATIO,
        BENCHMARK_CORRELATION, BENCHMARK_ALPHA, BENCHMARK_ALPHASIGNIFICANCE, BENCHMARK_BETA,
        BENCHMARK_TRACKINGERROR, BENCHMARK_INFORMATIONRATIO,
        BENCHMARK_EXCESSRETURN, BENCHMARK_UPSIDECAPTURE, BENCHMARK_DOWNSIDECAPTURE]

def test_all_four_ratios_are_populated():
    report = generate_benchmark_report(_series_([100.0, 110.0, 105.0, 120.0, 112.0, 130.0]), {}, date(2020, 1, 1), date(2020, 1, 7))
    row = report.rows(named=True)[0]
    assert all(isinstance(row[column], float) and math.isfinite(row[column]) for column in (SHARPERATIO, SORTINORATIO, CALMARRATIO, STERLINGRATIO))
    assert row[SORTINORATIO] > row[SHARPERATIO]
    assert row[STERLINGRATIO] > row[CALMARRATIO]

def test_benchmark_without_overlap_is_reported_as_nulls():
    report = generate_benchmark_report(_series_([100.0, 101.0, 102.0]), {"Late": [(datetime(2021, 6, 1), 5.0)]}, date(2020, 1, 1), date(2020, 1, 4))
    row = report.rows(named=True)[1]
    assert row[BENCHMARK_LABEL] == "Late" and row[BENCHMARK_TOTALRETURN] is None
