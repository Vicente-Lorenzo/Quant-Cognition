from typing import Union

from Library.Database.Dataframe import pl
from Library.Indicator.Indicator import IndicatorMode
from Library.Indicator.Technical.Baseline.MA import MovingAverageAPI, MovingAverageType
from Library.Indicator.Technical.Technical import PriceSignalAPI, TechnicalAPI, TechnicalType

class TripleMovingAverageAPI(PriceSignalAPI):

    Type = TechnicalType.Baseline
    Parameters = (TechnicalAPI.WINDOW, MovingAverageAPI.MOVING, TechnicalAPI.MODE)

    def __init__(self, name: str, window: int, type: MovingAverageType, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.TypeMA: MovingAverageType = type

    def _compose_(self, series: pl.Series, guard: bool) -> Union[pl.Series, None]:
        ma1 = MovingAverageAPI._batch_(series, self.Window, self.TypeMA)
        valid1 = ma1.fill_nan(None).drop_nulls()
        if guard and valid1.is_empty(): return None
        ma2 = MovingAverageAPI._nest_(valid1, self.Window, self.TypeMA, len(series))
        valid2 = ma2.fill_nan(None).drop_nulls()
        if guard and valid2.is_empty(): return None
        ma3 = MovingAverageAPI._nest_(valid2, self.Window, self.TypeMA, len(series))
        return 3 * ma1 - 3 * ma2 + ma3

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        tma = self._compose_(data, True)
        return self._pad_() if tma is None else pl.DataFrame({self.Name: tma})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        series = data.tail(self.Window * 7)
        if len(series) < self.Window * 3: return self._pad_()
        return self._scalar_(self._compose_(series, False)[-1])