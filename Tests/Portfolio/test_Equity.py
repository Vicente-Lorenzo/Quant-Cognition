from datetime import datetime
from types import SimpleNamespace

from Library.Portfolio.Portfolio import PortfolioAPI

def _portfolio_(balance=10000.0):
    portfolio = PortfolioAPI(db=None, migrate=False, autosave=False, autoload=False, autooverload=False)
    portfolio.init_data(account=SimpleNamespace(Balance=balance))
    return portfolio

def _position_(pnl, long=True):
    return SimpleNamespace(IsLong=long, IsShort=not long, NetPnL=SimpleNamespace(PnL=pnl))

def test_equity_equals_balance_when_flat():
    portfolio = _portfolio_(10000.0)
    assert portfolio.Equity == 10000.0
    assert portfolio.InitialBalance == 10000.0
    assert portfolio.EquityPeak == 10000.0 and portfolio.EquityTrough == 10000.0
    assert portfolio.EquityDrawdown == 0.0 and portfolio.EquityRunup == 0.0

def test_equity_includes_unrealized():
    portfolio = _portfolio_(10000.0)
    portfolio._positions_[1] = _position_(250.0)
    assert portfolio.Equity == 10250.0

def test_peak_holds_and_trough_tracks_drawdown():
    portfolio = _portfolio_(10000.0)
    portfolio._positions_[1] = _position_(500.0)
    portfolio._track_equity_()
    assert portfolio.EquityPeak == 10500.0
    portfolio._positions_[1] = _position_(-300.0)
    portfolio._track_equity_()
    assert portfolio.EquityPeak == 10500.0
    assert portfolio.EquityTrough == 9700.0
    assert abs(portfolio.EquityDrawdown - (9700.0 / 10500.0 - 1.0)) < 1e-12
    assert portfolio.EquityRunup == 0.0

def test_runup_measures_recovery_from_trough():
    portfolio = _portfolio_(10000.0)
    portfolio._positions_[1] = _position_(-400.0)
    portfolio._track_equity_()
    assert portfolio.EquityTrough == 9600.0
    portfolio._positions_[1] = _position_(200.0)
    portfolio._track_equity_()
    assert abs(portfolio.EquityRunup - (10200.0 / 9600.0 - 1.0)) < 1e-12
    assert abs(portfolio.EquityDrawdown - (10200.0 / 10200.0 - 1.0)) < 1e-12

def test_equity_curve_appends_one_point_per_bar_timestamp():
    portfolio = _portfolio_(10000.0)
    portfolio._equity_stamp_ = datetime(2021, 1, 1)
    portfolio._record_equity_()
    portfolio._equity_stamp_ = datetime(2021, 1, 2)
    portfolio._positions_[1] = _position_(50.0)
    portfolio._record_equity_()
    assert portfolio.EquityCurve == [10000.0, 10050.0]

def test_equity_curve_restamps_realized_pnl_on_close():
    portfolio = _portfolio_(10000.0)
    portfolio._equity_stamp_ = datetime(2021, 1, 1)
    portfolio._positions_[1] = _position_(100.0)
    portfolio._record_equity_()
    assert portfolio.EquityCurve == [10100.0]
    del portfolio._positions_[1]
    portfolio._account_.Balance += 60.0
    portfolio._record_equity_()
    assert portfolio.EquityCurve == [10060.0]

def test_excursion_accumulates_drawdown_and_runup():
    portfolio = _portfolio_(10000.0)
    for equity in (10000.0, 10200.0, 9900.0, 10100.0):
        portfolio._accumulate_excursion_(equity)
    assert abs(portfolio.MaxDrawdown - 300.0 / 10200.0) < 1e-12
    assert abs(portfolio.MeanDrawdown - (300.0 / 10200.0 + 100.0 / 10200.0) / 4.0) < 1e-12
    assert abs(portfolio.MaxRunup - 200.0 / 9900.0) < 1e-12
    assert abs(portfolio.MeanRunup - (200.0 / 10000.0 + 200.0 / 9900.0) / 4.0) < 1e-12