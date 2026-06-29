import pytest

from Library.Parameter import ParameterAPI
from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Protocol.Update import AccountUpdateAPI, BarUpdateAPI, SecurityUpdateAPI, UpdateID
from Library.Strategy.Rule.Download import DownloadStrategyAPI
from Library.Strategy.Rule.NNFX import NNFXStrategyAPI
from Library.Strategy.Strategy import StrategyAPI, StrategyType, Transform

def test_strategy_type_enum():
    assert StrategyType.Download.value == 1
    assert StrategyType.NNFX.value == 2
    assert StrategyType.DDPG.value == 3

def test_download_strategy_builds():
    p = ParameterAPI()
    strat = DownloadStrategyAPI(p, p, p)
    assert strat.risk_management() is None
    assert strat.signal_management() is None
    assert strat.strategy_management() is not None

def test_download_strategy_machine_initial_state():
    p = ParameterAPI()
    strat = DownloadStrategyAPI(p, p, p)
    eng = strat.strategy_management()
    assert eng.At.Name == "Initialization"

def test_account_update_sets_portfolio_account():
    p = ParameterAPI()
    strat = DownloadStrategyAPI(p, p, p)
    eng = strat.strategy_management()
    account = AccountAPI(Balance=10000.0)
    portfolio = PortfolioAPI()
    update = AccountUpdateAPI(Account=account, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=portfolio)
    eng.perform(UpdateID.Account, update)
    assert portfolio.Account is account

def test_security_update_sets_portfolio_security_in_initialization():
    p = ParameterAPI()
    strat = DownloadStrategyAPI(p, p, p)
    eng = strat.strategy_management()
    portfolio = PortfolioAPI()
    update = SecurityUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=portfolio)
    eng.perform(UpdateID.Security, update)
    assert portfolio.Security is None

def test_execution_transitions_initialization_to_execution():
    p = ParameterAPI()
    strat = DownloadStrategyAPI(p, p, p)
    strat.Transform = Transform()
    eng = strat.strategy_management()
    portfolio = PortfolioAPI()
    from unittest.mock import MagicMock
    market, technical, fundamental, sentimental = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    from Library.Protocol.Update import ExecutionUpdateAPI
    update = ExecutionUpdateAPI(Account=None, Security=None, Market=market, Technical=technical, Fundamental=fundamental, Sentimental=sentimental, Portfolio=portfolio)
    eng.perform(UpdateID.Execution, update)
    assert eng.At.Name == "Execution"
    technical.init_data.assert_called_once_with(market)
    fundamental.init_data.assert_called_once_with(market)
    sentimental.init_data.assert_called_once_with(market)

def test_shutdown_transitions_to_termination_from_initialization():
    p = ParameterAPI()
    strat = DownloadStrategyAPI(p, p, p)
    eng = strat.strategy_management()
    portfolio = PortfolioAPI()
    from Library.Protocol.Update import CompleteUpdateAPI
    update = CompleteUpdateAPI(Account=None, Security=None, Market=None, Technical=None, Fundamental=None, Sentimental=None, Portfolio=portfolio)
    eng.perform(UpdateID.Shutdown, update)
    assert eng.At.Name == "Termination"
    assert eng.At.End is True

def test_bar_closed_propagates_to_indicators_and_portfolio():
    p = ParameterAPI()
    strat = DownloadStrategyAPI(p, p, p)
    strat.Transform = Transform()
    eng = strat.strategy_management()
    portfolio_mock = type("P", (), {"Account": None, "Security": None, "update_data": lambda self, x: None})()
    from unittest.mock import MagicMock
    market, technical, fundamental, sentimental = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    from Library.Protocol.Update import CompleteUpdateAPI
    eng.perform(UpdateID.Execution, CompleteUpdateAPI(Account=None, Security=None, Market=market, Technical=technical, Fundamental=fundamental, Sentimental=sentimental, Portfolio=portfolio_mock))
    portfolio_mock.update_data = MagicMock()
    bar_update = BarUpdateAPI(Account=None, Security=None, Market=market, Technical=technical, Fundamental=fundamental, Sentimental=sentimental, Portfolio=portfolio_mock, Bar="bar_obj")
    eng.perform(UpdateID.BarClosed, bar_update)
    technical.update_data.assert_called_with(market)
    fundamental.update_data.assert_called_with(market)
    sentimental.update_data.assert_called_with(market)
    portfolio_mock.update_data.assert_called_with("bar_obj")

def test_download_strategy_skips_indicators_and_portfolio():
    p = ParameterAPI()
    strat = DownloadStrategyAPI(p, p, p)
    eng = strat.strategy_management()
    from unittest.mock import MagicMock
    from Library.Protocol.Update import CompleteUpdateAPI
    market, technical, fundamental, sentimental, portfolio = MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
    eng.perform(UpdateID.Execution, CompleteUpdateAPI(Account=None, Security=None, Market=market, Technical=technical, Fundamental=fundamental, Sentimental=sentimental, Portfolio=portfolio))
    eng.perform(UpdateID.BarClosed, BarUpdateAPI(Account=None, Security=None, Market=market, Technical=technical, Fundamental=fundamental, Sentimental=sentimental, Portfolio=portfolio, Bar="bar_obj"))
    technical.update_data.assert_not_called()
    portfolio.update_data.assert_not_called()

