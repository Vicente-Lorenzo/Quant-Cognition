from __future__ import annotations

from dataclasses import dataclass

from Library.Protocol.Update.Update import UpdateAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Market.Bar import BarAPI

@dataclass(slots=True)
class OpenedBuyPositionUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class OpenedSellPositionUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class IncreasedBuyPositionVolumeUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class IncreasedSellPositionVolumeUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class DecreasedBuyPositionVolumeUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class DecreasedSellPositionVolumeUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class ModifiedBuyPositionStopLossUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class ModifiedSellPositionStopLossUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class ModifiedBuyPositionTakeProfitUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class ModifiedSellPositionTakeProfitUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class ClosedBuyPositionUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class ClosedSellPositionUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class StopLossBuyPositionUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class StopLossSellPositionUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class TakeProfitBuyPositionUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class TakeProfitSellPositionUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class MarginCallBuyPositionUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class MarginCallSellPositionUpdateAPI(UpdateAPI):
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

__all__ = [
    "OpenedBuyPositionUpdateAPI",
    "OpenedSellPositionUpdateAPI",
    "IncreasedBuyPositionVolumeUpdateAPI",
    "IncreasedSellPositionVolumeUpdateAPI",
    "DecreasedBuyPositionVolumeUpdateAPI",
    "DecreasedSellPositionVolumeUpdateAPI",
    "ModifiedBuyPositionStopLossUpdateAPI",
    "ModifiedSellPositionStopLossUpdateAPI",
    "ModifiedBuyPositionTakeProfitUpdateAPI",
    "ModifiedSellPositionTakeProfitUpdateAPI",
    "ClosedBuyPositionUpdateAPI",
    "ClosedSellPositionUpdateAPI",
    "StopLossBuyPositionUpdateAPI",
    "StopLossSellPositionUpdateAPI",
    "TakeProfitBuyPositionUpdateAPI",
    "TakeProfitSellPositionUpdateAPI",
    "MarginCallBuyPositionUpdateAPI",
    "MarginCallSellPositionUpdateAPI"
]