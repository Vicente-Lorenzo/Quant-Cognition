from __future__ import annotations

from typing import Union, ClassVar
from dataclasses import dataclass

from Library.Protocol.Action.Action import ActionAPI, ActionID
from Library.Utility.Typing import cast

@dataclass(slots=True)
class OpenBuyStopOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenBuyStopOrder
    Volume: float
    StopPrice: float
    StopLoss: Union[float, None]
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)
        self.StopLoss = cast(self.StopLoss, float, None)
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class OpenSellStopOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenSellStopOrder
    Volume: float
    StopPrice: float
    StopLoss: Union[float, None]
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)
        self.StopLoss = cast(self.StopLoss, float, None)
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class ModifyBuyStopOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderVolume
    OrderID: int
    Volume: float

@dataclass(slots=True)
class ModifySellStopOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderVolume
    OrderID: int
    Volume: float

@dataclass(slots=True)
class ModifyBuyStopOrderStopPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderStopPrice
    OrderID: int
    StopPrice: float
    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)

@dataclass(slots=True)
class ModifySellStopOrderStopPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderStopPrice
    OrderID: int
    StopPrice: float
    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)

@dataclass(slots=True)
class ModifyBuyStopOrderStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderStopLoss
    OrderID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)

@dataclass(slots=True)
class ModifySellStopOrderStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderStopLoss
    OrderID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)

@dataclass(slots=True)
class ModifyBuyStopOrderTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopOrderTakeProfit
    OrderID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class ModifySellStopOrderTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopOrderTakeProfit
    OrderID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class CloseBuyStopOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseBuyStopOrder
    OrderID: int

@dataclass(slots=True)
class CloseSellStopOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseSellStopOrder
    OrderID: int

@dataclass(slots=True)
class OpenBuyLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenBuyLimitOrder
    Volume: float
    LimitPrice: float
    StopLoss: Union[float, None]
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.LimitPrice = cast(self.LimitPrice, float, None)
        self.StopLoss = cast(self.StopLoss, float, None)
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class OpenSellLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenSellLimitOrder
    Volume: float
    LimitPrice: float
    StopLoss: Union[float, None]
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.LimitPrice = cast(self.LimitPrice, float, None)
        self.StopLoss = cast(self.StopLoss, float, None)
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class ModifyBuyLimitOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderVolume
    OrderID: int
    Volume: float

@dataclass(slots=True)
class ModifySellLimitOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderVolume
    OrderID: int
    Volume: float

@dataclass(slots=True)
class ModifyBuyLimitOrderLimitPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderLimitPrice
    OrderID: int
    LimitPrice: float
    def __post_init__(self):
        self.LimitPrice = cast(self.LimitPrice, float, None)

@dataclass(slots=True)
class ModifySellLimitOrderLimitPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderLimitPrice
    OrderID: int
    LimitPrice: float
    def __post_init__(self):
        self.LimitPrice = cast(self.LimitPrice, float, None)

@dataclass(slots=True)
class ModifyBuyLimitOrderStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderStopLoss
    OrderID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)

@dataclass(slots=True)
class ModifySellLimitOrderStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderStopLoss
    OrderID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)

@dataclass(slots=True)
class ModifyBuyLimitOrderTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyLimitOrderTakeProfit
    OrderID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class ModifySellLimitOrderTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellLimitOrderTakeProfit
    OrderID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class CloseBuyLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseBuyLimitOrder
    OrderID: int

@dataclass(slots=True)
class CloseSellLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseSellLimitOrder
    OrderID: int

@dataclass(slots=True)
class OpenBuyStopLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenBuyStopLimitOrder
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

@dataclass(slots=True)
class OpenSellStopLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenSellStopLimitOrder
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

@dataclass(slots=True)
class ModifyBuyStopLimitOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderVolume
    OrderID: int
    Volume: float

@dataclass(slots=True)
class ModifySellStopLimitOrderVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderVolume
    OrderID: int
    Volume: float

@dataclass(slots=True)
class ModifyBuyStopLimitOrderStopPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderStopPrice
    OrderID: int
    StopPrice: float
    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)

@dataclass(slots=True)
class ModifySellStopLimitOrderStopPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderStopPrice
    OrderID: int
    StopPrice: float
    def __post_init__(self):
        self.StopPrice = cast(self.StopPrice, float, None)

@dataclass(slots=True)
class ModifyBuyStopLimitOrderLimitPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderLimitPrice
    OrderID: int
    LimitPrice: float
    def __post_init__(self):
        self.LimitPrice = cast(self.LimitPrice, float, None)

@dataclass(slots=True)
class ModifySellStopLimitOrderLimitPriceActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderLimitPrice
    OrderID: int
    LimitPrice: float
    def __post_init__(self):
        self.LimitPrice = cast(self.LimitPrice, float, None)

@dataclass(slots=True)
class ModifyBuyStopLimitOrderStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderStopLoss
    OrderID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)

@dataclass(slots=True)
class ModifySellStopLimitOrderStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderStopLoss
    OrderID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)

@dataclass(slots=True)
class ModifyBuyStopLimitOrderTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyStopLimitOrderTakeProfit
    OrderID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class ModifySellStopLimitOrderTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellStopLimitOrderTakeProfit
    OrderID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class CloseBuyStopLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseBuyStopLimitOrder
    OrderID: int

@dataclass(slots=True)
class CloseSellStopLimitOrderActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseSellStopLimitOrder
    OrderID: int

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