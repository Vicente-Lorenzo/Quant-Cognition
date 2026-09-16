import math

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Baseline.WMA import WeightedMovingAverageAPI
from Library.Indicator.Technical.Technical import BaselineAPI

class HullMovingAverageAPI(BaselineAPI):

    _TAIL_ = 3

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        half_w = math.floor(window / 2)
        sqrt_w = math.floor(math.sqrt(window))
        if len(series) < window + sqrt_w: return HullMovingAverageAPI._nulls_(len(series))
        s_np = series.to_numpy()
        apply_wma = WeightedMovingAverageAPI._weighted_
        wma_f = apply_wma(s_np, window)
        wma_h = apply_wma(s_np, half_w)
        diff = 2 * wma_h - wma_f
        hma = apply_wma(diff, sqrt_w)
        return pl.Series(hma)