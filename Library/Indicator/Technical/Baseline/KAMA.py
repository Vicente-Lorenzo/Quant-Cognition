from typing import Union

from Library.Database.Dataframe import np, pl
from Library.Indicator.Technical.Technical import BaselineAPI

class KaufmanAdaptiveMovingAverageAPI(BaselineAPI):

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        if len(series) <= window: return KaufmanAdaptiveMovingAverageAPI._nulls_(len(series))
        fast_alpha = 2 / (2 + 1)
        slow_alpha = 2 / (30 + 1)
        p = series.to_numpy()
        change = np.abs(p[window:] - p[:-window])
        diff = np.abs(p[1:] - p[:-1])
        volatility = np.convolve(diff, np.ones(window, dtype=int), 'valid')
        er = np.zeros_like(change)
        mask = volatility != 0
        er[mask] = change[mask] / volatility[mask]
        sc = (er * (fast_alpha - slow_alpha) + slow_alpha) ** 2
        kama = np.full_like(p, np.nan)
        kama[window - 1] = p[window - 1]
        for i in range(window, len(p)):
            kama[i] = kama[i - 1] + sc[i - window] * (p[i] - kama[i - 1])
        return pl.Series(kama)

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        fast_alpha = 2 / (2 + 1)
        slow_alpha = 2 / (30 + 1)
        prev_kama = self.Result.last()
        new_price = (data[-1] if len(data) > 0 else None)
        if prev_kama is None:
            if len(data) < self.Window + 1: return self._pad_()
            kama = self._batch_(data, self.Window)
            seed = kama[-1]
            if seed is None or seed != seed: return self._pad_()
            return self._scalar_(float(seed))
        old_price = (data[-(self.Window + 1)] if len(data) > self.Window else None)
        if old_price is None or new_price is None: return self._pad_()
        change = abs(new_price - old_price)
        prices = data.tail(self.Window + 1)
        p = prices.to_numpy()
        volatility = sum(abs(p[i] - p[i - 1]) for i in range(1, len(p)))
        er = change / volatility if volatility != 0 else 0
        sc = (er * (fast_alpha - slow_alpha) + slow_alpha) ** 2
        new_kama = prev_kama + sc * (new_price - prev_kama)
        return self._scalar_(new_kama)