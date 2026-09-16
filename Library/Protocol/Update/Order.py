from typing import ClassVar
from dataclasses import dataclass

from Library.Market.Price import Direction
from Library.Protocol.Update.Update import UpdateAPI
from Library.Portfolio.Order import OrderAPI
from Library.Market.Bar import BarAPI

@dataclass(slots=True)
class _OrderUpdateAPI_(UpdateAPI):

    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class OpenedBuyStopOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class OpenedSellStopOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyStopOrderVolumeUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellStopOrderVolumeUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyStopOrderStopPriceUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellStopOrderStopPriceUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyStopOrderStopLossUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellStopOrderStopLossUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyStopOrderTakeProfitUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellStopOrderTakeProfitUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ClosedBuyStopOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ClosedSellStopOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class FilledBuyStopOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class FilledSellStopOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ExpiredBuyStopOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ExpiredSellStopOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class OpenedBuyLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class OpenedSellLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyLimitOrderVolumeUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellLimitOrderVolumeUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyLimitOrderLimitPriceUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellLimitOrderLimitPriceUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyLimitOrderStopLossUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellLimitOrderStopLossUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyLimitOrderTakeProfitUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellLimitOrderTakeProfitUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ClosedBuyLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ClosedSellLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class FilledBuyLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class FilledSellLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ExpiredBuyLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ExpiredSellLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class OpenedBuyStopLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class OpenedSellStopLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderVolumeUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellStopLimitOrderVolumeUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderStopPriceUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellStopLimitOrderStopPriceUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderLimitPriceUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellStopLimitOrderLimitPriceUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderStopLossUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellStopLimitOrderStopLossUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderTakeProfitUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellStopLimitOrderTakeProfitUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ClosedBuyStopLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ClosedSellStopLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class FilledBuyStopLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class FilledSellStopLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ExpiredBuyStopLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ExpiredSellStopLimitOrderUpdateAPI(_OrderUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

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