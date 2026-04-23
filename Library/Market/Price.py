from __future__ import annotations

import math
from enum import Enum
from typing import TYPE_CHECKING
from dataclasses import dataclass, field

from Library.Database.Dataclass import DataclassAPI

if TYPE_CHECKING: from Library.Universe.Contract import ContractAPI

class TradeType(Enum):
    Buy = 1
    Neutral = 0
    Sell = -1

@dataclass(kw_only=True)
class PriceAPI(DataclassAPI):

    Price: float = field(init=True, repr=True)
    Reference: float | None = field(default=None, init=True, repr=True)
    Contract: ContractAPI | None = field(default=None, repr=False)

    @property
    def UID(self) -> float:
        return self.Price
    @UID.setter
    def UID(self, value) -> None:
        pass

    @property
    def LogPrice(self) -> float | None:
        if self.Price <= 0: return None
        return math.log(self.Price)
    @property
    def InvertedPrice(self) -> float | None:
        if not self.Price: return None
        return 1.0 / self.Price
    @property
    def Distance(self) -> float | None:
        if self.Reference is None: return None
        return self.Price - self.Reference
    @property
    def AbsoluteDistance(self) -> float | None:
        d = self.Distance
        return abs(d) if d is not None else None
    @property
    def Percentage(self) -> float | None:
        if not self.Reference: return None
        return (self.Price / self.Reference) - 1.0
    @property
    def LogPercentage(self) -> float | None:
        pct = self.Percentage
        if pct is None or pct <= -1.0: return None
        return math.log1p(pct)
    @property
    def AbsolutePercentage(self) -> float | None:
        pct = self.Percentage
        return abs(pct) if pct is not None else None
    @property
    def AbsoluteLogPercentage(self) -> float | None:
        lp = self.LogPercentage
        return abs(lp) if lp is not None else None
    @property
    def Direction(self) -> TradeType | None:
        d = self.Distance
        if d is None: return None
        return TradeType.Buy if d > 0 else TradeType.Sell if d < 0 else TradeType.Neutral
    @property
    def Ratio(self) -> float | None:
        if not self.Reference: return None
        return self.Price / self.Reference
    @property
    def Pips(self) -> float | None:
        if self.Contract is None or not self.Contract.PipSize: return None
        return self.Price / self.Contract.PipSize
    @property
    def Points(self) -> float | None:
        if self.Contract is None or not self.Contract.PointSize: return None
        return self.Price / self.Contract.PointSize