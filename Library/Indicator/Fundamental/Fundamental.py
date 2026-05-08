from __future__ import annotations

from typing import Union, TYPE_CHECKING
from Library.Indicator.Indicator import IndicatorMode

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class FundamentalAPI:

    def __init__(self, name: str, window: Union[int, None], mode: IndicatorMode, **indicators) -> None:
        self.Name: str = name
        self.Window: Union[int, None] = window
        self.Mode: IndicatorMode = mode
        self._indicators_ = list(indicators.values())
        for k, v in indicators.items():
            setattr(self, k, v)

    def init_data(self, market: MarketAPI) -> None:
        for ind in self._indicators_:
            if hasattr(ind, "init_data"): ind.init_data(market)

    def update_data(self, market: MarketAPI) -> None:
        for ind in self._indicators_:
            if hasattr(ind, "update_data"): ind.update_data(market)

    def update_offset(self, offset: int = 1) -> None:
        for ind in self._indicators_:
            if hasattr(ind, "update_offset"): ind.update_offset(offset)