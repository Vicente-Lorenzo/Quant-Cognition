from __future__ import annotations

from dataclasses import dataclass

from Library.Protocol.Update.Update import UpdateAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI
from Library.Market.Bar import BarAPI

@dataclass(slots=True)
class OpenedBuyStopOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class OpenedSellStopOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopOrderVolumeUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopOrderVolumeUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopOrderStopPriceUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopOrderStopPriceUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopOrderStopLossUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopOrderStopLossUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopOrderTakeProfitUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopOrderTakeProfitUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ClosedBuyStopOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ClosedSellStopOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class FilledBuyStopOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI
    Position: PositionAPI

@dataclass(slots=True)
class FilledSellStopOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI
    Position: PositionAPI

@dataclass(slots=True)
class ExpiredBuyStopOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ExpiredSellStopOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class OpenedBuyLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class OpenedSellLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyLimitOrderVolumeUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellLimitOrderVolumeUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyLimitOrderLimitPriceUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellLimitOrderLimitPriceUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyLimitOrderStopLossUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellLimitOrderStopLossUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyLimitOrderTakeProfitUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellLimitOrderTakeProfitUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ClosedBuyLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ClosedSellLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class FilledBuyLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI
    Position: PositionAPI

@dataclass(slots=True)
class FilledSellLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI
    Position: PositionAPI

@dataclass(slots=True)
class ExpiredBuyLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ExpiredSellLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class OpenedBuyStopLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class OpenedSellStopLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderVolumeUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopLimitOrderVolumeUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderStopPriceUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopLimitOrderStopPriceUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderLimitPriceUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopLimitOrderLimitPriceUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderStopLossUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopLimitOrderStopLossUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedBuyStopLimitOrderTakeProfitUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ModifiedSellStopLimitOrderTakeProfitUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ClosedBuyStopLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ClosedSellStopLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class FilledBuyStopLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI
    Position: PositionAPI

@dataclass(slots=True)
class FilledSellStopLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI
    Position: PositionAPI

@dataclass(slots=True)
class ExpiredBuyStopLimitOrderUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Order: OrderAPI

@dataclass(slots=True)
class ExpiredSellStopLimitOrderUpdateAPI(UpdateAPI):
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