from __future__ import annotations

from typing import ClassVar
from dataclasses import dataclass

from Library.Market.Price import Direction
from Library.Protocol.Update.Update import UpdateAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Market.Bar import BarAPI

@dataclass(slots=True)
class OpenedBuyPositionUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class OpenedSellPositionUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class IncreasedBuyPositionVolumeUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class IncreasedSellPositionVolumeUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class DecreasedBuyPositionVolumeUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class DecreasedSellPositionVolumeUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class ModifiedBuyPositionStopLossUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class ModifiedSellPositionStopLossUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class ModifiedBuyPositionTakeProfitUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class ModifiedSellPositionTakeProfitUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class ClosedBuyPositionUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class ClosedSellPositionUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class StopLossBuyPositionUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class StopLossSellPositionUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class TakeProfitBuyPositionUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class TakeProfitSellPositionUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Sell
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class MarginCallBuyPositionUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Buy
    Bar: BarAPI
    Position: PositionAPI
    Trade: TradeAPI

@dataclass(slots=True)
class MarginCallSellPositionUpdateAPI(UpdateAPI):
    Direction: ClassVar[Direction] = Direction.Sell
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