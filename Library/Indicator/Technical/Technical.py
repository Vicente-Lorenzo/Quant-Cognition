from __future__ import annotations

from typing import Union, TYPE_CHECKING, ClassVar

from Library.Utility.Enumeration import EnumerationAPI
from Library.Indicator.Indicator import IndicatorMode

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI
    from Library.Database.Dataframe import pl

class TechnicalType(EnumerationAPI):
    Baseline = 0
    Overlap = 1
    Momentum = 2
    Volume = 3
    Volatility = 4
    Pattern = 5
    Other = 6

class TechnicalAPI:

    Type: ClassVar[TechnicalType] = TechnicalType.Other

    def __init__(self, name: str, window: Union[int, None], mode: IndicatorMode, **indicators) -> None:
        self.Name: str = name
        self.Window: Union[int, None] = window
        self.Mode: IndicatorMode = mode
        self._indicators_ = list(indicators.values())
        for k, v in indicators.items():
            setattr(self, k, v)

    def _extract_(self, market: MarketAPI) -> pl.Series:
        return market.Volume.Price.tail()

    def init_data(self, market: MarketAPI) -> None:
        for ind in self._indicators_:
            if hasattr(ind, "init_data"): ind.init_data(market)

    def update_data(self, market: MarketAPI) -> None:
        for ind in self._indicators_:
            if hasattr(ind, "update_data"): ind.update_data(market)

    def update_offset(self, offset: int = 1) -> None:
        for ind in self._indicators_:
            if hasattr(ind, "update_offset"): ind.update_offset(offset)

    def _pad_(self) -> pl.DataFrame:
        from Library.Database.Dataframe import pl
        return pl.DataFrame()