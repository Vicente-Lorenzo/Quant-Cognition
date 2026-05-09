from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType
from Library.Indicator.Indicator import IndicatorMode
from Library.Market.Series import SeriesAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class ExponentialMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline

    def __init__(self, name: str, window: int, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.Result = SeriesAPI(self.Name)
        self._data_ = None

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        if series.is_empty(): return pl.Series([None] * len(series), dtype=pl.Float64)
        ema = series.ewm_mean(span=window, adjust=False)
        nulls = [None] * (window - 1)
        if len(ema) > window - 1: return pl.Series(nulls + ema.to_list()[window - 1:])
        return pl.Series([None] * len(ema))

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
        prev_ema = self.Result.last()
        alpha = 2 / (self.Window + 1)
        if prev_ema is None:
            prices = market.CloseTicks.Bid.tail(self.Window, dataframe=True)
            if len(prices) < self.Window: return self._pad_()
            return pl.DataFrame({self.Name: pl.Series([prices.mean()], dtype=pl.Float64)})
        new_price = market.CloseTicks.Bid.last()
        if new_price is None: return self._pad_()
        new_ema = prev_ema + alpha * (new_price - prev_ema)
        return pl.DataFrame({self.Name: pl.Series([new_ema], dtype=pl.Float64)})