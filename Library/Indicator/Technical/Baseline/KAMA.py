from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType
from Library.Indicator.Indicator import IndicatorMode
from Library.Market.Series import SeriesAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class KaufmanAdaptiveMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline

    def __init__(self, name: str, window: int, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.Result = SeriesAPI(self.Name)
        self._data_ = None

    @staticmethod
    def compute_batch(series: pl.Series, window: int) -> pl.Series:
        if len(series) <= window: return pl.Series([None] * len(series), dtype=pl.Float64)
        fast_alpha = 2 / (2 + 1)
        slow_alpha = 2 / (30 + 1)
        p = series.to_numpy()
        change = np.abs(p[window:] - p[:-window])
        diff = np.abs(p[1:] - p[:-1])
        volatility = np.convolve(diff, np.ones(window, dtype=int), 'valid')
        er = np.zeros_like(change)
        mask = volatility != 0
        er[mask] = change[mask] / volatility[mask]
        sc = (er * (fast_alpha - slow_alpha) + slow_alpha) ** 2
        kama = np.full_like(p, np.nan)
        kama[window - 1] = p[window - 1]
        for i in range(window, len(p)):
            kama[i] = kama[i-1] + sc[i - window] * (p[i] - kama[i-1])
        return pl.Series(kama)

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
        ma = self.compute_batch(series, self.Window)
        return pl.DataFrame({self.Name: ma})

    def stream(self, market: MarketAPI) -> pl.DataFrame:
        fast_alpha = 2 / (2 + 1)
        slow_alpha = 2 / (30 + 1)
        prev_kama = self.Result.last()
        new_price = market.CloseTicks.Bid.last()
        if prev_kama is None:
            prices = market.CloseTicks.Bid.tail(self.Window + 1, dataframe=True)
            if len(prices) < self.Window + 1: return self._pad_()
            return pl.DataFrame({self.Name: pl.Series([prices.to_numpy()[-2]], dtype=pl.Float64)})
        old_price = market.CloseTicks.Bid.last(shift=self.Window)
        if old_price is None or new_price is None: return self._pad_()
        change = abs(new_price - old_price)
        prices = market.CloseTicks.Bid.tail(self.Window + 1, dataframe=True)
        p = prices.to_numpy()
        volatility = sum(abs(p[i] - p[i-1]) for i in range(1, len(p)))
        er = change / volatility if volatility != 0 else 0
        sc = (er * (fast_alpha - slow_alpha) + slow_alpha) ** 2
        new_kama = prev_kama + sc * (new_price - prev_kama)
        return pl.DataFrame({self.Name: pl.Series([new_kama], dtype=pl.Float64)})