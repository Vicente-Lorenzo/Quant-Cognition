from __future__ import annotations

from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class AverageTrueRangeAPI(TechnicalAPI):

    Type = TechnicalType.Volatility

    def _extract_(self, market: MarketAPI) -> Union[pl.Series, pl.DataFrame]:
        return pl.DataFrame({
            "High": market.HighTicks.Price.tail(),
            "Low": market.LowTicks.Price.tail(),
            "Close": market.CloseTicks.Price.tail()
        })

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        highs = data["High"]
        lows = data["Low"]
        closes = data["Close"]
        if highs.is_empty(): return self._pad_()
        prev_closes = closes.shift(1)
        tr1 = highs - lows
        tr2 = (highs - prev_closes).abs()
        tr3 = (lows - prev_closes).abs()
        tr = pl.DataFrame({"tr1": tr1, "tr2": tr2, "tr3": tr3}).max_horizontal()
        atr = tr.ewm_mean(alpha=1.0 / self.Window, adjust=False)
        nulls = [None] * self.Window
        if len(atr) > self.Window:
            atr = pl.Series(nulls + atr.to_list()[self.Window:])
        else:
            atr = pl.Series([None] * len(atr))
        return pl.DataFrame({self.Name: atr})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        prev_atr = self.Result.last()
        highs = data["High"]
        lows = data["Low"]
        closes = data["Close"]
        new_high = (highs[-1] if len(highs) > 0 else None)
        new_low = (lows[-1] if len(lows) > 0 else None)
        prev_close = (closes[-2] if len(closes) > 1 else None)
        if new_high is None or new_low is None or prev_close is None: return self._pad_()
        tr1 = new_high - new_low
        tr2 = abs(new_high - prev_close)
        tr3 = abs(new_low - prev_close)
        tr = max(tr1, tr2, tr3)
        if prev_atr is None:
            if len(highs) < self.Window + 1: return self._pad_()
            prev_closes = closes.shift(1)
            t1 = highs - lows
            t2 = (highs - prev_closes).abs()
            t3 = (lows - prev_closes).abs()
            tr_series = pl.DataFrame({"t1": t1, "t2": t2, "t3": t3}).max_horizontal().drop_nulls()
            if len(tr_series) < self.Window: return self._pad_()
            return pl.DataFrame({self.Name: pl.Series([float(tr_series.mean())], dtype=pl.Float64)})
        new_atr = (prev_atr * (self.Window - 1) + tr) / self.Window
        return pl.DataFrame({self.Name: pl.Series([new_atr], dtype=pl.Float64)})