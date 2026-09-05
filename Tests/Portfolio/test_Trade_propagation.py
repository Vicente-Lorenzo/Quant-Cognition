from Library.Portfolio.Trade import TradeAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Contract import ContractAPI

def test_trade_security_propagates_contract():
    c1 = ContractAPI(PipSize=0.0001)
    s1 = SecurityAPI()
    s1.Contract = c1

    trade = TradeAPI(EntryPrice=1.0500, ExitPrice=1.0600)
    assert trade.EntryPrice.Contract is None
    assert trade.ExitPrice.Contract is None

    trade.Security = s1

    assert trade.EntryPrice.Contract is c1
    assert trade.ExitPrice.Contract is c1

def test_trade_entry_balance_propagates_reference():
    trade = TradeAPI()
    trade.NetPnL = 100.0

    assert trade.NetPnL.Reference is None

    trade.EntryBalance = 1000.0
    assert trade.NetPnL.Reference == 1000.0
    assert trade.ExitReturn is None

    trade.ExitBalance = 1100.0
    assert trade.ExitReturn.PnL == 100.0
    assert trade.ExitReturn.Reference == 1000.0