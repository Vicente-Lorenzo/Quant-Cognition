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
    Complete = 0
    Account = 1
    Security = 2
    OpenedBuyPosition = 3
    OpenedSellPosition = 4
    ModifiedBuyPositionVolume = 5
    ModifiedBuyPositionStopLoss = 6
    ModifiedBuyPositionTakeProfit = 7
    ModifiedSellPositionVolume = 8
    ModifiedSellPositionStopLoss = 9
    ModifiedSellPositionTakeProfit = 10
    ClosedBuyPosition = 11
    ClosedSellPosition = 12
    BarClosed = 13
    AskAboveTarget = 14
    AskBelowTarget = 15
    BidAboveTarget = 16
    BidBelowTarget = 17
    Shutdown = 18
    OpenedBuyStopOrder = 19
    OpenedSellStopOrder = 20
    ModifiedBuyStopOrderVolume = 21
    ModifiedBuyStopOrderStopPrice = 22
    ModifiedBuyStopOrderStopLoss = 23
    ModifiedBuyStopOrderTakeProfit = 24
    ModifiedSellStopOrderVolume = 25
    ModifiedSellStopOrderStopPrice = 26
    ModifiedSellStopOrderStopLoss = 27
    ModifiedSellStopOrderTakeProfit = 28
    ClosedBuyStopOrder = 29
    ClosedSellStopOrder = 30
    FilledBuyStopOrder = 31
    FilledSellStopOrder = 32
    ExpiredBuyStopOrder = 33
    ExpiredSellStopOrder = 34
    OpenedBuyLimitOrder = 35
    OpenedSellLimitOrder = 36
    ModifiedBuyLimitOrderVolume = 37
    ModifiedBuyLimitOrderLimitPrice = 38
    ModifiedBuyLimitOrderStopLoss = 39
    ModifiedBuyLimitOrderTakeProfit = 40
    ModifiedSellLimitOrderVolume = 41
    ModifiedSellLimitOrderLimitPrice = 42
    ModifiedSellLimitOrderStopLoss = 43
    ModifiedSellLimitOrderTakeProfit = 44
    ClosedBuyLimitOrder = 45
    ClosedSellLimitOrder = 46
    FilledBuyLimitOrder = 47
    FilledSellLimitOrder = 48
    ExpiredBuyLimitOrder = 49
    ExpiredSellLimitOrder = 50
    OpenedBuyStopLimitOrder = 51
    OpenedSellStopLimitOrder = 52
    ModifiedBuyStopLimitOrderVolume = 53
    ModifiedBuyStopLimitOrderStopPrice = 54
    ModifiedBuyStopLimitOrderLimitPrice = 55
    ModifiedBuyStopLimitOrderStopLoss = 56
    ModifiedBuyStopLimitOrderTakeProfit = 57
    ModifiedSellStopLimitOrderVolume = 58
    ModifiedSellStopLimitOrderStopPrice = 59
    ModifiedSellStopLimitOrderLimitPrice = 60
    ModifiedSellStopLimitOrderStopLoss = 61
    ModifiedSellStopLimitOrderTakeProfit = 62
    ClosedBuyStopLimitOrder = 63
    ClosedSellStopLimitOrder = 64
    FilledBuyStopLimitOrder = 65
    FilledSellStopLimitOrder = 66
    ExpiredBuyStopLimitOrder = 67
    ExpiredSellStopLimitOrder = 68
    StopLossBuyPosition = 69
    StopLossSellPosition = 70
    TakeProfitBuyPosition = 71
    TakeProfitSellPosition = 72
    MarginCallBuyPosition = 73
    MarginCallSellPosition = 74
    Denied = 75
    Exception = 76

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
class BarUpdateAPI(UpdateAPI):
    Bar: BarAPI

@dataclass(slots=True)
class TickUpdateAPI(UpdateAPI):
    Tick: TickAPI

__all__ = [
    "UpdateID",
    "UpdateAPI",
    "CompleteUpdateAPI",
    "AccountUpdateAPI",
    "SecurityUpdateAPI",
    "BarUpdateAPI",
    "TickUpdateAPI"
]