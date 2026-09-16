from __future__ import annotations

from typing import Union, TYPE_CHECKING
from dataclasses import dataclass, field

from Library.Utility.Typing import MISSING
from Library.Database.Dataclass import DataclassAPI
from Library.Utility.Enumeration import EnumerationAPI
from Library.Statistic.Metric import (
    calculate_log_percentage,
    calculate_log_return,
    calculate_log_value,
    calculate_percentage,
    calculate_price_return
)

if TYPE_CHECKING:
    from Library.Universe.Contract import ContractAPI

class Direction(EnumerationAPI):

    Buy = 1
    Neutral = 0
    Sell = -1

    @classmethod
    def calculate(cls, value: float) -> Direction:
        return cls.Buy if value > 0 else cls.Sell if value < 0 else cls.Neutral

class PriceMode(EnumerationAPI):

    Ask = 0
    Mid = 1
    Bid = 2

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
        if value is not MISSING: self.Price = value

    @classmethod
    def unwrap(cls, value: Union[float, PriceAPI, None]) -> Union[float, None]:
        if isinstance(value, cls): return value.Price
        return value if value is not MISSING else None

    @classmethod
    def make(cls, value: Union[float, PriceAPI, None], reference: Union[float, None] = None, contract: Union[ContractAPI, None] = None) -> Union[PriceAPI, None]:
        if isinstance(value, cls):
            if value.Contract is None: value.Contract = contract
            if value.Reference is None: value.Reference = reference
            return value
        if value is MISSING or value is None: return None
        return cls(Price=value, Reference=reference, Contract=contract)

    @classmethod
    def assign(cls, backing: Union[PriceAPI, None], value: Union[float, PriceAPI, None], reference: Union[float, None] = None, contract: Union[ContractAPI, None] = None) -> Union[PriceAPI, None]:
        if isinstance(value, cls): return value
        if value is MISSING or value is None: return backing
        if backing:
            backing.Price = value
            return backing
        return cls(Price=value, Reference=reference, Contract=contract)

    @property
    def LogPrice(self) -> Union[float, None]:
        return calculate_log_value(self.Price)

    @property
    def InvertedPrice(self) -> Union[float, None]:
        if not self.Price: return None
        return 1.0 / self.Price

    @property
    def Distance(self) -> Union[float, None]:
        if self.Reference is None: return None
        return self.Price - self.Reference

    @property
    def Return(self) -> Union[float, None]:
        return calculate_price_return(self.Price, self.Reference)

    @property
    def LogReturn(self) -> Union[float, None]:
        return calculate_log_return(self.Return)

    @property
    def Percentage(self) -> Union[float, None]:
        return calculate_percentage(self.Return)

    @property
    def LogPercentage(self) -> Union[float, None]:
        return calculate_log_percentage(self.LogReturn)

    @property
    def Direction(self) -> Union[Direction, None]:
        d = self.Distance
        if d is None: return None
        return Direction.calculate(d)

    @property
    def Ratio(self) -> Union[float, None]:
        if not self.Reference: return None
        return self.Price / self.Reference

    @property
    def Points(self) -> Union[float, None]:
        if self.Contract is None or not self.Contract.PointSize: return None
        return self.Price / self.Contract.PointSize

    @property
    def Pips(self) -> Union[float, None]:
        if self.Contract is None or not self.Contract.PipSize: return None
        return self.Price / self.Contract.PipSize