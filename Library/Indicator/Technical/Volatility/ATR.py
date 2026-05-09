from __future__ import annotations

from typing import TYPE_CHECKING, Union

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

    def _extract_(self, market: MarketAPI) -> pl.DataFrame:
        return pl.DataFrame({
            "High": market.HighTicks.Price.tail(),
            "Low": market.LowTicks.Price.tail(),
            "Close": market.CloseTicks.Price.tail()
        })

    def init_data(self, market: MarketAPI) -> None:
        self._data_ = self.calculate(self._extract_(market), batch=True)
        return self.Result.init_data(self._data_)

    def update_data(self, market: MarketAPI) -> None:
        if self._data_ is None: return self.init_data(market)
        df = self.calculate(self._extract_(market), batch=False)
        self._data_ = self._data_.vstack(df)
        return self.Result.init_data(self._data_)

    def update_offset(self, offset: int = 1) -> None:
        self.Result.update_offset(offset)

    def _pad_(self) -> pl.DataFrame:
        return pl.DataFrame({self.Name: pl.Series([None], dtype=pl.Float64)})

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        highs = data["High"]
        lows = data["Low"]
        closes = data["Close"]
        if highs.is_empty(): return self._pad_()
        prev_closes = closes.shift(1)
        tr1 = highs - lows
        tr2 = (highs - prev_closes).abs()
        tr3 = (lows - prev_closes).abs()
        tr = pl.DataFrame([tr1, tr2, tr3]).max_horizontal()
        atr = tr.ewm_mean(alpha=1.0/self.Window, adjust=False)
        nulls = [None] * self.Window
        if len(atr) > self.Window:
            atr = pl.Series(nulls + atr.to_list()[self.Window:])
        else:
            atr = pl.Series([None] * len(atr))
        return pl.DataFrame({self.Name: atr})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        prev_atr = self.Result.last()
        new_high = (data["High"][-1] if len(data["High"]) > 0 else None)
        new_low = (data["Low"][-1] if len(data["Low"]) > 0 else None)
        prev_close = (data["Close"][-2] if len(data["Close"]) > 1 else None)
        if new_high is None or new_low is None or prev_close is None: return self._pad_()
        tr1 = new_high - new_low
        tr2 = abs(new_high - prev_close)
        tr3 = abs(new_low - prev_close)
        tr = max(tr1, tr2, tr3)
        if prev_atr is None:
            highs = data["High"]
            lows = data["Low"]
            closes = data["Close"]
            if len(highs) < self.Window + 1: return self._pad_()
            prev_closes = closes.shift(1)
            t1 = highs - lows
            t2 = (highs - prev_closes).abs()
            t3 = (lows - prev_closes).abs()
            tr_series = pl.DataFrame([t1, t2, t3]).max_horizontal().drop_nulls()
            if len(tr_series) < self.Window: return self._pad_()
            return pl.DataFrame({self.Name: pl.Series([tr_series.mean()], dtype=pl.Float64)})
        new_atr = (prev_atr * (self.Window - 1) + tr) / self.Window
        return pl.DataFrame({self.Name: pl.Series([new_atr], dtype=pl.Float64)})

    def calculate(self, data: Union[pl.Series, pl.DataFrame], batch: bool = False) -> pl.DataFrame:
        if batch: return self.batch(data)
        return self.stream(data)