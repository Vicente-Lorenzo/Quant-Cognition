import pytest
from Library.Market.Price import PriceAPI, Direction
from Library.Universe.Contract import ContractAPI

def test_price_initialization():
    c = ContractAPI(PipSize=0.0001, PointSize=0.00001)
    p = PriceAPI(Price=1.0500, Reference=1.0400, Contract=c)
    assert p.Distance == pytest.approx(0.0100)
    assert p.Pips == pytest.approx(10500.0)
    assert p.Points == pytest.approx(105000.0)
    assert p.Return == pytest.approx(0.0100 / 1.0400)
    assert p.Direction == Direction.Buy

def test_price_without_reference():
    c = ContractAPI(PipSize=0.0001)
    p = PriceAPI(Price=1.0500, Contract=c)
    assert p.Distance is None
    assert p.Return is None
    assert p.Pips == pytest.approx(10500.0)

def test_price_inverted():
    p = PriceAPI(Price=2.0)
    assert p.InvertedPrice == 0.5