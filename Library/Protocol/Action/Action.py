from enum import IntFlag
from typing import Union, ClassVar
from dataclasses import dataclass

from Library.Market.Price import Direction
from Library.Protocol.Binary import BinaryAPI
from Library.Database.Dataclass import DataclassAPI
from Library.Utility.Enumeration import EnumerationAPI
from Library.Utility.Typing import cast

class ActionID(EnumerationAPI):

    Init = 0
    Execution = 1
    AskAboveTarget = 2
    AskBelowTarget = 3
    BidAboveTarget = 4
    BidBelowTarget = 5
    OpenBuyStopOrder = 6
    OpenSellStopOrder = 7
    ModifyBuyStopOrderVolume = 8
    ModifySellStopOrderVolume = 9
    ModifyBuyStopOrderStopPrice = 10
    ModifySellStopOrderStopPrice = 11
    ModifyBuyStopOrderStopLoss = 12
    ModifySellStopOrderStopLoss = 13
    ModifyBuyStopOrderTakeProfit = 14
    ModifySellStopOrderTakeProfit = 15
    CloseBuyStopOrder = 16
    CloseSellStopOrder = 17
    OpenBuyLimitOrder = 18
    OpenSellLimitOrder = 19
    ModifyBuyLimitOrderVolume = 20
    ModifySellLimitOrderVolume = 21
    ModifyBuyLimitOrderLimitPrice = 22
    ModifySellLimitOrderLimitPrice = 23
    ModifyBuyLimitOrderStopLoss = 24
    ModifySellLimitOrderStopLoss = 25
    ModifyBuyLimitOrderTakeProfit = 26
    ModifySellLimitOrderTakeProfit = 27
    CloseBuyLimitOrder = 28
    CloseSellLimitOrder = 29
    OpenBuyStopLimitOrder = 30
    OpenSellStopLimitOrder = 31
    ModifyBuyStopLimitOrderVolume = 32
    ModifySellStopLimitOrderVolume = 33
    ModifyBuyStopLimitOrderStopPrice = 34
    ModifySellStopLimitOrderStopPrice = 35
    ModifyBuyStopLimitOrderLimitPrice = 36
    ModifySellStopLimitOrderLimitPrice = 37
    ModifyBuyStopLimitOrderStopLoss = 38
    ModifySellStopLimitOrderStopLoss = 39
    ModifyBuyStopLimitOrderTakeProfit = 40
    ModifySellStopLimitOrderTakeProfit = 41
    CloseBuyStopLimitOrder = 42
    CloseSellStopLimitOrder = 43
    OpenBuyPosition = 44
    OpenSellPosition = 45
    IncreaseBuyPositionVolume = 46
    IncreaseSellPositionVolume = 47
    DecreaseBuyPositionVolume = 48
    DecreaseSellPositionVolume = 49
    ModifyBuyPositionVolume = 50
    ModifySellPositionVolume = 51
    ModifyBuyPositionStopLoss = 52
    ModifySellPositionStopLoss = 53
    ModifyBuyPositionTakeProfit = 54
    ModifySellPositionTakeProfit = 55
    CloseBuyPosition = 56
    CloseSellPosition = 57
    Subscribe = 58
    Unsubscribe = 59
    Shutdown = 60
    Complete = 61

@dataclass(slots=True)
class ActionAPI(DataclassAPI):

    ActionID: ClassVar[ActionID]
    Direction: ClassVar[Direction] = Direction.Neutral

    def serialize(self) -> bytes:
        raise NotImplementedError

@dataclass(slots=True)
class CompleteActionAPI(ActionAPI):

    ActionID: ClassVar[ActionID] = ActionID.Complete
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B')

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value)

@dataclass(slots=True)
class ShutdownActionAPI(ActionAPI):

    ActionID: ClassVar[ActionID] = ActionID.Shutdown
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
class ExecutionActionAPI(ActionAPI):

    ActionID: ClassVar[ActionID] = ActionID.Execution
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B')

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value)

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

class Stream(IntFlag):

    Tick = 1
    BarOpened = 2
    BarClosed = 4
    Order = 8
    Position = 16
    Trade = 32
    All = Tick | BarOpened | BarClosed | Order | Position | Trade

@dataclass(slots=True)
class SubscribeActionAPI(ActionAPI):

    ActionID: ClassVar[ActionID] = ActionID.Subscribe
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'B')
    Streams: int

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.Streams)

@dataclass(slots=True)
class UnsubscribeActionAPI(ActionAPI):

    ActionID: ClassVar[ActionID] = ActionID.Unsubscribe
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'B')
    Streams: int

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.Streams)

__all__ = [
    "ActionID",
    "ActionAPI",
    "CompleteActionAPI",
    "ShutdownActionAPI",
    "InitActionAPI",
    "ExecutionActionAPI",
    "AskAboveTargetActionAPI",
    "AskBelowTargetActionAPI",
    "BidAboveTargetActionAPI",
    "BidBelowTargetActionAPI",
    "Stream",
    "SubscribeActionAPI",
    "UnsubscribeActionAPI"
]