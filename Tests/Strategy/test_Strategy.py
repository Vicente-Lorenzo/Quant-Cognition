import pytest
from Library.Strategy.Strategy import StrategyAPI, StrategyType
from Library.Strategy.Rule.NNFX import NNFXStrategyAPI
from Library.Strategy.Rule.Download import DownloadStrategyAPI
from Library.Parameters import ParametersAPI
from Library.Protocol.Update import AccountUpdateAPI, UpdateID
from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Market.Market import MarketAPI

def test_strategy_type():
    assert StrategyType.Download.value == 1
    assert StrategyType.NNFX.value == 2

def test_download_strategy():
    p = ParametersAPI()
    strat = DownloadStrategyAPI(p, p, p)
    assert strat.risk_management() is None
    assert strat.signal_management() is None
    
    eng = strat.strategy_management()
    assert eng is not None

def test_strategy_portfolio_assignments():
    p = ParametersAPI()
    strat = DownloadStrategyAPI(p, p, p)
    eng = strat.strategy_management()
    
    account = AccountAPI(Balance=10000.0)
    portfolio = PortfolioAPI()
    
    update = AccountUpdateAPI(Account=account, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=portfolio)
    
    eng.perform(UpdateID.Account, update)
    assert portfolio.Account is account
