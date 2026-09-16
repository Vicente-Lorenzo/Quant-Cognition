from typing import Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import BaselineAPI

class ExponentialMovingAverageAPI(BaselineAPI):

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        if series.is_empty(): return ExponentialMovingAverageAPI._nulls_(len(series))
        ema = series.ewm_mean(span=window, adjust=False)
        return ExponentialMovingAverageAPI._mask_(ema, window - 1)

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        prev_ema = self.Result.last()
        alpha = 2 / (self.Window + 1)
        if prev_ema is None:
            if len(data) < self.Window: return self._pad_()
            ema = data.ewm_mean(span=self.Window, adjust=False)
            return self._scalar_(float(ema[-1]))
        new_price = (data[-1] if len(data) > 0 else None)
        if new_price is None: return self._pad_()
        new_ema = prev_ema + alpha * (new_price - prev_ema)
        return self._scalar_(new_ema)