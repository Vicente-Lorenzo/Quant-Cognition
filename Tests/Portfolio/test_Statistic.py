import pytest
from datetime import datetime, timedelta
from Library.Database.Dataframe import pl
from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Statistic import generate_realized_report, generate_unrealized_report, generate_net_report

def test_statistic_report_empty():
    account = AccountAPI(Balance=10000.0)
    start = datetime(2023, 1, 1)
    stop = datetime(2023, 1, 31)
    
    trades_df = pl.DataFrame()
    positions_df = pl.DataFrame()
    
    report_r = generate_realized_report(trades_df, account, start, stop)
    assert report_r.shape == (73, 7)
    assert "Realized Buy Metrics (Individual)" in report_r.columns

    report_u = generate_unrealized_report(positions_df, account, start, stop)
    assert report_u.shape == (73, 7)
    assert "Unrealized Buy Metrics (Individual)" in report_u.columns

    report_n = generate_net_report(positions_df, trades_df, account, start, stop)
    assert report_n.shape == (73, 7)
    assert "Net Buy Metrics (Individual)" in report_n.columns

def test_statistic_report_populated():
    account = AccountAPI(Balance=10000.0)
    start = datetime(2023, 1, 1)
    stop = datetime(2023, 1, 31)
    
    # 2 Trades: 1 winner, 1 loser
    trades_data = {
        "NetPnL": [500.0, -200.0],
        "GrossPnL": [510.0, -190.0],
        "NetReturn": [5.0, -2.0],
        "MaxDrawdownPnL": [-50.0, -250.0],
        "MaxRunupPnL": [550.0, 20.0],
        "EntryTimestamp": [datetime(2023, 1, 2), datetime(2023, 1, 10)],
        "ExitTimestamp": [datetime(2023, 1, 5), datetime(2023, 1, 12)]
    }
    trades_df = pl.DataFrame(trades_data)
    
    # 1 Open Position: Winner
    positions_data = {
        "NetPnL": [300.0],
        "GrossPnL": [300.0],
        "NetReturn": [3.0],
        "MaxDrawdownPnL": [-10.0],
        "MaxRunupPnL": [350.0],
        "EntryTimestamp": [datetime(2023, 1, 20)]
    }
    positions_df = pl.DataFrame(positions_data)
    
    report_r = generate_realized_report(trades_df, account, start, stop)
    assert not report_r.is_empty()
    
    report_u = generate_unrealized_report(positions_df, account, start, stop)
    assert not report_u.is_empty()
    
    report_n = generate_net_report(positions_df, trades_df, account, start, stop)
    assert not report_n.is_empty()
    
    assert "Realized Total Metrics (Individual)" in report_r.columns
    assert "Unrealized Total Metrics (Individual)" in report_u.columns
    assert "Net Total Metrics (Individual)" in report_n.columns
    
    # Realized Net PnL = 500 - 200 = 300
    realized_net_pnl = report_r.filter(pl.col("Statistical Metrics") == "Net Profit/Loss")["Realized Total Metrics (Individual)"][0]
    assert realized_net_pnl == 300.0
    
    # Unrealized Net PnL = 300
    unrealized_net_pnl = report_u.filter(pl.col("Statistical Metrics") == "Net Profit/Loss")["Unrealized Total Metrics (Individual)"][0]
    assert unrealized_net_pnl == 300.0
    
    # Net Performance PnL = 300 + 300 = 600
    net_pnl = report_n.filter(pl.col("Statistical Metrics") == "Net Profit/Loss")["Net Total Metrics (Individual)"][0]
    assert net_pnl == 600.0

    # Test Win Rate
    realized_win_rate = report_r.filter(pl.col("Statistical Metrics") == "Winning Rate (%)")["Realized Total Metrics (Individual)"][0]
    assert realized_win_rate == 50.0  # 1 win out of 2

    # Test Payoff Ratio
    # Avg win = 500. Avg loss = -200. Risk-to-Reward = abs(-200) / 500 = 0.4
    realized_payoff = report_r.filter(pl.col("Statistical Metrics") == "Risk-to-Reward Ratio")["Realized Total Metrics (Individual)"][0]
    assert realized_payoff == 0.4