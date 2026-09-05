from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Indicator.Indicator import IndicatorMode
from Library.Indicator.Technical.Technical import MODE, SlotAPI, TechnicalAPI, TechnicalType, WINDOW
from Library.Utility.Enumeration import EnumerationAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class MovingAverageType(EnumerationAPI):

    Simple = 0
    Exponential = 1
    Weighted = 2
    Hull = 3
    Triangular = 4
    Kaufman = 5

MOVING = SlotAPI(name="type", default=MovingAverageType.Exponential, parser=MovingAverageType.parse)

class MovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline
    Parameters = (WINDOW, MOVING, MODE)

    def __init__(self, name: str, window: int, type: MovingAverageType, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.TypeMA: MovingAverageType = type
        match self.TypeMA:
            case MovingAverageType.Simple:
                from Library.Indicator.Technical.Baseline.SMA import SimpleMovingAverageAPI
                self.MA: TechnicalAPI = SimpleMovingAverageAPI(name=name, window=window, mode=IndicatorMode.Off)
            case MovingAverageType.Exponential:
                from Library.Indicator.Technical.Baseline.EMA import ExponentialMovingAverageAPI
                self.MA = ExponentialMovingAverageAPI(name=name, window=window, mode=IndicatorMode.Off)
            case MovingAverageType.Weighted:
                from Library.Indicator.Technical.Baseline.WMA import WeightedMovingAverageAPI
                self.MA = WeightedMovingAverageAPI(name=name, window=window, mode=IndicatorMode.Off)
            case MovingAverageType.Hull:
                from Library.Indicator.Technical.Baseline.HMA import HullMovingAverageAPI
                self.MA = HullMovingAverageAPI(name=name, window=window, mode=IndicatorMode.Off)
            case MovingAverageType.Triangular:
                from Library.Indicator.Technical.Baseline.TRIMA import TriangularMovingAverageAPI
                self.MA = TriangularMovingAverageAPI(name=name, window=window, mode=IndicatorMode.Off)
            case MovingAverageType.Kaufman:
                from Library.Indicator.Technical.Baseline.KAMA import KaufmanAdaptiveMovingAverageAPI
                self.MA = KaufmanAdaptiveMovingAverageAPI(name=name, window=window, mode=IndicatorMode.Off)
        self.Result = self.MA.Result

    @staticmethod
    def _batch_(series: pl.Series, window: int, type: MovingAverageType) -> pl.Series:
        match type:
            case MovingAverageType.Simple:
                from Library.Indicator.Technical.Baseline.SMA import SimpleMovingAverageAPI
                return SimpleMovingAverageAPI._batch_(series, window)
            case MovingAverageType.Exponential:
                from Library.Indicator.Technical.Baseline.EMA import ExponentialMovingAverageAPI
                return ExponentialMovingAverageAPI._batch_(series, window)
            case MovingAverageType.Weighted:
                from Library.Indicator.Technical.Baseline.WMA import WeightedMovingAverageAPI
                return WeightedMovingAverageAPI._batch_(series, window)
            case MovingAverageType.Hull:
                from Library.Indicator.Technical.Baseline.HMA import HullMovingAverageAPI
                return HullMovingAverageAPI._batch_(series, window)
            case MovingAverageType.Triangular:
                from Library.Indicator.Technical.Baseline.TRIMA import TriangularMovingAverageAPI
                return TriangularMovingAverageAPI._batch_(series, window)
            case MovingAverageType.Kaufman:
                from Library.Indicator.Technical.Baseline.KAMA import KaufmanAdaptiveMovingAverageAPI
                return KaufmanAdaptiveMovingAverageAPI._batch_(series, window)

    def init_data(self, market: MarketAPI) -> None:
        self.MA.init_data(market)

    def update_data(self, market: MarketAPI) -> None:
        self.MA.update_data(market)

    def update_offset(self, offset: int = 1) -> None:
        self.MA.update_offset(offset)

    def filter_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.over(self.Result))

    def filter_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.under(self.Result))

    def signal_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossover(self.Result))

    def signal_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossunder(self.Result))