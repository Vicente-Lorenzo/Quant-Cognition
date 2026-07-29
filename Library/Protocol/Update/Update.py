from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING
from dataclasses import dataclass

from Library.Market.Price import Direction
from Library.Database.Dataclass import DataclassAPI
from Library.Utility.Enumeration import EnumerationAPI
from Library.Portfolio.Account import AccountAPI
from Library.Universe.Security import SecurityAPI
from Library.Market.Bar import BarAPI
from Library.Market.Tick import TickAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI
    from Library.Indicator.Technical import TechnicalAPI
    from Library.Indicator.Fundamental import FundamentalAPI
    from Library.Indicator.Sentimental import SentimentalAPI
    from Library.Portfolio.Portfolio import PortfolioAPI

class UpdateID(EnumerationAPI):
    Init = 0
    Account = 1
    Security = 2
    Execution = 3
    Tick = 4
    BarOpened = 5
    BarClosed = 6
    AskAboveTarget = 7
    AskBelowTarget = 8
    BidAboveTarget = 9
    BidBelowTarget = 10
    OpenedBuyStopOrder = 11
    OpenedSellStopOrder = 12
    ModifiedBuyStopOrderVolume = 13
    ModifiedSellStopOrderVolume = 14
    ModifiedBuyStopOrderStopPrice = 15
    ModifiedSellStopOrderStopPrice = 16
    ModifiedBuyStopOrderStopLoss = 17
    ModifiedSellStopOrderStopLoss = 18
    ModifiedBuyStopOrderTakeProfit = 19
    ModifiedSellStopOrderTakeProfit = 20
    ClosedBuyStopOrder = 21
    ClosedSellStopOrder = 22
    FilledBuyStopOrder = 23
    FilledSellStopOrder = 24
    ExpiredBuyStopOrder = 25
    ExpiredSellStopOrder = 26
    OpenedBuyLimitOrder = 27
    OpenedSellLimitOrder = 28
    ModifiedBuyLimitOrderVolume = 29
    ModifiedSellLimitOrderVolume = 30
    ModifiedBuyLimitOrderLimitPrice = 31
    ModifiedSellLimitOrderLimitPrice = 32
    ModifiedBuyLimitOrderStopLoss = 33
    ModifiedSellLimitOrderStopLoss = 34
    ModifiedBuyLimitOrderTakeProfit = 35
    ModifiedSellLimitOrderTakeProfit = 36
    ClosedBuyLimitOrder = 37
    ClosedSellLimitOrder = 38
    FilledBuyLimitOrder = 39
    FilledSellLimitOrder = 40
    ExpiredBuyLimitOrder = 41
    ExpiredSellLimitOrder = 42
    OpenedBuyStopLimitOrder = 43
    OpenedSellStopLimitOrder = 44
    ModifiedBuyStopLimitOrderVolume = 45
    ModifiedSellStopLimitOrderVolume = 46
    ModifiedBuyStopLimitOrderStopPrice = 47
    ModifiedSellStopLimitOrderStopPrice = 48
    ModifiedBuyStopLimitOrderLimitPrice = 49
    ModifiedSellStopLimitOrderLimitPrice = 50
    ModifiedBuyStopLimitOrderStopLoss = 51
    ModifiedSellStopLimitOrderStopLoss = 52
    ModifiedBuyStopLimitOrderTakeProfit = 53
    ModifiedSellStopLimitOrderTakeProfit = 54
    ClosedBuyStopLimitOrder = 55
    ClosedSellStopLimitOrder = 56
    FilledBuyStopLimitOrder = 57
    FilledSellStopLimitOrder = 58
    ExpiredBuyStopLimitOrder = 59
    ExpiredSellStopLimitOrder = 60
    OpenedBuyPosition = 61
    OpenedSellPosition = 62
    IncreasedBuyPositionVolume = 63
    IncreasedSellPositionVolume = 64
    DecreasedBuyPositionVolume = 65
    DecreasedSellPositionVolume = 66
    ModifiedBuyPositionStopLoss = 67
    ModifiedSellPositionStopLoss = 68
    ModifiedBuyPositionTakeProfit = 69
    ModifiedSellPositionTakeProfit = 70
    ClosedBuyPosition = 71
    ClosedSellPosition = 72
    StopLossBuyPosition = 73
    StopLossSellPosition = 74
    TakeProfitBuyPosition = 75
    TakeProfitSellPosition = 76
    MarginCallBuyPosition = 77
    MarginCallSellPosition = 78
    Denied = 79
    Exception = 80
    Shutdown = 81
    Batch = 82
    Complete = 83

@dataclass(slots=True)
class UpdateAPI(DataclassAPI):
    Direction: ClassVar[Direction] = Direction.Neutral
    Account: AccountAPI
    Security: SecurityAPI
    Market: MarketAPI
    Technical: TechnicalAPI
    Fundamental: FundamentalAPI
    Sentimental: SentimentalAPI
    Portfolio: PortfolioAPI

@dataclass(slots=True)
class CompleteUpdateAPI(UpdateAPI):
    pass

@dataclass(slots=True)
class InitUpdateAPI(UpdateAPI):
    ProcessID: int

@dataclass(slots=True)
class AccountUpdateAPI(UpdateAPI):
    pass

@dataclass(slots=True)
class SecurityUpdateAPI(UpdateAPI):
    pass

@dataclass(slots=True)
class ExecutionUpdateAPI(UpdateAPI):
    pass

@dataclass(slots=True)
class TickUpdateAPI(UpdateAPI):
    Tick: TickAPI

@dataclass(slots=True)
class BarUpdateAPI(UpdateAPI):
    Bar: BarAPI

__all__ = [
    "UpdateID",
    "UpdateAPI",
    "CompleteUpdateAPI",
    "InitUpdateAPI",
    "AccountUpdateAPI",
    "SecurityUpdateAPI",
    "ExecutionUpdateAPI",
    "TickUpdateAPI",
    "BarUpdateAPI"
]