from __future__ import annotations

from typing import Union, ClassVar
from dataclasses import dataclass

from Library.Protocol.Binary import BinaryAPI
from Library.Database.Dataclass import DataclassAPI
from Library.Utility.Enumeration import EnumerationAPI
from Library.Utility.Typing import cast

class ActionID(EnumerationAPI):
    Init = 0
    AskAboveTarget = 1
    AskBelowTarget = 2
    BidAboveTarget = 3
    BidBelowTarget = 4
    OpenBuyStopOrder = 5
    OpenSellStopOrder = 6
    ModifyBuyStopOrderVolume = 7
    ModifySellStopOrderVolume = 8
    ModifyBuyStopOrderStopPrice = 9
    ModifySellStopOrderStopPrice = 10
    ModifyBuyStopOrderStopLoss = 11
    ModifySellStopOrderStopLoss = 12
    ModifyBuyStopOrderTakeProfit = 13
    ModifySellStopOrderTakeProfit = 14
    CloseBuyStopOrder = 15
    CloseSellStopOrder = 16
    OpenBuyLimitOrder = 17
    OpenSellLimitOrder = 18
    ModifyBuyLimitOrderVolume = 19
    ModifySellLimitOrderVolume = 20
    ModifyBuyLimitOrderLimitPrice = 21
    ModifySellLimitOrderLimitPrice = 22
    ModifyBuyLimitOrderStopLoss = 23
    ModifySellLimitOrderStopLoss = 24
    ModifyBuyLimitOrderTakeProfit = 25
    ModifySellLimitOrderTakeProfit = 26
    CloseBuyLimitOrder = 27
    CloseSellLimitOrder = 28
    OpenBuyStopLimitOrder = 29
    OpenSellStopLimitOrder = 30
    ModifyBuyStopLimitOrderVolume = 31
    ModifySellStopLimitOrderVolume = 32
    ModifyBuyStopLimitOrderStopPrice = 33
    ModifySellStopLimitOrderStopPrice = 34
    ModifyBuyStopLimitOrderLimitPrice = 35
    ModifySellStopLimitOrderLimitPrice = 36
    ModifyBuyStopLimitOrderStopLoss = 37
    ModifySellStopLimitOrderStopLoss = 38
    ModifyBuyStopLimitOrderTakeProfit = 39
    ModifySellStopLimitOrderTakeProfit = 40
    CloseBuyStopLimitOrder = 41
    CloseSellStopLimitOrder = 42
    OpenBuyPosition = 43
    OpenSellPosition = 44
    ModifyBuyPositionVolume = 45
    ModifySellPositionVolume = 46
    ModifyBuyPositionStopLoss = 47
    ModifySellPositionStopLoss = 48
    ModifyBuyPositionTakeProfit = 49
    ModifySellPositionTakeProfit = 50
    CloseBuyPosition = 51
    CloseSellPosition = 52
    Complete = 53

@dataclass(slots=True)
class ActionAPI(DataclassAPI):
    ActionID: ClassVar[ActionID]
    def serialize(self) -> bytes:
        raise NotImplementedError

@dataclass(slots=True)
class CompleteActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.Complete
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B')
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value)

@dataclass(slots=True)
class InitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.Init
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    ProcessID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.ProcessID)

@dataclass(slots=True)
class AskAboveTargetActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.AskAboveTarget
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'D')
    Ask: Union[float, None]
    def __post_init__(self):
        self.Ask = cast(self.Ask, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.Ask)

@dataclass(slots=True)
class AskBelowTargetActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.AskBelowTarget
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'D')
    Ask: Union[float, None]
    def __post_init__(self):
        self.Ask = cast(self.Ask, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.Ask)

@dataclass(slots=True)
class BidAboveTargetActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.BidAboveTarget
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'D')
    Bid: Union[float, None]
    def __post_init__(self):
        self.Bid = cast(self.Bid, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.Bid)

@dataclass(slots=True)
class BidBelowTargetActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.BidBelowTarget
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'D')
    Bid: Union[float, None]
    def __post_init__(self):
        self.Bid = cast(self.Bid, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.Bid)

__all__ = [
    "ActionID",
    "ActionAPI",
    "CompleteActionAPI",
    "InitActionAPI",
    "AskAboveTargetActionAPI",
    "AskBelowTargetActionAPI",
    "BidAboveTargetActionAPI",
    "BidBelowTargetActionAPI"
]