from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType
from Library.Indicator.Indicator import IndicatorMode
from Library.Market.Series import SeriesAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class AverageTrueRangeAPI(TechnicalAPI):

    Type = TechnicalType.Volatility

    def __init__(self, name: str, window: int, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.Result = SeriesAPI(self.Name)
        self._data_ = None

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
        highs = market.HighTicks.Bid.tail(dataframe=True)
        lows = market.LowTicks.Bid.tail(dataframe=True)
        closes = market.CloseTicks.Bid.tail(dataframe=True)
        if highs.is_empty(): return self._pad_()
        prev_closes = closes.shift(1)
        tr1 = highs - lows
        tr2 = (highs - prev_closes).abs()
        tr3 = (lows - prev_closes).abs()
        tr = pl.max_horizontal(tr1, tr2, tr3)
        atr = tr.ewm_mean(alpha=1.0/self.Window, adjust=False)
        nulls = [None] * self.Window
        if len(atr) > self.Window:
            atr = pl.Series(nulls + atr.to_list()[self.Window:])
        else:
            atr = pl.Series([None] * len(atr))
        return pl.DataFrame({self.Name: atr})

    def stream(self, market: MarketAPI) -> pl.DataFrame:
        prev_atr = self.Result.last()
        new_high = market.HighTicks.Bid.last()
        new_low = market.LowTicks.Bid.last()
        prev_close = market.CloseTicks.Bid.last(shift=1)
        if new_high is None or new_low is None or prev_close is None: return self._pad_()
        tr1 = new_high - new_low
        tr2 = abs(new_high - prev_close)
        tr3 = abs(new_low - prev_close)
        tr = max(tr1, tr2, tr3)
        if prev_atr is None:
            highs = market.HighTicks.Bid.tail(self.Window + 1, dataframe=True)
            lows = market.LowTicks.Bid.tail(self.Window + 1, dataframe=True)
            closes = market.CloseTicks.Bid.tail(self.Window + 1, dataframe=True)
            if len(highs) < self.Window + 1: return self._pad_()
            prev_closes = closes.shift(1)
            t1 = highs - lows
            t2 = (highs - prev_closes).abs()
            t3 = (lows - prev_closes).abs()
            tr_series = pl.max_horizontal(t1, t2, t3).drop_nulls()
            if len(tr_series) < self.Window: return self._pad_()
            return pl.DataFrame({self.Name: pl.Series([tr_series.mean()], dtype=pl.Float64)})
        new_atr = (prev_atr * (self.Window - 1) + tr) / self.Window
        return pl.DataFrame({self.Name: pl.Series([new_atr], dtype=pl.Float64)})