from __future__ import annotations

import math
from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Baseline.WMA import WeightedMovingAverageAPI
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class HullMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        half_w = math.floor(window / 2)
        sqrt_w = math.floor(math.sqrt(window))
        if len(series) < window + sqrt_w: return pl.Series([None] * len(series), dtype=pl.Float64)
        s_np = series.to_numpy()
        apply_wma = WeightedMovingAverageAPI._weighted_
        wma_f = apply_wma(s_np, window)
        wma_h = apply_wma(s_np, half_w)
        diff = 2 * wma_h - wma_f
        hma = apply_wma(diff, sqrt_w)
        return pl.Series(hma)

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        ma = self._batch_(data, self.Window)
        return pl.DataFrame({self.Name: ma})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        series = data.tail(self.Window * 3)
        if len(series) < self.Window: return self._pad_()
        ma = self._batch_(series, self.Window)
        return pl.DataFrame({self.Name: pl.Series([ma[-1]], dtype=pl.Float64)})

    def filter_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.over(self.Result))

    def filter_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.under(self.Result))

    def signal_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossover(self.Result))

    def signal_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossunder(self.Result))