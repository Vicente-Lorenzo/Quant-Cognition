from __future__ import annotations

import math
from typing import Union, TYPE_CHECKING
from dataclasses import dataclass, field

from Library.Database.Dataclass import DataclassAPI
from Library.Database.Enumeration import Enumeration

if TYPE_CHECKING:
    from Library.Universe.Contract import ContractAPI

class Direction(Enumeration):
    Buy = 1
    Neutral = 0
    Sell = -1

@dataclass(kw_only=True)
class PriceAPI(DataclassAPI):

    Price: float = field(init=True, repr=True)
    Reference: Union[float, None] = field(default=None, init=True, repr=True)
    Contract: Union[ContractAPI, None] = field(default=None, repr=False)

    @property
    def UID(self) -> float:
        return self.Price
    @UID.setter
    def UID(self, value) -> None:
        pass

    @property
    def LogPrice(self) -> Union[float, None]:
        if self.Price <= 0: return None
        return math.log(self.Price)
    @property
    def InvertedPrice(self) -> Union[float, None]:
        if not self.Price: return None
        return 1.0 / self.Price
    @property
    def Distance(self) -> Union[float, None]:
        if self.Reference is None: return None
        return self.Price - self.Reference
    @property
    def AbsoluteDistance(self) -> Union[float, None]:
        d = self.Distance
        return abs(d) if d is not None else None
    @property
    def Percentage(self) -> Union[float, None]:
        if not self.Reference: return None
        return (self.Price / self.Reference) - 1.0
    @property
    def LogPercentage(self) -> Union[float, None]:
        pct = self.Percentage
        if pct is None or pct <= -1.0: return None
        return math.log1p(pct)
    @property
    def AbsolutePercentage(self) -> Union[float, None]:
        pct = self.Percentage
        return abs(pct) if pct is not None else None
    @property
    def AbsoluteLogPercentage(self) -> Union[float, None]:
        lp = self.LogPercentage
        return abs(lp) if lp is not None else None
    @property
    def Direction(self) -> Union[Direction, None]:
        d = self.Distance
        if d is None: return None
        return Direction.Buy if d > 0 else Direction.Sell if d < 0 else Direction.Neutral
    @property
    def Ratio(self) -> Union[float, None]:
        if not self.Reference: return None
        return self.Price / self.Reference
    @property
    def Pips(self) -> Union[float, None]:
        if self.Contract is None or not self.Contract.PipSize: return None
        return self.Price / self.Contract.PipSize
    @property
    def Points(self) -> Union[float, None]:
        if self.Contract is None or not self.Contract.PointSize: return None
        return self.Price / self.Contract.PointSize