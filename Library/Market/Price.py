from __future__ import annotations

import math
from typing import TYPE_CHECKING
from dataclasses import dataclass, field

from Library.Database.Dataclass import DataclassAPI
if TYPE_CHECKING:
    from Library.Universe.Contract import ContractAPI

@dataclass(slots=True, kw_only=True)
class PriceAPI(DataclassAPI):

    Price: float = field(init=True, repr=True)
    Reference: float | None = field(default=None, init=True, repr=True)
    Contract: ContractAPI | None = field(default=None, init=True, repr=True)

    @property
    def UID(self) -> float:
        return self.Price

    @property
    def Distance(self) -> float | None:
        if self.Reference is None: return None
        return self.Price - self.Reference
    @property
    def Points(self) -> float | None:
        distance = self.Distance
        if distance is None or not self.Contract or not self.Contract.PointSize: return None
        return distance / self.Contract.PointSize
    @property
    def Pips(self) -> float | None:
        distance = self.Distance
        if distance is None or not self.Contract or not self.Contract.PipSize: return None
        return distance / self.Contract.PipSize
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
    def LogPrice(self) -> float | None:
        if self.Price <= 0: return None
        return math.log(self.Price)