from typing import ClassVar, Union

from Library.Engine import MachineAPI
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

    def risk_management(self) -> Union[MachineAPI, None]:
        return None

    def signal_management(self) -> Union[MachineAPI, None]:
        return None