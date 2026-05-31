from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class WeightedMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        if len(series) < window: return pl.Series([None] * len(series), dtype=pl.Float64)
        weights = np.arange(1, window + 1)
        w_sum = weights.sum()
        s_np = series.to_numpy()
        wma = np.full_like(s_np, fill_value=np.nan, dtype=float)
        for i in range(window - 1, len(s_np)):
            wma[i] = np.dot(s_np[i - window + 1: i + 1], weights) / w_sum
        return pl.Series(wma)

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        ma = self._batch_(data, self.Window)
        return pl.DataFrame({self.Name: ma})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        series = data.tail(self.Window)
        if len(series) < self.Window: return self._pad_()
        ma = self._batch_(series, self.Window)
        return pl.DataFrame({self.Name: pl.Series([ma.to_list()[-1]], dtype=pl.Float64)})

    def filter_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.over(self.Result))

    def filter_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.under(self.Result))

    def signal_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossover(self.Result))

    def signal_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossunder(self.Result))