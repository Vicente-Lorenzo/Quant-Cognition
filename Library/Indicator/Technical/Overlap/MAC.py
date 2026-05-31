from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Indicator.Indicator import IndicatorMode
from Library.Indicator.Technical.Baseline.MA import MovingAverageAPI, MovingAverageType
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class MovingAverageCrossAPI(TechnicalAPI):

    Type = TechnicalType.Overlap

    def __init__(self, name: str, fast_window: int, slow_window: int, type: MovingAverageType, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=slow_window, mode=mode)
        self.TypeMA: MovingAverageType = type
        self.Fast: MovingAverageAPI = MovingAverageAPI(name=f"{name}.Fast", window=fast_window, type=type, mode=IndicatorMode.Off)
        self.Slow: MovingAverageAPI = MovingAverageAPI(name=f"{name}.Slow", window=slow_window, type=type, mode=IndicatorMode.Off)
        self._indicators_ = [self.Fast, self.Slow]
        self.Window = self._window_()

    def filter_buy(self, market: MarketAPI) -> bool:
        return bool(self.Fast.Result.over(self.Slow.Result))

    def filter_sell(self, market: MarketAPI) -> bool:
        return bool(self.Fast.Result.under(self.Slow.Result))

    def signal_buy(self, market: MarketAPI) -> bool:
        return bool(self.Fast.Result.crossover(self.Slow.Result))

    def signal_sell(self, market: MarketAPI) -> bool:
        return bool(self.Fast.Result.crossunder(self.Slow.Result))