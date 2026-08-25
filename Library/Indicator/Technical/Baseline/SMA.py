from __future__ import annotations

from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import MODE, TechnicalAPI, TechnicalType, WINDOW

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class SimpleMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline
    Parameters = (WINDOW, MODE)

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        if series.is_empty(): return pl.Series([None] * len(series), dtype=pl.Float64)
        return series.rolling_mean(window_size=window)

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        ma = self._batch_(data, self.Window)
        return pl.DataFrame({self.Name: ma})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        prev_sma = self.Result.last()
        if prev_sma is None:
            prices = data.tail(self.Window)
            if len(prices) < self.Window: return self._pad_()
            return pl.DataFrame({self.Name: pl.Series([float(prices.mean())], dtype=pl.Float64)})
        new_price = (data[-1] if len(data) > 0 else None)
        old_price = (data[-(self.Window + 1)] if len(data) > self.Window else None)
        if new_price is None or old_price is None: return self._pad_()
        new_sma = prev_sma + (new_price - old_price) / self.Window
        return pl.DataFrame({self.Name: pl.Series([new_sma], dtype=pl.Float64)})

    def filter_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.over(self.Result))

    def filter_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.under(self.Result))

    def signal_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossover(self.Result))

    def signal_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossunder(self.Result))