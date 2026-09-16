from typing import Union, ClassVar
from dataclasses import dataclass

from Library.Market.Price import Direction
from Library.Utility.Typing import cast
from Library.Protocol.Binary import BinaryAPI
from Library.Protocol.Action.Action import ActionAPI, ActionID

@dataclass(slots=True)
class _OpenStopOrderActionAPI_(ActionAPI):

    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'd', 'd', 'D', 'D')
    Volume: float
    StopPrice: float
    StopLoss: Union[float, None]
    TakeProfit: Union[float, None]

    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)
        self.StopLoss = cast(self.StopLoss, float, None)
        self.TakeProfit = cast(self.TakeProfit, float, None)

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.Volume, self.StopPrice, self.StopLoss, self.TakeProfit)

@dataclass(slots=True)
class _OpenLimitOrderActionAPI_(ActionAPI):

    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'd', 'd', 'D', 'D')
    Volume: float
    LimitPrice: float
    StopLoss: Union[float, None]
    TakeProfit: Union[float, None]

    def __post_init__(self):
        self.LimitPrice = cast(self.LimitPrice, float, None)
        self.StopLoss = cast(self.StopLoss, float, None)
        self.TakeProfit = cast(self.TakeProfit, float, None)

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.Volume, self.LimitPrice, self.StopLoss, self.TakeProfit)

@dataclass(slots=True)
class _OpenStopLimitOrderActionAPI_(ActionAPI):

    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'd', 'd', 'd', 'D', 'D')
    Volume: float
    StopPrice: float
    LimitPrice: float
    StopLoss: Union[float, None]
    TakeProfit: Union[float, None]

    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)
        self.LimitPrice = cast(self.LimitPrice, float, None)
        self.StopLoss = cast(self.StopLoss, float, None)
        self.TakeProfit = cast(self.TakeProfit, float, None)

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.Volume, self.StopPrice, self.LimitPrice, self.StopLoss, self.TakeProfit)

@dataclass(slots=True)
class _ModifyOrderVolumeActionAPI_(ActionAPI):

    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class _ModifyOrderStopPriceActionAPI_(ActionAPI):

    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    StopPrice: float

    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.StopPrice)

@dataclass(slots=True)
class _ModifyOrderLimitPriceActionAPI_(ActionAPI):

    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    LimitPrice: float

    def __post_init__(self):
        self.LimitPrice = cast(self.LimitPrice, float, None)

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.LimitPrice)

@dataclass(slots=True)
class _ModifyOrderStopLossActionAPI_(ActionAPI):

    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    StopLoss: Union[float, None]

    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.StopLoss)

@dataclass(slots=True)
class _ModifyOrderTakeProfitActionAPI_(ActionAPI):

    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    TakeProfit: Union[float, None]

    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.TakeProfit)

@dataclass(slots=True)
class _CloseOrderActionAPI_(ActionAPI):

    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    OrderID: int

    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID)

