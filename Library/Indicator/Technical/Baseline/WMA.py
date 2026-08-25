from __future__ import annotations

from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import np, pl
from Library.Indicator.Technical.Technical import MODE, TechnicalAPI, TechnicalType, WINDOW

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class WeightedMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline
    Parameters = (WINDOW, MODE)

    @staticmethod
    def _weighted_(values: np.ndarray, window: int) -> np.ndarray:
        weights = np.arange(1, window + 1, dtype=float)
        wma = np.full_like(values, fill_value=np.nan, dtype=float)
        wma[window - 1:] = np.convolve(values, weights[::-1], "valid") / weights.sum()
        return wma

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        if len(series) < window: return pl.Series([None] * len(series), dtype=pl.Float64)
        return pl.Series(WeightedMovingAverageAPI._weighted_(series.to_numpy(), window))

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        ma = self._batch_(data, self.Window)
        return pl.DataFrame({self.Name: ma})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        series = data.tail(self.Window)
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