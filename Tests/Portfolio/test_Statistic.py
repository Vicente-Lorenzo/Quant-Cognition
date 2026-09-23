import math
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from Library.Database.Dataframe import pl
from Library.Statistic.Curve import CurveAPI
from Library.Statistic.Label import (
    CALMARRATIOANN,
    EXPECTEDLOSINGRETURNPERC,
    EXPECTEDNETRETURNPERC,
    EXPECTEDWINNINGRETURNPERC,
    LOSINGRETURNANNPERC,
    LOSINGRETURNPERC,
    MAXBALANCEDRAWDOWNPERC,
    MAXEQUITYDRAWDOWNPERC,
    MAXHOLDINGTIME,
    NET_BUY_AGGREGATED,
    NET_BUY_INDIVIDUAL,
    NET_SELL_AGGREGATED,
    NET_SELL_INDIVIDUAL,
    NET_TOTAL_AGGREGATED,
    NET_TOTAL_INDIVIDUAL,
    NETRETURNANNPERC,
    NETRETURNPERC,
    NETVOLATILITYPERC,
    RISKFREERATEPERC,
    SHARPERATIO,
    SHARPERATIOANN,
    SORTINORATIOANN,
    STATISTICS_METRICS_LABEL,
    STERLINGRATIOANN,
    TOTALTRADESVALUE,
    WINNINGRETURNANNPERC,
    WINNINGRETURNPERC
)
from Library.Statistic.Metric import calculate_annualized_return, calculate_annualized_volatility
from Library.Portfolio.Statistic import (
    Metrics,
    _aligned_positions_,
    calculate_drawdown,
    calculate_return,
    calculate_volatility,
    generate_net_report
)
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Trade import TradeAPI

LOG = str(PositionAPI.ID.LogReturn)
PNL = str(PositionAPI.ID.NetPnL)

def _curve_(values, risk_free=0.0):
    curve = CurveAPI(risk_free=risk_free)
    for index, value in enumerate(values):
        curve.record(datetime(2021, 1, 1) + timedelta(days=365) / max(len(values) - 1, 1) * index, value)
        curve.observe(value)
    return curve

def _curves_(total, buy=None, sell=None, risk_free=0.0):
    return (_curve_(buy or total, risk_free), _curve_(sell or total, risk_free), _curve_(total, risk_free))

def test_trade_volatility_is_the_lognormal_dispersion_of_trade_returns():
    df = pl.DataFrame({LOG: [0.02, -0.01, 0.03, -0.01]})
    deviation = pl.Series([0.02, -0.01, 0.03, -0.01]).std()
    assert abs(calculate_volatility(df) - math.sqrt(math.exp(deviation ** 2) - 1.0) * 100.0) < 1e-9

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

def test_volatility_survives_all_null_log_returns():
    assert calculate_volatility(pl.DataFrame({LOG: [None, None]})) == 0.0

def test_every_column_reads_its_own_curve():
    empty = pl.DataFrame()
    curves = _curves_([100.0, 80.0, 160.0], buy=[100.0, 90.0, 120.0], sell=[100.0, 90.0, 140.0])
    report = generate_net_report(empty, empty, SimpleNamespace(Balance=100.0), date(2021, 1, 1), date(2022, 1, 1), curves)
    def _cell_(label, column): return report.filter(pl.col(STATISTICS_METRICS_LABEL) == label)[column].item()
    for column in (NET_TOTAL_INDIVIDUAL, NET_TOTAL_AGGREGATED):
        assert abs(_cell_(CALMARRATIOANN, column) - 3.0) < 1e-9
        assert abs(_cell_(SORTINORATIOANN, column) - 4.0) < 1e-9
        assert abs(_cell_(SHARPERATIOANN, column) - 2.0 / 3.0) < 1e-9
        assert abs(_cell_(STERLINGRATIOANN, column) - 9.0) < 1e-9
    for column in (NET_BUY_INDIVIDUAL, NET_BUY_AGGREGATED):
        assert abs(_cell_(MAXEQUITYDRAWDOWNPERC, column) - 10.0) < 1e-9
        assert abs(_cell_(CALMARRATIOANN, column) - 2.0) < 1e-9
    for column in (NET_SELL_INDIVIDUAL, NET_SELL_AGGREGATED):
        assert abs(_cell_(CALMARRATIOANN, column) - 4.0) < 1e-9