def test_strategy_subscription_defaults_and_download():
    from Library.Protocol.Action import Stream
    assert StrategyAPI.Subscription == Stream.All
    assert DownloadStrategyAPI.Subscription == Stream.BarClosed

def test_subscribe_action_serializes_actionid_and_bitmask():
    from Library.Protocol.Action import SubscribeActionAPI, ActionID, Stream
    payload = SubscribeActionAPI(Streams=int(Stream.Tick | Stream.BarClosed)).serialize()
    assert payload[0] == ActionID.Subscribe.value
    assert payload[1] == int(Stream.Tick | Stream.BarClosed)

def test_nnfx_strategy_imports():
    assert NNFXStrategyAPI is not None
    assert issubclass(NNFXStrategyAPI, StrategyAPI)

def test_opened_stop_order_propagates_to_portfolio():
    from unittest.mock import MagicMock
    from Library.Protocol.Update import OpenedBuyStopOrderUpdateAPI, CompleteUpdateAPI
    p = ParameterAPI()
    strat = DownloadStrategyAPI(p, p, p)
    eng = strat.strategy_management()
    portfolio = MagicMock()
    portfolio.update_data = MagicMock()
    portfolio.open_order = MagicMock()
    portfolio.Account = None
    portfolio.Security = None
    market, technical, fundamental, sentimental = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    eng.perform(UpdateID.Execution, CompleteUpdateAPI(Account=None, Security=None, Market=market, Technical=technical, Fundamental=fundamental, Sentimental=sentimental, Portfolio=portfolio))
    account = MagicMock()
    order = MagicMock()
    order.Type = MagicMock()
    order.Type.name = "Stop"
    order.Direction = MagicMock()
    order.Direction.name = "Buy"
    update = OpenedBuyStopOrderUpdateAPI(Account=account, Security=None, Market=market, Technical=technical, Fundamental=fundamental, Sentimental=sentimental, Portfolio=portfolio, Bar=None, Order=order)
    eng.perform(UpdateID.OpenedBuyStopOrder, update)
    pass
    portfolio.open_order.assert_called_once_with(order)

def test_filled_stop_order_transitions_order_to_position():
    from unittest.mock import MagicMock
    from Library.Protocol.Update import FilledBuyStopOrderUpdateAPI, CompleteUpdateAPI
    p = ParameterAPI()
    strat = DownloadStrategyAPI(p, p, p)
    eng = strat.strategy_management()
    portfolio = MagicMock()
    portfolio.update_data = MagicMock()
    portfolio.open_position = MagicMock()
    portfolio.Account = None
    portfolio.Security = None
    market, technical, fundamental, sentimental = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    eng.perform(UpdateID.Execution, CompleteUpdateAPI(Account=None, Security=None, Market=market, Technical=technical, Fundamental=fundamental, Sentimental=sentimental, Portfolio=portfolio))
    order = MagicMock()
    order.UID = 42
    order.Type = MagicMock(); order.Type.name = "Stop"
    order.Direction = MagicMock(); order.Direction.name = "Buy"
    position = MagicMock()
    position.UID = 100
    update = FilledBuyStopOrderUpdateAPI(Account=None, Security=None, Market=market, Technical=technical, Fundamental=fundamental, Sentimental=sentimental, Portfolio=portfolio, Bar=None, Order=order)
    eng.perform(UpdateID.FilledBuyStopOrder, update)
    portfolio.close_order.assert_called_once_with(42)

def test_expired_limit_order_removes_order():
    from unittest.mock import MagicMock
    from Library.Protocol.Update import ExpiredBuyLimitOrderUpdateAPI, CompleteUpdateAPI
    p = ParameterAPI()
    strat = DownloadStrategyAPI(p, p, p)
    eng = strat.strategy_management()
    portfolio = MagicMock()
    portfolio.update_data = MagicMock()
    portfolio.close_order = MagicMock()
    portfolio.Account = None
    portfolio.Security = None
    market, technical, fundamental, sentimental = MagicMock(), MagicMock(), MagicMock(), MagicMock()
    eng.perform(UpdateID.Execution, CompleteUpdateAPI(Account=None, Security=None, Market=market, Technical=technical, Fundamental=fundamental, Sentimental=sentimental, Portfolio=portfolio))
    order = MagicMock()
    order.UID = 77
    order.Type = MagicMock(); order.Type.name = "Limit"
    order.Direction = MagicMock(); order.Direction.name = "Buy"
    update = ExpiredBuyLimitOrderUpdateAPI(Account=None, Security=None, Market=market, Technical=technical, Fundamental=fundamental, Sentimental=sentimental, Portfolio=portfolio, Bar=None, Order=order)
    eng.perform(UpdateID.ExpiredBuyLimitOrder, update)
    portfolio.close_order.assert_called_once_with(77)