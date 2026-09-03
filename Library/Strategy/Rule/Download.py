from typing import ClassVar, Union

from Library.Engine import MachineAPI
from Library.Utility.Parameter import Parameter
from Library.Protocol.Action import Stream
from Library.Strategy.Strategy import StrategyAPI, Transform

class DownloadStrategyAPI(StrategyAPI):

    Defaults: ClassVar[dict] = {
        "Realtime": {
            'FundamentalManagement': None,
            'MoneyManagement': None,
            'PortfolioManagement': None,
            'RiskManagement': None,
            'SentimentalManagement': None,
            'SignalManagement': None,
            'TechnicalManagement': None,
        },
        "Optimization": {
            'FundamentalManagement': None,
            'MoneyManagement': None,
            'PortfolioManagement': None,
            'RiskManagement': None,
            'SentimentalManagement': None,
            'SignalManagement': None,
            'TechnicalManagement': None,
        },
    }

    Transform = Transform(Market=False, Indicators=False, Portfolio=False)
    Subscription = Stream.BarClosed

    def __init__(self,
                 money_management: Parameter,
                 risk_management: Parameter,
                 signal_management: Parameter,
                 technical_management: Parameter,
                 fundamental_management: Parameter,
                 sentimental_management: Parameter,
                 portfolio_management: Parameter) -> None:
        super().__init__(money_management, risk_management, signal_management, technical_management, fundamental_management, sentimental_management, portfolio_management)

    def risk_management(self) -> Union[MachineAPI, None]:
        return None

    def signal_management(self) -> Union[MachineAPI, None]:
        return None