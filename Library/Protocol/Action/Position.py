from __future__ import annotations

from typing import Union, ClassVar
from dataclasses import dataclass

from Library.Utility.Typing import cast
from Library.Protocol.Binary import BinaryAPI
from Library.Portfolio.Position import PositionType
from Library.Protocol.Action.Action import ActionAPI, ActionID

@dataclass(slots=True)
class OpenBuyPositionActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenBuyPosition
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 's', 'd', 'D', 'D')
    PositionType: PositionType
    Volume: float
    StopLoss: Union[float, None]
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.PositionType = PositionType(self.PositionType)
        self.StopLoss = cast(self.StopLoss, float, None)
        self.TakeProfit = cast(self.TakeProfit, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionType.name, self.Volume, self.StopLoss, self.TakeProfit)

@dataclass(slots=True)
class OpenSellPositionActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenSellPosition
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 's', 'd', 'D', 'D')
    PositionType: PositionType
    Volume: float
    StopLoss: Union[float, None]
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.PositionType = PositionType(self.PositionType)
        self.StopLoss = cast(self.StopLoss, float, None)
        self.TakeProfit = cast(self.TakeProfit, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionType.name, self.Volume, self.StopLoss, self.TakeProfit)

@dataclass(slots=True)
class IncreaseBuyPositionVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.IncreaseBuyPositionVolume
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    PositionID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionID, self.Volume)

@dataclass(slots=True)
class IncreaseSellPositionVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.IncreaseSellPositionVolume
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    PositionID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionID, self.Volume)

@dataclass(slots=True)
class DecreaseBuyPositionVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.DecreaseBuyPositionVolume
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    PositionID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionID, self.Volume)

@dataclass(slots=True)
class DecreaseSellPositionVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.DecreaseSellPositionVolume
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    PositionID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionID, self.Volume)

@dataclass(slots=True)
class ModifyBuyPositionVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyPositionVolume
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    PositionID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionID, self.Volume)

@dataclass(slots=True)
class ModifySellPositionVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellPositionVolume
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'd')
    PositionID: int
    Volume: float
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionID, self.Volume)

@dataclass(slots=True)
class ModifyBuyPositionStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyPositionStopLoss
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    PositionID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionID, self.StopLoss)

@dataclass(slots=True)
class ModifySellPositionStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellPositionStopLoss
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    PositionID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionID, self.StopLoss)

@dataclass(slots=True)
class ModifyBuyPositionTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyPositionTakeProfit
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    PositionID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionID, self.TakeProfit)

@dataclass(slots=True)
class ModifySellPositionTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellPositionTakeProfit
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i', 'D')
    PositionID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionID, self.TakeProfit)

@dataclass(slots=True)
class CloseBuyPositionActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseBuyPosition
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    PositionID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionID)

@dataclass(slots=True)
class CloseSellPositionActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseSellPosition
    _binary_: ClassVar[BinaryAPI] = BinaryAPI('B', 'i')
    PositionID: int
    def serialize(self) -> bytes:
        return self._binary_.pack(self.ActionID.value, self.PositionID)

__all__ = [
    "OpenBuyPositionActionAPI",
    "OpenSellPositionActionAPI",
    "IncreaseBuyPositionVolumeActionAPI",
    "IncreaseSellPositionVolumeActionAPI",
    "DecreaseBuyPositionVolumeActionAPI",
    "DecreaseSellPositionVolumeActionAPI",
    "ModifyBuyPositionVolumeActionAPI",
    "ModifySellPositionVolumeActionAPI",
    "ModifyBuyPositionStopLossActionAPI",
    "ModifySellPositionStopLossActionAPI",
    "ModifyBuyPositionTakeProfitActionAPI",
    "ModifySellPositionTakeProfitActionAPI",
    "CloseBuyPositionActionAPI",
    "CloseSellPositionActionAPI"
]