from __future__ import annotations

from typing import Union, TYPE_CHECKING
from dataclasses import dataclass, field

from Library.Database.Dataclass import DataclassAPI
from Library.Utility.Enumeration import EnumerationAPI

if TYPE_CHECKING:
    from Library.Universe.Contract import ContractAPI

class Direction(EnumerationAPI):
    Buy = 1
    Neutral = 0
    Sell = -1

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
        pass

    @property
    def LogPrice(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_log_value
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
        from Library.Portfolio.Statistic import calculate_price_return
        return calculate_price_return(self.Price, self.Reference)
    @property
    def LogReturn(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_log_return
        return calculate_log_return(self.Return)
    @property
    def Percentage(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_percentage
        return calculate_percentage(self.Return)
    @property
    def LogPercentage(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_log_percentage
        return calculate_log_percentage(self.LogReturn)
    @property
    def Direction(self) -> Union[Direction, None]:
        from Library.Portfolio.Statistic import calculate_direction
        d = self.Distance
        if d is None: return None
        return calculate_direction(d)
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