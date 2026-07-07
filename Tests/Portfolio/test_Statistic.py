import math
from Library.Database.Dataframe import pl
from Library.Portfolio.Statistic import (
    calculate_annualized_volatility,
    calculate_calmar,
    calculate_volatility,
    calculate_drawdown,
    calculate_sortino
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
