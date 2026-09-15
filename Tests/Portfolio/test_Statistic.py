import math
from datetime import date, datetime
from types import SimpleNamespace
from Library.Database.Dataframe import pl
from Library.Statistic.Label import (
    CALMARRATIO,
    MAXBALANCEDRAWDOWNPERC,
    MAXHOLDINGTIME,
    NET_TOTAL_AGGREGATED,
    NET_TOTAL_INDIVIDUAL,
    SHARPERATIO,
    SORTINORATIO,
    STATISTICS_METRICS_LABEL,
    STERLINGRATIO,
    TOTALTRADESVALUE
)
from Library.Statistic.Metric import (
    calculate_annualized_volatility,
    calculate_calmar,
    calculate_sortino,
    equity_curve_ratios
)
from Library.Portfolio.Statistic import (
    _aligned_positions_,
    calculate_drawdown,
    calculate_volatility,
    generate_net_report
)
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Trade import TradeAPI

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
def _frames_():
    trades = pl.DataFrame({
        str(TradeAPI.ID.UID): [1, 2],
        str(TradeAPI.ID.Position): [10, 10],
        str(PositionAPI.ID.Direction): ["Buy", "Buy"],
        str(PositionAPI.ID.Volume): [1000.0, 1000.0],
        str(PositionAPI.ID.EntryTimestamp): [datetime(2023, 1, 2, 8), datetime(2023, 1, 2, 8)],
        str(TradeAPI.ID.ExitTimestamp): [datetime(2023, 1, 2, 12), datetime(2023, 1, 2, 20)],
        str(PositionAPI.ID.EntryPrice): [1.1, 1.1],
        str(TradeAPI.ID.ExitPrice): [1.12, 1.09],
        PNL: [50.0, -20.0]
    })
    positions = pl.DataFrame({
        str(PositionAPI.ID.UID): [11],
        str(PositionAPI.ID.Direction): ["Sell"],
        str(PositionAPI.ID.Volume): [1000.0],
        str(PositionAPI.ID.EntryTimestamp): [datetime(2023, 1, 3, 9)],
        str(PositionAPI.ID.EntryPrice): [1.2],
        str(TradeAPI.ID.ExitPrice): [None],
        PNL: [5.0]
    })
    return trades, positions

def test_aligned_positions_supplies_the_columns_the_concat_would_drop():
    trades, positions = _frames_()
    aligned = _aligned_positions_(positions, trades)
    assert str(TradeAPI.ID.Position) in aligned.columns
    assert aligned[str(TradeAPI.ID.Position)].to_list() == [11]
    assert str(TradeAPI.ID.ExitTimestamp) in aligned.columns
    assert aligned[str(TradeAPI.ID.ExitTimestamp)].to_list() == [None]

def test_open_position_does_not_disable_aggregation():
    trades, positions = _frames_()
    report = generate_net_report(positions, trades, SimpleNamespace(Balance=10000.0), date(2023, 1, 1), date(2023, 2, 1))
    def _cell_(label, column): return report.filter(pl.col(STATISTICS_METRICS_LABEL) == label)[column].item()
    assert _cell_(TOTALTRADESVALUE, NET_TOTAL_INDIVIDUAL) == 3.0
    assert _cell_(TOTALTRADESVALUE, NET_TOTAL_AGGREGATED) == 2.0

def test_balance_drawdown_uses_the_opening_balance_not_the_closing_one():
    trades = pl.DataFrame({str(PositionAPI.ID.Direction): ["Buy", "Buy"], PNL: [-3000.0, 0.0]})
    empty = pl.DataFrame()
    report = generate_net_report(empty, trades, SimpleNamespace(Balance=7000.0), date(2023, 1, 1), date(2024, 1, 1), [10000.0, 7000.0])
    percentage = report.filter(pl.col(STATISTICS_METRICS_LABEL) == MAXBALANCEDRAWDOWNPERC)[NET_TOTAL_INDIVIDUAL].item()
    assert abs(percentage - 30.0) < 1e-9

def test_holding_time_measures_entry_to_exit_with_a_position_open():
    trades, positions = _frames_()
    report = generate_net_report(positions, trades, SimpleNamespace(Balance=10000.0), date(2023, 1, 1), date(2023, 2, 1))
    maximum = report.filter(pl.col(STATISTICS_METRICS_LABEL) == MAXHOLDINGTIME)[NET_TOTAL_INDIVIDUAL].item()
    assert maximum < 30.0