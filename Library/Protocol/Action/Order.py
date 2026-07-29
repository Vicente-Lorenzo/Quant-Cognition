from __future__ import annotations

from typing import Union, ClassVar
from dataclasses import dataclass

from Library.Market.Price import Direction
from Library.Utility.Typing import cast
from Library.Protocol.Binary import BinaryAPI
from Library.Protocol.Action.Action import ActionAPI, ActionID

@dataclass(slots=True)
class OpenBuyStopOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenBuyStopOrder
    Direction: ClassVar[Direction] = Direction.Buy
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
class OpenSellStopOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenSellStopOrder
    Direction: ClassVar[Direction] = Direction.Sell
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
class ModifyBuyStopOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderVolume
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class ModifySellStopOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderVolume
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class ModifyBuyStopOrderStopPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderStopPrice
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    StopPrice: float
    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.StopPrice)

@dataclass(slots=True)
class ModifySellStopOrderStopPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderStopPrice
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    StopPrice: float
    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.StopPrice)

@dataclass(slots=True)
class ModifyBuyStopOrderStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderStopLoss
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.StopLoss)

@dataclass(slots=True)
class ModifySellStopOrderStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderStopLoss
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.StopLoss)

@dataclass(slots=True)
class ModifyBuyStopOrderTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderTakeProfit
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.TakeProfit)

@dataclass(slots=True)
class ModifySellStopOrderTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderTakeProfit
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.TakeProfit)

@dataclass(slots=True)
class CloseBuyStopOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseBuyStopOrder
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    OrderID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID)

@dataclass(slots=True)
class CloseSellStopOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseSellStopOrder
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    OrderID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID)

@dataclass(slots=True)
class OpenBuyLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenBuyLimitOrder
    Direction: ClassVar[Direction] = Direction.Buy
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
class OpenSellLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenSellLimitOrder
    Direction: ClassVar[Direction] = Direction.Sell
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
class ModifyBuyLimitOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderVolume
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class ModifySellLimitOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderVolume
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class ModifyBuyLimitOrderLimitPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderLimitPrice
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    LimitPrice: float
    def __post_init__(self):
        self.LimitPrice = cast(self.LimitPrice, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.LimitPrice)

@dataclass(slots=True)
class ModifySellLimitOrderLimitPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderLimitPrice
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    LimitPrice: float
    def __post_init__(self):
        self.LimitPrice = cast(self.LimitPrice, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.LimitPrice)

@dataclass(slots=True)
class ModifyBuyLimitOrderStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderStopLoss
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.StopLoss)

@dataclass(slots=True)
class ModifySellLimitOrderStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderStopLoss
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.StopLoss)

@dataclass(slots=True)
class ModifyBuyLimitOrderTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderTakeProfit
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.TakeProfit)

@dataclass(slots=True)
class ModifySellLimitOrderTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderTakeProfit
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.TakeProfit)

@dataclass(slots=True)
class CloseBuyLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseBuyLimitOrder
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    OrderID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID)

@dataclass(slots=True)
class CloseSellLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseSellLimitOrder
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    OrderID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID)

@dataclass(slots=True)
class OpenBuyStopLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenBuyStopLimitOrder
    Direction: ClassVar[Direction] = Direction.Buy
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
class OpenSellStopLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenSellStopLimitOrder
    Direction: ClassVar[Direction] = Direction.Sell
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
class ModifyBuyStopLimitOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderVolume
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class ModifySellStopLimitOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderVolume
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class ModifyBuyStopLimitOrderStopPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderStopPrice
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    StopPrice: float
    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.StopPrice)

@dataclass(slots=True)
class ModifySellStopLimitOrderStopPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderStopPrice
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    StopPrice: float
    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.StopPrice)

@dataclass(slots=True)
class ModifyBuyStopLimitOrderLimitPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderLimitPrice
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    LimitPrice: float
    def __post_init__(self):
        self.LimitPrice = cast(self.LimitPrice, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.LimitPrice)

@dataclass(slots=True)
class ModifySellStopLimitOrderLimitPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderLimitPrice
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    LimitPrice: float
    def __post_init__(self):
        self.LimitPrice = cast(self.LimitPrice, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.LimitPrice)

@dataclass(slots=True)
class ModifyBuyStopLimitOrderStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderStopLoss
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.StopLoss)

@dataclass(slots=True)
class ModifySellStopLimitOrderStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderStopLoss
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.StopLoss)

@dataclass(slots=True)
class ModifyBuyStopLimitOrderTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderTakeProfit
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.TakeProfit)

@dataclass(slots=True)
class ModifySellStopLimitOrderTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderTakeProfit
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    OrderID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.TakeProfit)

@dataclass(slots=True)
class CloseBuyStopLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseBuyStopLimitOrder
    Direction: ClassVar[Direction] = Direction.Buy
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    OrderID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID)

@dataclass(slots=True)
class CloseSellStopLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseSellStopLimitOrder
    Direction: ClassVar[Direction] = Direction.Sell
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    OrderID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID)

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