from __future__ import annotations

import math
from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType
from Library.Indicator.Indicator import IndicatorMode
from Library.Market.Series import SeriesAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class TriangularMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline

    def __init__(self, name: str, window: int, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.Result = SeriesAPI(self.Name)
        self._data_ = None

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        if series.is_empty(): return pl.Series([None] * len(series), dtype=pl.Float64)
        w1 = math.ceil(window / 2.0)
        w2 = math.ceil((window + 1) / 2.0)
        sma1 = series.rolling_mean(window_size=w1)
        nulls1 = [None] * (w1 - 1)
        if len(sma1) > w1 - 1: sma1 = pl.Series(nulls1 + sma1.to_list()[w1 - 1:])
        else: sma1 = pl.Series([None] * len(sma1))
        trima = sma1.rolling_mean(window_size=w2)
        nulls2 = [None] * (w1 - 1 + w2 - 1)
        if len(trima) > w1 - 1 + w2 - 1: return pl.Series(nulls2 + trima.to_list()[w1 - 1 + w2 - 1:])
        return pl.Series([None] * len(trima))

    def _extract_(self, market: MarketAPI) -> pl.Series:
        return market.CloseTicks.Price.tail()

    def init_data(self, market: MarketAPI) -> None:
        self._data_ = self.calculate(self._extract_(market), batch=True)
        return self.Result.init_data(self._data_)

    def update_data(self, market: MarketAPI) -> None:
        if self._data_ is None: return self.init_data(market)
        df = self.calculate(self._extract_(market), batch=False)
        self._data_ = self._data_.vstack(df)
        return self.Result.init_data(self._data_)

    def update_offset(self, offset: int = 1) -> None:
        self.Result.update_offset(offset)

    def _pad_(self) -> pl.DataFrame:
        return pl.DataFrame({self.Name: pl.Series([None], dtype=pl.Float64)})

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        series = data
        if series.is_empty(): return self._pad_()
        ma = self._batch_(series, self.Window)
        return pl.DataFrame({self.Name: ma})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        required_len = self.Window * 3
        series = data.tail(required_len)
        if len(series) < self.Window: return self._pad_()
        ma = self._batch_(series, self.Window)
        return pl.DataFrame({self.Name: pl.Series([ma.to_list()[-1]], dtype=pl.Float64)})

    def calculate(self, data: Union[pl.Series, pl.DataFrame], batch: bool = False) -> pl.DataFrame:
        if batch: return self.batch(data)
        return self.stream(data)