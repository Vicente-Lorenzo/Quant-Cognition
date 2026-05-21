import pytest
from Library.Portfolio.Position import PositionAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Contract import ContractAPI
from Library.Market.Price import PriceAPI

def test_position_security_propagates_contract():
    c1 = ContractAPI(PipSize=0.0001)
    s1 = SecurityAPI()
    s1.Contract = c1
    
    pos = PositionAPI(EntryPrice=1.0500, StopLossPrice=1.0400)
    # Verify initially None
    assert pos.EntryPrice.Contract is None
    assert pos.StopLossPrice.Contract is None

    # Assign security
    pos.Security = s1
    
    assert pos.EntryPrice.Contract is c1
    assert pos.StopLossPrice.Contract is c1

def test_position_entry_price_propagates_reference():
    pos = PositionAPI()
    pos.StopLossPrice = 1.0400
    
    assert pos.StopLossPrice.Reference == 1.0400
    
    pos.EntryPrice = 1.0500
    assert pos.EntryPrice.Price == 1.0500
    assert pos.StopLossPrice.Reference == 1.0500
    
    pos.TakeProfitPrice = 1.0600
    assert pos.TakeProfitPrice.Reference == 1.0500

def test_position_entry_balance_propagates_reference():
    pos = PositionAPI()
    pos.StopLossPnL = -100.0
    
    assert pos.StopLossPnL.Reference is None
    
    pos.EntryBalance = 10000.0
    assert pos.StopLossPnL.Reference == 10000.0
    
    pos.TakeProfitPnL = 200.0
    assert pos.TakeProfitPnL.Reference == 10000.0
