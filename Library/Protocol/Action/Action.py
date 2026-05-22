from __future__ import annotations

from typing import Union, ClassVar
from dataclasses import dataclass

from Library.Database.Dataclass import DataclassAPI
from Library.Utility.Enumeration import EnumerationAPI
from Library.Utility.Typing import cast

class ActionID(EnumerationAPI):
    Complete = 0
    OpenBuyPosition = 1
    OpenSellPosition = 2
    ModifyBuyPositionVolume = 3
    ModifyBuyPositionStopLoss = 4
    ModifyBuyPositionTakeProfit = 5
    ModifySellPositionVolume = 6
    ModifySellPositionStopLoss = 7
    ModifySellPositionTakeProfit = 8
    CloseBuyPosition = 9
    CloseSellPosition = 10
    AskAboveTarget = 11
    AskBelowTarget = 12
    BidAboveTarget = 13
    BidBelowTarget = 14
    OpenBuyStopOrder = 15
    OpenSellStopOrder = 16
    ModifyBuyStopOrderVolume = 17
    ModifyBuyStopOrderStopPrice = 18
    ModifyBuyStopOrderStopLoss = 19
    ModifyBuyStopOrderTakeProfit = 20
    ModifySellStopOrderVolume = 21
    ModifySellStopOrderStopPrice = 22
    ModifySellStopOrderStopLoss = 23
    ModifySellStopOrderTakeProfit = 24
    CloseBuyStopOrder = 25
    CloseSellStopOrder = 26
    OpenBuyLimitOrder = 27
    OpenSellLimitOrder = 28
    ModifyBuyLimitOrderVolume = 29
    ModifyBuyLimitOrderLimitPrice = 30
    ModifyBuyLimitOrderStopLoss = 31
    ModifyBuyLimitOrderTakeProfit = 32
    ModifySellLimitOrderVolume = 33
    ModifySellLimitOrderLimitPrice = 34
    ModifySellLimitOrderStopLoss = 35
    ModifySellLimitOrderTakeProfit = 36
    CloseBuyLimitOrder = 37
    CloseSellLimitOrder = 38
    OpenBuyStopLimitOrder = 39
    OpenSellStopLimitOrder = 40
    ModifyBuyStopLimitOrderVolume = 41
    ModifyBuyStopLimitOrderStopPrice = 42
    ModifyBuyStopLimitOrderLimitPrice = 43
    ModifyBuyStopLimitOrderStopLoss = 44
    ModifyBuyStopLimitOrderTakeProfit = 45
    ModifySellStopLimitOrderVolume = 46
    ModifySellStopLimitOrderStopPrice = 47
    ModifySellStopLimitOrderLimitPrice = 48
    ModifySellStopLimitOrderStopLoss = 49
    ModifySellStopLimitOrderTakeProfit = 50
    CloseBuyStopLimitOrder = 51
    CloseSellStopLimitOrder = 52

@dataclass(slots=True)
class ActionAPI(DataclassAPI):
    ActionID: ClassVar[ActionID]
    def serialize(self) -> str:
        return self.json(include_initvar_fields=True, ActionID=self.ActionID.value)

@dataclass(slots=True)
class CompleteActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.Complete

@dataclass(slots=True)
class AskAboveTargetActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.AskAboveTarget
    Ask: Union[float, None]
    def __post_init__(self):
        self.Ask = cast(self.Ask, float, None)

@dataclass(slots=True)
class AskBelowTargetActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.AskBelowTarget
    Ask: Union[float, None]
    def __post_init__(self):
        self.Ask = cast(self.Ask, float, None)

@dataclass(slots=True)
class BidAboveTargetActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.BidAboveTarget
    Bid: Union[float, None]
    def __post_init__(self):
        self.Bid = cast(self.Bid, float, None)

@dataclass(slots=True)
class BidBelowTargetActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.BidBelowTarget
    Bid: Union[float, None]
    def __post_init__(self):
        self.Bid = cast(self.Bid, float, None)

__all__ = [
    "ActionID",
    "ActionAPI",
    "CompleteActionAPI",
    "AskAboveTargetActionAPI",
    "AskBelowTargetActionAPI",
    "BidAboveTargetActionAPI",
    "BidBelowTargetActionAPI"
]