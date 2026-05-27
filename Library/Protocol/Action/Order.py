from __future__ import annotations

from typing import Union, ClassVar
from dataclasses import dataclass

from Library.Utility.Typing import cast
from Library.Protocol.Binary import BinaryAPI
from Library.Protocol.Action.Action import ActionAPI, ActionID

@dataclass(slots=True)
class OpenBuyStopOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenBuyStopOrder
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
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class ModifySellStopOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderVolume
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class ModifyBuyStopOrderStopPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderStopPrice
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
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    OrderID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID)

@dataclass(slots=True)
class CloseSellStopOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseSellStopOrder
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    OrderID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID)

@dataclass(slots=True)
class OpenBuyLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenBuyLimitOrder
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
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class ModifySellLimitOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderVolume
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class ModifyBuyLimitOrderLimitPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderLimitPrice
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
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    OrderID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID)

@dataclass(slots=True)
class CloseSellLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseSellLimitOrder
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    OrderID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID)

@dataclass(slots=True)
class OpenBuyStopLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenBuyStopLimitOrder
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
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class ModifySellStopLimitOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderVolume
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    OrderID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID, self.Volume)

@dataclass(slots=True)
class ModifyBuyStopLimitOrderStopPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderStopPrice
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
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    OrderID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.OrderID)

@dataclass(slots=True)
class CloseSellStopLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseSellStopLimitOrder
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