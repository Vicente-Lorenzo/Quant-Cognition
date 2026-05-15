from __future__ import annotations

from typing import Union, ClassVar
from dataclasses import dataclass

from Library.Protocol.Action.Action import ActionAPI, ActionID
from Library.Portfolio.Position import PositionType
from Library.Utility.Typing import cast

@dataclass(slots=True)
class OpenBuyPositionActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenBuyPosition
    PositionType: PositionType
    Volume: float
    StopLoss: Union[float, None]
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.PositionType = PositionType(self.PositionType)
        self.StopLoss = cast(self.StopLoss, float, None)
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class OpenSellPositionActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.OpenSellPosition
    PositionType: PositionType
    Volume: float
    StopLoss: Union[float, None]
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.PositionType = PositionType(self.PositionType)
        self.StopLoss = cast(self.StopLoss, float, None)
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class ModifyBuyPositionVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyPositionVolume
    PositionID: int
    Volume: float

@dataclass(slots=True)
class ModifySellPositionVolumeActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellPositionVolume
    PositionID: int
    Volume: float

@dataclass(slots=True)
class ModifyBuyPositionStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyPositionStopLoss
    PositionID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)

@dataclass(slots=True)
class ModifySellPositionStopLossActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellPositionStopLoss
    PositionID: int
    StopLoss: Union[float, None]
    def __post_init__(self):
        self.StopLoss = cast(self.StopLoss, float, None)

@dataclass(slots=True)
class ModifyBuyPositionTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifyBuyPositionTakeProfit
    PositionID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class ModifySellPositionTakeProfitActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.ModifySellPositionTakeProfit
    PositionID: int
    TakeProfit: Union[float, None]
    def __post_init__(self):
        self.TakeProfit = cast(self.TakeProfit, float, None)

@dataclass(slots=True)
class CloseBuyPositionActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseBuyPosition
    PositionID: int

@dataclass(slots=True)
class CloseSellPositionActionAPI(ActionAPI):
    ActionID: ClassVar[ActionID] = ActionID.CloseSellPosition
    PositionID: int

__all__ = [
    "OpenBuyPositionActionAPI",
    "OpenSellPositionActionAPI",
    "ModifyBuyPositionVolumeActionAPI",
    "ModifySellPositionVolumeActionAPI",
    "ModifyBuyPositionStopLossActionAPI",
    "ModifySellPositionStopLossActionAPI",
    "ModifyBuyPositionTakeProfitActionAPI",
    "ModifySellPositionTakeProfitActionAPI",
    "CloseBuyPositionActionAPI",
    "CloseSellPositionActionAPI"
]