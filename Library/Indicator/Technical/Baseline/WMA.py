from Library.Database.Dataframe import np, pl
from Library.Indicator.Technical.Technical import BaselineAPI

class WeightedMovingAverageAPI(BaselineAPI):

    @staticmethod
    def _weighted_(values: np.ndarray, window: int) -> np.ndarray:
        weights = np.arange(1, window + 1, dtype=float)
        wma = np.full_like(values, fill_value=np.nan, dtype=float)
        wma[window - 1:] = np.convolve(values, weights[::-1], "valid") / weights.sum()
        return wma

    @staticmethod
    def _batch_(series: pl.Series, window: int) -> pl.Series:
        if len(series) < window: return WeightedMovingAverageAPI._nulls_(len(series))
        return pl.Series(WeightedMovingAverageAPI._weighted_(series.to_numpy(), window))