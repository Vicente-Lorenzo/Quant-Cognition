from typing import ClassVar
from dataclasses import dataclass

from Library.Market.Price import Direction
from Library.Protocol.Update.Update import UpdateAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Market.Bar import BarAPI

@dataclass(slots=True)
class _PositionUpdateAPI_(UpdateAPI):

    Bar: BarAPI
    Position: PositionAPI

@dataclass(slots=True)
class _TradeUpdateAPI_(_PositionUpdateAPI_):

    Trade: TradeAPI

@dataclass(slots=True)
class OpenedBuyPositionUpdateAPI(_PositionUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class OpenedSellPositionUpdateAPI(_PositionUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class IncreasedBuyPositionVolumeUpdateAPI(_PositionUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class IncreasedSellPositionVolumeUpdateAPI(_PositionUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class DecreasedBuyPositionVolumeUpdateAPI(_TradeUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class DecreasedSellPositionVolumeUpdateAPI(_TradeUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyPositionStopLossUpdateAPI(_PositionUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellPositionStopLossUpdateAPI(_PositionUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ModifiedBuyPositionTakeProfitUpdateAPI(_PositionUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ModifiedSellPositionTakeProfitUpdateAPI(_PositionUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class ClosedBuyPositionUpdateAPI(_TradeUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class ClosedSellPositionUpdateAPI(_TradeUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class StopLossBuyPositionUpdateAPI(_TradeUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class StopLossSellPositionUpdateAPI(_TradeUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class TakeProfitBuyPositionUpdateAPI(_TradeUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class TakeProfitSellPositionUpdateAPI(_TradeUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

@dataclass(slots=True)
class MarginCallBuyPositionUpdateAPI(_TradeUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Buy

@dataclass(slots=True)
class MarginCallSellPositionUpdateAPI(_TradeUpdateAPI_):

    Direction: ClassVar[Direction] = Direction.Sell

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