from typing import ClassVar
from dataclasses import dataclass

from Library.Market.Price import Direction
from Library.Protocol.Update.Update import UpdateAPI
from Library.Portfolio.Order import OrderAPI
from Library.Market.Bar import BarAPI

@dataclass(slots=True)
class OpenedBuyStopOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class OpenedSellStopOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopOrderVolumeUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopOrderVolumeUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopOrderStopPriceUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopOrderStopPriceUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopOrderStopLossUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopOrderStopLossUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopOrderTakeProfitUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopOrderTakeProfitUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ClosedBuyStopOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ClosedSellStopOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class FilledBuyStopOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class FilledSellStopOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ExpiredBuyStopOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ExpiredSellStopOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class OpenedBuyLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class OpenedSellLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyLimitOrderVolumeUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellLimitOrderVolumeUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyLimitOrderLimitPriceUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellLimitOrderLimitPriceUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyLimitOrderStopLossUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellLimitOrderStopLossUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyLimitOrderTakeProfitUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellLimitOrderTakeProfitUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ClosedBuyLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ClosedSellLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class FilledBuyLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class FilledSellLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ExpiredBuyLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ExpiredSellLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class OpenedBuyStopLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class OpenedSellStopLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderVolumeUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopLimitOrderVolumeUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderStopPriceUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopLimitOrderStopPriceUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderLimitPriceUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopLimitOrderLimitPriceUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderStopLossUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopLimitOrderStopLossUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderTakeProfitUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopLimitOrderTakeProfitUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ClosedBuyStopLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ClosedSellStopLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class FilledBuyStopLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class FilledSellStopLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ExpiredBuyStopLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ExpiredSellStopLimitOrderUpdateAPI(UpdateAPI):

    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Order: OrderAPI

__all__ = [
    "OpenedBuyStopOrderUpdateAPI",
    "OpenedSellStopOrderUpdateAPI",
    "ModifiedBuyStopOrderVolumeUpdateAPI",
    "ModifiedSellStopOrderVolumeUpdateAPI",
    "ModifiedBuyStopOrderStopPriceUpdateAPI",
    "ModifiedSellStopOrderStopPriceUpdateAPI",
    "ModifiedBuyStopOrderStopLossUpdateAPI",
    "ModifiedSellStopOrderStopLossUpdateAPI",
    "ModifiedBuyStopOrderTakeProfitUpdateAPI",
    "ModifiedSellStopOrderTakeProfitUpdateAPI",
    "ClosedBuyStopOrderUpdateAPI",
    "ClosedSellStopOrderUpdateAPI",
    "FilledBuyStopOrderUpdateAPI",
    "FilledSellStopOrderUpdateAPI",
    "ExpiredBuyStopOrderUpdateAPI",
    "ExpiredSellStopOrderUpdateAPI",
    "OpenedBuyLimitOrderUpdateAPI",
    "OpenedSellLimitOrderUpdateAPI",
    "ModifiedBuyLimitOrderVolumeUpdateAPI",
    "ModifiedSellLimitOrderVolumeUpdateAPI",
    "ModifiedBuyLimitOrderLimitPriceUpdateAPI",
    "ModifiedSellLimitOrderLimitPriceUpdateAPI",
    "ModifiedBuyLimitOrderStopLossUpdateAPI",
    "ModifiedSellLimitOrderStopLossUpdateAPI",
    "ModifiedBuyLimitOrderTakeProfitUpdateAPI",
    "ModifiedSellLimitOrderTakeProfitUpdateAPI",
    "ClosedBuyLimitOrderUpdateAPI",
    "ClosedSellLimitOrderUpdateAPI",
    "FilledBuyLimitOrderUpdateAPI",
    "FilledSellLimitOrderUpdateAPI",
    "ExpiredBuyLimitOrderUpdateAPI",
    "ExpiredSellLimitOrderUpdateAPI",
    "OpenedBuyStopLimitOrderUpdateAPI",
    "OpenedSellStopLimitOrderUpdateAPI",
    "ModifiedBuyStopLimitOrderVolumeUpdateAPI",
    "ModifiedSellStopLimitOrderVolumeUpdateAPI",
    "ModifiedBuyStopLimitOrderStopPriceUpdateAPI",
    "ModifiedSellStopLimitOrderStopPriceUpdateAPI",
    "ModifiedBuyStopLimitOrderLimitPriceUpdateAPI",
    "ModifiedSellStopLimitOrderLimitPriceUpdateAPI",
    "ModifiedBuyStopLimitOrderStopLossUpdateAPI",
    "ModifiedSellStopLimitOrderStopLossUpdateAPI",
    "ModifiedBuyStopLimitOrderTakeProfitUpdateAPI",
    "ModifiedSellStopLimitOrderTakeProfitUpdateAPI",
    "ClosedBuyStopLimitOrderUpdateAPI",
    "ClosedSellStopLimitOrderUpdateAPI",
    "FilledBuyStopLimitOrderUpdateAPI",
    "FilledSellStopLimitOrderUpdateAPI",
    "ExpiredBuyStopLimitOrderUpdateAPI",
    "ExpiredSellStopLimitOrderUpdateAPI"
]