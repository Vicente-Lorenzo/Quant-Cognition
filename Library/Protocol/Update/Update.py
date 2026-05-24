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
    Tick = 13
    BarOpened = 14
    BarClosed = 15
    AskAboveTarget = 16
    AskBelowTarget = 17
    BidAboveTarget = 18
    BidBelowTarget = 19
    Shutdown = 20
    OpenedBuyStopOrder = 21
    OpenedSellStopOrder = 22
    ModifiedBuyStopOrderVolume = 23
    ModifiedBuyStopOrderStopPrice = 24
    ModifiedBuyStopOrderStopLoss = 25
    ModifiedBuyStopOrderTakeProfit = 26
    ModifiedSellStopOrderVolume = 27
    ModifiedSellStopOrderStopPrice = 28
    ModifiedSellStopOrderStopLoss = 29
    ModifiedSellStopOrderTakeProfit = 30
    ClosedBuyStopOrder = 31
    ClosedSellStopOrder = 32
    FilledBuyStopOrder = 33
    FilledSellStopOrder = 34
    ExpiredBuyStopOrder = 35
    ExpiredSellStopOrder = 36
    OpenedBuyLimitOrder = 37
    OpenedSellLimitOrder = 38
    ModifiedBuyLimitOrderVolume = 39
    ModifiedBuyLimitOrderLimitPrice = 40
    ModifiedBuyLimitOrderStopLoss = 41
    ModifiedBuyLimitOrderTakeProfit = 42
    ModifiedSellLimitOrderVolume = 43
    ModifiedSellLimitOrderLimitPrice = 44
    ModifiedSellLimitOrderStopLoss = 45
    ModifiedSellLimitOrderTakeProfit = 46
    ClosedBuyLimitOrder = 47
    ClosedSellLimitOrder = 48
    FilledBuyLimitOrder = 49
    FilledSellLimitOrder = 50
    ExpiredBuyLimitOrder = 51
    ExpiredSellLimitOrder = 52
    OpenedBuyStopLimitOrder = 53
    OpenedSellStopLimitOrder = 54
    ModifiedBuyStopLimitOrderVolume = 55
    ModifiedBuyStopLimitOrderStopPrice = 56
    ModifiedBuyStopLimitOrderLimitPrice = 57
    ModifiedBuyStopLimitOrderStopLoss = 58
    ModifiedBuyStopLimitOrderTakeProfit = 59
    ModifiedSellStopLimitOrderVolume = 60
    ModifiedSellStopLimitOrderStopPrice = 61
    ModifiedSellStopLimitOrderLimitPrice = 62
    ModifiedSellStopLimitOrderStopLoss = 63
    ModifiedSellStopLimitOrderTakeProfit = 64
    ClosedBuyStopLimitOrder = 65
    ClosedSellStopLimitOrder = 66
    FilledBuyStopLimitOrder = 67
    FilledSellStopLimitOrder = 68
    ExpiredBuyStopLimitOrder = 69
    ExpiredSellStopLimitOrder = 70
    StopLossBuyPosition = 71
    StopLossSellPosition = 72
    TakeProfitBuyPosition = 73
    TakeProfitSellPosition = 74
    MarginCallBuyPosition = 75
    MarginCallSellPosition = 76
    Denied = 77
    Exception = 78

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