from __future__ import annotations

import math
from dataclasses import dataclass, field

from Library.Database.Dataclass import DataclassAPI
from Library.Market.Price import Direction

@dataclass(slots=True, kw_only=True)
class PnLAPI(DataclassAPI):

    PnL: float = field(init=True, repr=True)
    Reference: float | None = field(default=None, init=True, repr=True)

    @property
    def UID(self) -> float:
        return self.PnL

    @property
    def Absolute(self) -> float:
        return abs(self.PnL)
    @property
    def Direction(self) -> Direction:
        return Direction.Buy if self.PnL > 0 else Direction.Sell if self.PnL < 0 else Direction.Neutral
    @property
    def Return(self) -> float | None:
        if not self.Reference: return None
        return self.PnL / self.Reference
    @property
    def AbsoluteReturn(self) -> float | None:
        ret = self.Return
        return abs(ret) if ret is not None else None
    @property
    def Percentage(self) -> float | None:
        ret = self.Return
        return ret * 100.0 if ret is not None else None
    @property
    def LogReturn(self) -> float | None:
        ret = self.Return
        if ret is None or ret <= -1.0: return None
        return math.log1p(ret)
    @property
    def AbsoluteLogReturn(self) -> float | None:
        lr = self.LogReturn
        return abs(lr) if lr is not None else None