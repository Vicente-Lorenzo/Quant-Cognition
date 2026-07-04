from __future__ import annotations

import math
from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class TriangularMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        if series.is_empty(): return pl.Series([None] * len(series), dtype=pl.Float64)
        w1 = math.ceil(window / 2.0)
        w2 = math.ceil((window + 1) / 2.0)
        sma1 = series.rolling_mean(window_size=w1)
        nulls1 = [None] * (w1 - 1)
        if len(sma1) > w1 - 1: sma1 = pl.Series(nulls1 + sma1.to_list()[w1 - 1:])
        else: sma1 = pl.Series([None] * len(sma1), dtype=pl.Float64)
        trima = sma1.rolling_mean(window_size=w2)
        nulls2 = [None] * (w1 - 1 + w2 - 1)
        if len(trima) > w1 - 1 + w2 - 1: return pl.Series(nulls2 + trima.to_list()[w1 - 1 + w2 - 1:])
        return pl.Series([None] * len(trima), dtype=pl.Float64)

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        ma = self._batch_(data, self.Window)
        return pl.DataFrame({self.Name: ma})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        series = data.tail(self.Window * 3)
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