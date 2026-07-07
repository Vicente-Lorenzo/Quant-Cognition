import math
from datetime import date
from types import SimpleNamespace
from Library.Database.Dataframe import pl
from Library.Portfolio.Statistic import (
    CALMARRATIO,
    NET_TOTAL_AGGREGATED,
    SHARPERATIO,
    SORTINORATIO,
    STATISTICS_METRICS_LABEL,
    STERLINGRATIO,
    calculate_annualized_volatility,
    calculate_calmar,
    calculate_volatility,
    calculate_drawdown,
    calculate_sortino,
    equity_curve_ratios,
    generate_net_report
)
from Library.Portfolio.Position import PositionAPI

LOG = str(PositionAPI.ID.LogReturn)
PNL = str(PositionAPI.ID.NetPnL)

def test_downside_deviation_uses_all_trades_below_zero():
    df = pl.DataFrame({LOG: [0.02, -0.01, 0.03, -0.01]})
    expected_log = math.sqrt((0.0 + 0.01 ** 2 + 0.0 + 0.01 ** 2) / 4)
    expected = math.sqrt(math.exp(expected_log ** 2) - 1.0) * 100.0
    assert abs(calculate_volatility(df, downside=True) - expected) < 1e-9

def test_downside_deviation_no_explosion_on_identical_losses():
    df = pl.DataFrame({LOG: [-0.01, -0.01]})
    assert calculate_volatility(df, downside=True) > 0.9

def test_annualized_volatility_scales_with_trade_frequency():
    year_seconds = 365 * 86400.0
    yearly = calculate_annualized_volatility(1.0, 100, year_seconds, pct=True)
    assert abs(yearly - 10.0) < 1e-6
    sparse = calculate_annualized_volatility(1.0, 4, year_seconds, pct=True)
    assert abs(sparse - 2.0) < 1e-6

def test_max_drawdown_pct_uses_concurrent_peak():
    df = pl.DataFrame({PNL: [-2000.0, 12000.0]})
    _, max_dd_pct, _, _ = calculate_drawdown(10000.0, df)
    assert abs(max_dd_pct - 20.0) < 1e-9

def test_sortino_and_calmar_floor_but_finite():
    assert calculate_sortino(5.0, 2.5) == 2.0
    assert calculate_sortino(5.0, 0.0) == 500.0
    assert calculate_calmar(10.0, 20.0) == 0.5

def test_volatility_survives_all_null_log_returns():
    df = pl.DataFrame({LOG: [None, None]})
    assert calculate_volatility(df) == 0.0
    assert calculate_volatility(df, upside=True) == 0.0
    assert calculate_volatility(df, downside=True) == 0.0

def test_upside_deviation_mirrors_downside():
    df = pl.DataFrame({LOG: [0.02, -0.01, 0.03, -0.01]})
    up = calculate_volatility(df, upside=True)
    down = calculate_volatility(df, downside=True)
    expected_up_log = math.sqrt((0.02 ** 2 + 0.03 ** 2) / 4)
    assert abs(up - math.sqrt(math.exp(expected_up_log ** 2) - 1.0) * 100.0) < 1e-9
    assert up > down

def test_equity_curve_ratios_none_on_empty_or_flat():
    assert equity_curve_ratios(None, date(2021, 1, 1), date(2022, 1, 1)) is None
    assert equity_curve_ratios([100.0], date(2021, 1, 1), date(2022, 1, 1)) is None
    flat = equity_curve_ratios([100.0, 100.0, 100.0], date(2021, 1, 1), date(2022, 1, 1))
    assert flat[SHARPERATIO] == 0.0 and flat[SORTINORATIO] == 0.0 and flat[CALMARRATIO] == 0.0

def test_equity_curve_ratios_exact_one_year():
    ratios = equity_curve_ratios([100.0, 80.0, 160.0], date(2021, 1, 1), date(2022, 1, 1))
    assert abs(ratios[CALMARRATIO] - 3.0) < 1e-9
    assert abs(ratios[SORTINORATIO] - 4.0) < 1e-9
    assert abs(ratios[SHARPERATIO] - 2.0 / 3.0) < 1e-9
    assert abs(ratios[STERLINGRATIO] - 9.0) < 1e-9

def test_equity_curve_ratios_uses_supplied_drawdowns():
    ratios = equity_curve_ratios([100.0, 160.0], date(2021, 1, 1), date(2022, 1, 1), max_drawdown=0.30, mean_drawdown=0.10)
    assert abs(ratios[CALMARRATIO] - 2.0) < 1e-9
    assert abs(ratios[STERLINGRATIO] - 6.0) < 1e-9

def test_net_report_overrides_total_ratios_with_bar_curve():
    account = SimpleNamespace(Balance=100.0)
    empty = pl.DataFrame()
    report = generate_net_report(empty, empty, account, date(2021, 1, 1), date(2022, 1, 1), [100.0, 80.0, 160.0])
    def _cell_(label): return report.filter(pl.col(STATISTICS_METRICS_LABEL) == label)[NET_TOTAL_AGGREGATED].item()
    assert abs(_cell_(CALMARRATIO) - 3.0) < 1e-9
    assert abs(_cell_(SORTINORATIO) - 4.0) < 1e-9
    assert abs(_cell_(SHARPERATIO) - 2.0 / 3.0) < 1e-9
    assert abs(_cell_(STERLINGRATIO) - 9.0) < 1e-9