def test_the_report_keeps_every_row_and_adds_the_risk_free_rate():
    empty = pl.DataFrame()
    report = generate_net_report(empty, empty, SimpleNamespace(Balance=100.0), date(2021, 1, 1), date(2022, 1, 1), _curves_([100.0, 110.0], risk_free=0.03))
    assert report[STATISTICS_METRICS_LABEL].to_list() == Metrics and len(Metrics) == 90
    assert report.filter(pl.col(STATISTICS_METRICS_LABEL) == RISKFREERATEPERC).row(0)[1:] == (3.0,) * 6

def test_a_report_without_curves_leaves_the_curve_rows_at_zero():
    trades, positions = _frames_()
    report = generate_net_report(positions, trades, SimpleNamespace(Balance=10000.0), date(2023, 1, 1), date(2023, 2, 1))
    for label in (SHARPERATIO, SHARPERATIOANN, NETVOLATILITYPERC, MAXEQUITYDRAWDOWNPERC):
        assert report.filter(pl.col(STATISTICS_METRICS_LABEL) == label).row(0)[1:] == (0.0,) * 6

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
    report = generate_net_report(empty, trades, SimpleNamespace(Balance=7000.0), date(2023, 1, 1), date(2024, 1, 1), _curves_([10000.0, 7000.0]))
    percentage = report.filter(pl.col(STATISTICS_METRICS_LABEL) == MAXBALANCEDRAWDOWNPERC)[NET_TOTAL_INDIVIDUAL].item()
    assert abs(percentage - 30.0) < 1e-9

def test_holding_time_measures_entry_to_exit_with_a_position_open():
    trades, positions = _frames_()
    report = generate_net_report(positions, trades, SimpleNamespace(Balance=10000.0), date(2023, 1, 1), date(2023, 2, 1))
    maximum = report.filter(pl.col(STATISTICS_METRICS_LABEL) == MAXHOLDINGTIME)[NET_TOTAL_INDIVIDUAL].item()
    assert maximum < 30.0

def _returns_(start: date, stop: date):
    trades, positions = _frames_()
    report = generate_net_report(positions, trades, SimpleNamespace(Balance=10030.0), start, stop, _curves_([10000.0, 10035.0]))
    def _cell_(label, column): return report.filter(pl.col(STATISTICS_METRICS_LABEL) == label)[column].item()
    return _cell_

def test_net_return_is_the_account_return_on_the_opening_balance():
    cell = _returns_(date(2023, 1, 1), date(2023, 2, 1))
    for buy, sell, total in ((NET_BUY_INDIVIDUAL, NET_SELL_INDIVIDUAL, NET_TOTAL_INDIVIDUAL), (NET_BUY_AGGREGATED, NET_SELL_AGGREGATED, NET_TOTAL_AGGREGATED)):
        assert abs(cell(NETRETURNPERC, buy) - 0.30) < 1e-9
        assert abs(cell(NETRETURNPERC, sell) - 0.05) < 1e-9
        assert abs(cell(NETRETURNPERC, total) - 0.35) < 1e-9
        assert abs(cell(NETRETURNPERC, buy) + cell(NETRETURNPERC, sell) - cell(NETRETURNPERC, total)) < 1e-9

def test_winning_and_losing_returns_sum_to_the_net_return():
    cell = _returns_(date(2023, 1, 1), date(2023, 2, 1))
    for column in (NET_BUY_INDIVIDUAL, NET_SELL_INDIVIDUAL, NET_TOTAL_INDIVIDUAL, NET_BUY_AGGREGATED, NET_SELL_AGGREGATED, NET_TOTAL_AGGREGATED):
        assert abs(cell(WINNINGRETURNPERC, column) + cell(LOSINGRETURNPERC, column) - cell(NETRETURNPERC, column)) < 1e-9
    assert abs(cell(WINNINGRETURNPERC, NET_TOTAL_INDIVIDUAL) - 0.55) < 1e-9
    assert abs(cell(LOSINGRETURNPERC, NET_TOTAL_INDIVIDUAL) + 0.20) < 1e-9

def test_expected_returns_are_the_mean_trade_on_the_opening_balance():
    cell = _returns_(date(2023, 1, 1), date(2023, 2, 1))
    assert abs(cell(EXPECTEDNETRETURNPERC, NET_TOTAL_INDIVIDUAL) - 0.35 / 3) < 1e-9
    assert abs(cell(EXPECTEDNETRETURNPERC, NET_TOTAL_AGGREGATED) - 0.35 / 2) < 1e-9
    assert abs(cell(EXPECTEDWINNINGRETURNPERC, NET_TOTAL_INDIVIDUAL) - 0.55 / 2) < 1e-9
    assert abs(cell(EXPECTEDLOSINGRETURNPERC, NET_TOTAL_INDIVIDUAL) + 0.20) < 1e-9

