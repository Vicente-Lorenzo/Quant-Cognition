from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType
from Library.Indicator.Indicator import IndicatorMode
from Library.Market.Series import SeriesAPI
from Library.Indicator.Technical.Baseline.MA import MovingAverageType, MovingAverageAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class DoubleMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline

    def __init__(self, name: str, window: int, type: MovingAverageType, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.TypeMA = type
        self.Result = SeriesAPI(self.Name)
        self._data_ = None

    def init_data(self, market: MarketAPI) -> None:
        self._data_ = self.calculate(market, batch=True)
        return self.Result.init_data(self._data_)

    def update_data(self, market: MarketAPI) -> None:
        if self._data_ is None: return self.init_data(market)
        df = self.calculate(market, batch=False)
        self._data_ = self._data_.vstack(df)
        return self.Result.init_data(self._data_)

    def update_offset(self, offset: int = 1) -> None:
        self.Result.update_offset(offset)

    def _pad_(self) -> pl.DataFrame:
        return pl.DataFrame({self.Name: pl.Series([None], dtype=pl.Float64)})

    def calculate(self, market: MarketAPI, batch: bool = False) -> pl.DataFrame:
        if batch: return self.batch(market)
        return self.stream(market)

    def batch(self, market: MarketAPI) -> pl.DataFrame:
        series = market.CloseTicks.Bid.tail(dataframe=True)
        if series.is_empty(): return self._pad_()
        ma1 = MovingAverageAPI._batch_(series, self.Window, self.TypeMA)
        s_valid = ma1.drop_nulls()
        if s_valid.is_empty(): return self._pad_()
        ma2_valid = MovingAverageAPI._batch_(s_valid, self.Window, self.TypeMA)
        nulls = [None] * (len(series) - len(ma2_valid))
        ma2 = pl.Series(nulls + ma2_valid.to_list())
        dma = 2 * ma1 - ma2
        return pl.DataFrame({self.Name: dma})

    def stream(self, market: MarketAPI) -> pl.DataFrame:
        required_bars = self.Window * 5
        series = market.CloseTicks.Bid.tail(required_bars, dataframe=True)
        if len(series) < self.Window * 2: return self._pad_()
        ma1 = MovingAverageAPI._batch_(series, self.Window, self.TypeMA)
        s_valid = ma1.drop_nulls()
        ma2_valid = MovingAverageAPI._batch_(s_valid, self.Window, self.TypeMA)
        nulls = [None] * (len(series) - len(ma2_valid))
        ma2 = pl.Series(nulls + ma2_valid.to_list())
        dma = 2 * ma1 - ma2
        return pl.DataFrame({self.Name: pl.Series([dma.to_list()[-1]], dtype=pl.Float64)})