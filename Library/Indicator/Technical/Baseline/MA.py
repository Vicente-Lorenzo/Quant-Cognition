from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Indicator.Indicator import IndicatorMode
from Library.Indicator.Technical.Baseline.EMA import ExponentialMovingAverageAPI
from Library.Indicator.Technical.Baseline.HMA import HullMovingAverageAPI
from Library.Indicator.Technical.Baseline.KAMA import KaufmanAdaptiveMovingAverageAPI
from Library.Indicator.Technical.Baseline.SMA import SimpleMovingAverageAPI
from Library.Indicator.Technical.Baseline.TRIMA import TriangularMovingAverageAPI
from Library.Indicator.Technical.Baseline.WMA import WeightedMovingAverageAPI
from Library.Indicator.Technical.Technical import MODE, PriceSignalAPI, SlotAPI, TechnicalAPI, TechnicalType, WINDOW
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

class MovingAverageAPI(PriceSignalAPI):

    Type = TechnicalType.Baseline
    Parameters = (WINDOW, MOVING, MODE)
    _AVERAGES_ = {
        MovingAverageType.Simple: SimpleMovingAverageAPI,
        MovingAverageType.Exponential: ExponentialMovingAverageAPI,
        MovingAverageType.Weighted: WeightedMovingAverageAPI,
        MovingAverageType.Hull: HullMovingAverageAPI,
        MovingAverageType.Triangular: TriangularMovingAverageAPI,
        MovingAverageType.Kaufman: KaufmanAdaptiveMovingAverageAPI
    }

    def __init__(self, name: str, window: int, type: MovingAverageType, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.TypeMA: MovingAverageType = type
        self.MA: TechnicalAPI = self._resolve_(type)(name=name, window=window, mode=IndicatorMode.Off)
        self.Result = self.MA.Result

    @staticmethod
    def _resolve_(type: MovingAverageType) -> type:
        return MovingAverageAPI._AVERAGES_[type]

    @staticmethod
    def _batch_(series: pl.Series, window: int, type: MovingAverageType) -> pl.Series:
        return MovingAverageAPI._resolve_(type)._batch_(series, window)

    @staticmethod
    def _nest_(valid: pl.Series, window: int, type: MovingAverageType, length: int) -> pl.Series:
        nested = MovingAverageAPI._batch_(valid, window, type)
        return pl.Series([None] * (length - len(nested)) + nested.to_list())

    def init_data(self, market: MarketAPI) -> None:
        self.MA.init_data(market)

    def update_data(self, market: MarketAPI) -> None:
        self.MA.update_data(market)

    def update_offset(self, offset: int = 1) -> None:
        self.MA.update_offset(offset)