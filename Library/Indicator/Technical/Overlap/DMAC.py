from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType
from Library.Indicator.Indicator import IndicatorMode
from Library.Indicator.Technical.Baseline.DMA import DoubleMovingAverageAPI
from Library.Indicator.Technical.Baseline.MA import MovingAverageType

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class DoubleMovingAverageCrossAPI(TechnicalAPI):

    Type = TechnicalType.Overlap

    def __init__(self, name: str, fast_window: int, slow_window: int, type: MovingAverageType, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=slow_window, mode=mode)
        self.TypeMA = type
        self.Fast = DoubleMovingAverageAPI(name=f"{name}.Fast", window=fast_window, type=type, mode=IndicatorMode.Off)
        self.Slow = DoubleMovingAverageAPI(name=f"{name}.Slow", window=slow_window, type=type, mode=IndicatorMode.Off)
        self._indicators_ = [self.Fast, self.Slow]

    def filter_buy(self, market: MarketAPI) -> bool:
        return self.Fast.Result.over(self.Slow.Result)

    def filter_sell(self, market: MarketAPI) -> bool:
        return self.Fast.Result.under(self.Slow.Result)

    def signal_buy(self, market: MarketAPI) -> bool:
        return self.Fast.Result.crossover(self.Slow.Result)

    def signal_sell(self, market: MarketAPI) -> bool:
        return self.Fast.Result.crossunder(self.Slow.Result)