def test_net_return_annualized_compounds_the_account_return():
    start, stop = date(2023, 1, 1), date(2025, 1, 1)
    cell = _returns_(start, stop)
    years = (stop - start).days / 365.0
    assert abs(cell(NETRETURNANNPERC, NET_TOTAL_AGGREGATED) - (1.0035 ** (1.0 / years) - 1.0) * 100.0) < 1e-9
    assert abs(cell(NETRETURNANNPERC, NET_TOTAL_INDIVIDUAL) - cell(NETRETURNANNPERC, NET_TOTAL_AGGREGATED)) < 1e-12
    assert abs(cell(WINNINGRETURNANNPERC, NET_TOTAL_INDIVIDUAL) - 0.55 / years) < 1e-9
    assert abs(cell(LOSINGRETURNANNPERC, NET_TOTAL_INDIVIDUAL) + 0.20 / years) < 1e-9

def test_return_needs_an_opening_balance():
    df = pl.DataFrame({PNL: [50.0, -20.0]})
    assert calculate_return(0.0, df) == (0.0, 0.0)
    assert calculate_return(None, df) == (0.0, 0.0)
    assert calculate_return(1000.0, df) == (1.5, 3.0)

def test_annualized_return_floors_a_loss_beyond_the_balance():
    two_years = 2 * 365 * 86400.0
    assert calculate_annualized_return(-150.0, two_years, pct=True) == -100.0
    assert calculate_annualized_return(-100.0, two_years, pct=True) == -100.0
    assert abs(calculate_annualized_return(21.0, two_years, pct=True) - 10.0) < 1e-9

def test_annualized_return_saturates_instead_of_overflowing():
    assert calculate_annualized_return(0.10, 3600.0) == math.inf

def test_the_balance_path_follows_realization_not_entry_order():
    entry = datetime(2023, 1, 2, 8)
    trades = pl.DataFrame({
        str(TradeAPI.ID.UID): [1, 2],
        str(TradeAPI.ID.Position): [10, 11],
        str(PositionAPI.ID.Direction): ["Buy", "Buy"],
        str(PositionAPI.ID.Volume): [1000.0, 1000.0],
        str(PositionAPI.ID.EntryTimestamp): [entry, entry],
        str(TradeAPI.ID.ExitTimestamp): [entry + timedelta(hours=9), entry + timedelta(hours=1)],
        str(PositionAPI.ID.EntryPrice): [1.1, 1.1],
        str(TradeAPI.ID.ExitPrice): [1.07, 1.15],
        PNL: [-3000.0, 5000.0]
    })
    report = generate_net_report(pl.DataFrame(), trades, SimpleNamespace(Balance=12000.0), date(2023, 1, 1), date(2024, 1, 1), _curves_([10000.0, 12000.0]))
    for column in (NET_TOTAL_INDIVIDUAL, NET_TOTAL_AGGREGATED):
        assert abs(report.filter(pl.col(STATISTICS_METRICS_LABEL) == MAXBALANCEDRAWDOWNPERC)[column].item() - 20.0) < 1e-9

def test_a_deal_still_open_after_a_partial_close_stays_open_when_aggregated():
    from Library.Portfolio.Statistic import aggregate_items, calculate_holding_times, realize_items
    entry = datetime(2023, 1, 2, 8)
    frame = pl.DataFrame({
        str(TradeAPI.ID.UID): [1, 2, 10], str(TradeAPI.ID.Position): [10, 11, 10], str(PositionAPI.ID.Direction): ["Buy", "Buy", "Buy"],
        str(PositionAPI.ID.Volume): [1000.0, 1000.0, 1000.0], str(PositionAPI.ID.EntryTimestamp): [entry, entry + timedelta(hours=2), entry],
        str(TradeAPI.ID.ExitTimestamp): [entry + timedelta(hours=1), entry + timedelta(hours=5), None],
        str(PositionAPI.ID.EntryPrice): [1.1, 1.1, 1.1], str(TradeAPI.ID.ExitPrice): [1.11, 1.12, None], PNL: [10.0, 20.0, -50.0]
    })
    deals = realize_items(aggregate_items(frame))
    assert deals[str(TradeAPI.ID.Position)].to_list() == [11, 10]
    assert deals[str(TradeAPI.ID.ExitTimestamp)].to_list() == [entry + timedelta(hours=5), None]
    maximum, _, _ = calculate_holding_times(deals, date(2023, 2, 1))
    assert abs(maximum - (datetime(2023, 2, 1) - entry).total_seconds() / 86400.0) < 1e-9