from __future__ import annotations

import math
import numpy as np
from typing import TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType
from Library.Indicator.Indicator import IndicatorMode
from Library.Market.Series import SeriesAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class HullMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline

    def __init__(self, name: str, window: int, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.Result = SeriesAPI(self.Name)
        self._data_ = None

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        half_w = math.floor(window / 2)
        sqrt_w = math.floor(math.sqrt(window))
        if len(series) < window + sqrt_w: return pl.Series([None] * len(series), dtype=pl.Float64)
        s_np = series.to_numpy()
        def apply_wma(data: np.ndarray, w: int) -> np.ndarray:
            weights = np.arange(1, w + 1)
            w_sum = weights.sum()
            res = np.full_like(data, fill_value=np.nan, dtype=float)
            for i in range(w - 1, len(data)):
                res[i] = np.dot(data[i - w + 1 : i + 1], weights) / w_sum
            return res
        wma_f = apply_wma(s_np, window)
        wma_h = apply_wma(s_np, half_w)
        diff = 2 * wma_h - wma_f
        hma = apply_wma(diff, sqrt_w)
        return pl.Series(hma)

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
        ma = self._batch_(series, self.Window)
        return pl.DataFrame({self.Name: ma})

    def stream(self, market: MarketAPI) -> pl.DataFrame:
        required_len = self.Window * 3
        series = market.CloseTicks.Bid.tail(required_len, dataframe=True)
        if len(series) < self.Window: return self._pad_()
        ma = self._batch_(series, self.Window)
        return pl.DataFrame({self.Name: pl.Series([ma.to_list()[-1]], dtype=pl.Float64)})