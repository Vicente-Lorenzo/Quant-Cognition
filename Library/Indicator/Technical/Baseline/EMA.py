from __future__ import annotations

from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import MODE, TechnicalAPI, TechnicalType, WINDOW

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class ExponentialMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline
    Parameters = (WINDOW, MODE)

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        if series.is_empty(): return pl.Series([None] * len(series), dtype=pl.Float64)
        ema = series.ewm_mean(span=window, adjust=False)
        nulls = [None] * (window - 1)
        if len(ema) > window - 1: return pl.Series(nulls + ema.to_list()[window - 1:])
        return pl.Series([None] * len(ema), dtype=pl.Float64)

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        ma = self._batch_(data, self.Window)
        return pl.DataFrame({self.Name: ma})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        prev_ema = self.Result.last()
        alpha = 2 / (self.Window + 1)
        if prev_ema is None:
            if len(data) < self.Window: return self._pad_()
            ema = data.ewm_mean(span=self.Window, adjust=False)
            return pl.DataFrame({self.Name: pl.Series([float(ema[-1])], dtype=pl.Float64)})
        new_price = (data[-1] if len(data) > 0 else None)
        if new_price is None: return self._pad_()
        new_ema = prev_ema + alpha * (new_price - prev_ema)
        return pl.DataFrame({self.Name: pl.Series([new_ema], dtype=pl.Float64)})

    def filter_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.over(self.Result))

    def filter_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.under(self.Result))

    def signal_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossover(self.Result))

    def signal_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossunder(self.Result))