from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Indicator.Indicator import IndicatorMode

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class SentimentalAPI:

    def __init__(self, name: str, window: int, mode: IndicatorMode, **indicators) -> None:
        self.Name: str = name
        self.Mode: IndicatorMode = mode
        self._indicators_: list = list(indicators.values())
        for k, v in indicators.items():
            setattr(self, k, v)
        self.Window: int = self._window_() or window

    def _window_(self) -> int:
        return max((ind.Window for ind in self._indicators_ if hasattr(ind, "Window")), default=0)

    def init_data(self, market: MarketAPI) -> None:
        for ind in self._indicators_:
            if hasattr(ind, "init_data"): ind.init_data(market)

    def update_data(self, market: MarketAPI) -> None:
        for ind in self._indicators_:
            if hasattr(ind, "update_data"): ind.update_data(market)

    def update_offset(self, offset: int = 1) -> None:
        for ind in self._indicators_:
            if hasattr(ind, "update_offset"): ind.update_offset(offset)