@dataclass(slots=True)
class OpenBuyStopOrderActionAPI(_OpenStopOrderActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.OpenBuyStopOrder
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class OpenSellStopOrderActionAPI(_OpenStopOrderActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.OpenSellStopOrder
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyStopOrderVolumeActionAPI(_ModifyOrderVolumeActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderVolume
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellStopOrderVolumeActionAPI(_ModifyOrderVolumeActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderVolume
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyStopOrderStopPriceActionAPI(_ModifyOrderStopPriceActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderStopPrice
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellStopOrderStopPriceActionAPI(_ModifyOrderStopPriceActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderStopPrice
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyStopOrderStopLossActionAPI(_ModifyOrderStopLossActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderStopLoss
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellStopOrderStopLossActionAPI(_ModifyOrderStopLossActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderStopLoss
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyStopOrderTakeProfitActionAPI(_ModifyOrderTakeProfitActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderTakeProfit
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellStopOrderTakeProfitActionAPI(_ModifyOrderTakeProfitActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderTakeProfit
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class CloseBuyStopOrderActionAPI(_CloseOrderActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.CloseBuyStopOrder
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class CloseSellStopOrderActionAPI(_CloseOrderActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.CloseSellStopOrder
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class OpenBuyLimitOrderActionAPI(_OpenLimitOrderActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.OpenBuyLimitOrder
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class OpenSellLimitOrderActionAPI(_OpenLimitOrderActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.OpenSellLimitOrder
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyLimitOrderVolumeActionAPI(_ModifyOrderVolumeActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderVolume
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellLimitOrderVolumeActionAPI(_ModifyOrderVolumeActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderVolume
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyLimitOrderLimitPriceActionAPI(_ModifyOrderLimitPriceActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderLimitPrice
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellLimitOrderLimitPriceActionAPI(_ModifyOrderLimitPriceActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderLimitPrice
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyLimitOrderStopLossActionAPI(_ModifyOrderStopLossActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderStopLoss
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellLimitOrderStopLossActionAPI(_ModifyOrderStopLossActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderStopLoss
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyLimitOrderTakeProfitActionAPI(_ModifyOrderTakeProfitActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderTakeProfit
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellLimitOrderTakeProfitActionAPI(_ModifyOrderTakeProfitActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderTakeProfit
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class CloseBuyLimitOrderActionAPI(_CloseOrderActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.CloseBuyLimitOrder
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class CloseSellLimitOrderActionAPI(_CloseOrderActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.CloseSellLimitOrder
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class OpenBuyStopLimitOrderActionAPI(_OpenStopLimitOrderActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.OpenBuyStopLimitOrder
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class OpenSellStopLimitOrderActionAPI(_OpenStopLimitOrderActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.OpenSellStopLimitOrder
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyStopLimitOrderVolumeActionAPI(_ModifyOrderVolumeActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderVolume
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellStopLimitOrderVolumeActionAPI(_ModifyOrderVolumeActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderVolume
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyStopLimitOrderStopPriceActionAPI(_ModifyOrderStopPriceActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderStopPrice
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellStopLimitOrderStopPriceActionAPI(_ModifyOrderStopPriceActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderStopPrice
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyStopLimitOrderLimitPriceActionAPI(_ModifyOrderLimitPriceActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderLimitPrice
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellStopLimitOrderLimitPriceActionAPI(_ModifyOrderLimitPriceActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderLimitPrice
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyStopLimitOrderStopLossActionAPI(_ModifyOrderStopLossActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderStopLoss
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellStopLimitOrderStopLossActionAPI(_ModifyOrderStopLossActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderStopLoss
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifyBuyStopLimitOrderTakeProfitActionAPI(_ModifyOrderTakeProfitActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderTakeProfit
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifySellStopLimitOrderTakeProfitActionAPI(_ModifyOrderTakeProfitActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderTakeProfit
    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class CloseBuyStopLimitOrderActionAPI(_CloseOrderActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.CloseBuyStopLimitOrder
    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class CloseSellStopLimitOrderActionAPI(_CloseOrderActionAPI_):

    ActionID: ClassVar[ActionID] = ActionID.CloseSellStopLimitOrder
    Direction: ClassVar[Direction] = Direction.Sell

__all__ = [
    "OpenBuyStopOrderActionAPI",
    "OpenSellStopOrderActionAPI",
    "ModifyBuyStopOrderVolumeActionAPI",
    "ModifySellStopOrderVolumeActionAPI",
    "ModifyBuyStopOrderStopPriceActionAPI",
    "ModifySellStopOrderStopPriceActionAPI",
    "ModifyBuyStopOrderStopLossActionAPI",
    "ModifySellStopOrderStopLossActionAPI",
    "ModifyBuyStopOrderTakeProfitActionAPI",
    "ModifySellStopOrderTakeProfitActionAPI",
    "CloseBuyStopOrderActionAPI",
    "CloseSellStopOrderActionAPI",
    "OpenBuyLimitOrderActionAPI",
    "OpenSellLimitOrderActionAPI",
    "ModifyBuyLimitOrderVolumeActionAPI",
    "ModifySellLimitOrderVolumeActionAPI",
    "ModifyBuyLimitOrderLimitPriceActionAPI",
    "ModifySellLimitOrderLimitPriceActionAPI",
    "ModifyBuyLimitOrderStopLossActionAPI",
    "ModifySellLimitOrderStopLossActionAPI",
    "ModifyBuyLimitOrderTakeProfitActionAPI",
    "ModifySellLimitOrderTakeProfitActionAPI",
    "CloseBuyLimitOrderActionAPI",
    "CloseSellLimitOrderActionAPI",
    "OpenBuyStopLimitOrderActionAPI",
    "OpenSellStopLimitOrderActionAPI",
    "ModifyBuyStopLimitOrderVolumeActionAPI",
    "ModifySellStopLimitOrderVolumeActionAPI",
    "ModifyBuyStopLimitOrderStopPriceActionAPI",
    "ModifySellStopLimitOrderStopPriceActionAPI",
    "ModifyBuyStopLimitOrderLimitPriceActionAPI",
    "ModifySellStopLimitOrderLimitPriceActionAPI",
    "ModifyBuyStopLimitOrderStopLossActionAPI",
    "ModifySellStopLimitOrderStopLossActionAPI",
    "ModifyBuyStopLimitOrderTakeProfitActionAPI",
    "ModifySellStopLimitOrderTakeProfitActionAPI",
    "CloseBuyStopLimitOrderActionAPI",
    "CloseSellStopLimitOrderActionAPI"
]