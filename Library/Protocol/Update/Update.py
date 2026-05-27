from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

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
    Initialization = 0
    Account = 1
    Security = 2
    Tick = 3
    BarOpened = 4
    BarClosed = 5
    AskAboveTarget = 6
    AskBelowTarget = 7
    BidAboveTarget = 8
    BidBelowTarget = 9
    OpenedBuyStopOrder = 10
    OpenedSellStopOrder = 11
    ModifiedBuyStopOrderVolume = 12
    ModifiedSellStopOrderVolume = 13
    ModifiedBuyStopOrderStopPrice = 14
    ModifiedSellStopOrderStopPrice = 15
    ModifiedBuyStopOrderStopLoss = 16
    ModifiedSellStopOrderStopLoss = 17
    ModifiedBuyStopOrderTakeProfit = 18
    ModifiedSellStopOrderTakeProfit = 19
    ClosedBuyStopOrder = 20
    ClosedSellStopOrder = 21
    FilledBuyStopOrder = 22
    FilledSellStopOrder = 23
    ExpiredBuyStopOrder = 24
    ExpiredSellStopOrder = 25
    OpenedBuyLimitOrder = 26
    OpenedSellLimitOrder = 27
    ModifiedBuyLimitOrderVolume = 28
    ModifiedSellLimitOrderVolume = 29
    ModifiedBuyLimitOrderLimitPrice = 30
    ModifiedSellLimitOrderLimitPrice = 31
    ModifiedBuyLimitOrderStopLoss = 32
    ModifiedSellLimitOrderStopLoss = 33
    ModifiedBuyLimitOrderTakeProfit = 34
    ModifiedSellLimitOrderTakeProfit = 35
    ClosedBuyLimitOrder = 36
    ClosedSellLimitOrder = 37
    FilledBuyLimitOrder = 38
    FilledSellLimitOrder = 39
    ExpiredBuyLimitOrder = 40
    ExpiredSellLimitOrder = 41
    OpenedBuyStopLimitOrder = 42
    OpenedSellStopLimitOrder = 43
    ModifiedBuyStopLimitOrderVolume = 44
    ModifiedSellStopLimitOrderVolume = 45
    ModifiedBuyStopLimitOrderStopPrice = 46
    ModifiedSellStopLimitOrderStopPrice = 47
    ModifiedBuyStopLimitOrderLimitPrice = 48
    ModifiedSellStopLimitOrderLimitPrice = 49
    ModifiedBuyStopLimitOrderStopLoss = 50
    ModifiedSellStopLimitOrderStopLoss = 51
    ModifiedBuyStopLimitOrderTakeProfit = 52
    ModifiedSellStopLimitOrderTakeProfit = 53
    ClosedBuyStopLimitOrder = 54
    ClosedSellStopLimitOrder = 55
    FilledBuyStopLimitOrder = 56
    FilledSellStopLimitOrder = 57
    ExpiredBuyStopLimitOrder = 58
    ExpiredSellStopLimitOrder = 59
    OpenedBuyPosition = 60
    OpenedSellPosition = 61
    ModifiedBuyPositionVolume = 62
    ModifiedSellPositionVolume = 63
    ModifiedBuyPositionStopLoss = 64
    ModifiedSellPositionStopLoss = 65
    ModifiedBuyPositionTakeProfit = 66
    ModifiedSellPositionTakeProfit = 67
    ClosedBuyPosition = 68
    ClosedSellPosition = 69
    StopLossBuyPosition = 70
    StopLossSellPosition = 71
    TakeProfitBuyPosition = 72
    TakeProfitSellPosition = 73
    MarginCallBuyPosition = 74
    MarginCallSellPosition = 75
    Complete = 76
    Denied = 77
    Exception = 78
    Shutdown = 79

@dataclass(slots=True)
class UpdateAPI(DataclassAPI):
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
class AccountUpdateAPI(UpdateAPI):
    pass

@dataclass(slots=True)
class SecurityUpdateAPI(UpdateAPI):
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
    "AccountUpdateAPI",
    "SecurityUpdateAPI",
    "TickUpdateAPI",
    "BarUpdateAPI"
]