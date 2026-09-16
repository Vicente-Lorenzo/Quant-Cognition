from typing import Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import BaselineAPI

class SimpleMovingAverageAPI(BaselineAPI):

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        if series.is_empty(): return SimpleMovingAverageAPI._nulls_(len(series))
        return series.rolling_mean(window_size=window)

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        prev_sma = self.Result.last()
        if prev_sma is None:
            prices = data.tail(self.Window)
            if len(prices) < self.Window: return self._pad_()
            return self._scalar_(float(prices.mean()))
        new_price = (data[-1] if len(data) > 0 else None)
        old_price = (data[-(self.Window + 1)] if len(data) > self.Window else None)
        if new_price is None or old_price is None: return self._pad_()
        new_sma = prev_sma + (new_price - old_price) / self.Window
        return self._scalar_(new_sma)