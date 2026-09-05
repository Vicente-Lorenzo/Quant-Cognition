from Library.Portfolio.PnL import PnLAPI
from Library.Market.Price import Direction

def test_pnl_initialization():
    pnl = PnLAPI(PnL=150.0, Reference=1000.0)
    assert pnl.PnL == 150.0
    assert pnl.Reference == 1000.0
    assert pnl.Return == 0.15
    assert pnl.Percentage == 15.0

def test_pnl_direction():
    assert PnLAPI(PnL=10.0).Direction == Direction.Buy
    assert PnLAPI(PnL=-10.0).Direction == Direction.Sell
    assert PnLAPI(PnL=0.0).Direction == Direction.Neutral