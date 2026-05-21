import pytest
from Library.Market.Tick import TickAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Contract import ContractAPI

def test_tick_security_propagates_contract():
    c1 = ContractAPI(PipSize=0.0001)
    s1 = SecurityAPI()
    s1.Contract = c1
    
    tick = TickAPI(Ask=1.0500, Bid=1.0490, AskBaseConversion=1.0)
    assert tick.Ask.Contract is None
    assert tick.Bid.Contract is None
    assert tick.Mid.Contract is None
    assert tick.AskBaseConversion.Contract is None

    tick.Security = s1
    
    assert tick.Ask.Contract is c1
    assert tick.Bid.Contract is c1
    assert tick.Mid.Contract is c1
    assert tick.AskBaseConversion.Contract is c1
    
    # Check that new assignments inherit the contract
    tick.BidBaseConversion = 1.0
    assert tick.BidBaseConversion.Contract is c1
