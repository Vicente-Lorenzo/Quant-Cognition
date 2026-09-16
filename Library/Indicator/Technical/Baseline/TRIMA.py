import math

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import BaselineAPI

class TriangularMovingAverageAPI(BaselineAPI):

    _TAIL_ = 3

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        if series.is_empty(): return TriangularMovingAverageAPI._nulls_(len(series))
        w1 = math.ceil(window / 2.0)
        w2 = math.ceil((window + 1) / 2.0)
        sma1 = TriangularMovingAverageAPI._mask_(series.rolling_mean(window_size=w1), w1 - 1)
        trima = sma1.rolling_mean(window_size=w2)
        return TriangularMovingAverageAPI._mask_(trima, w1 - 1 + w2 - 1)