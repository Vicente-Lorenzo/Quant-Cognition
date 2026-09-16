from typing import Union

from Library.Database.Dataframe import pl
from Library.Indicator.Indicator import IndicatorMode
from Library.Indicator.Technical.Baseline.MA import MOVING, MovingAverageAPI, MovingAverageType
from Library.Indicator.Technical.Technical import MODE, PriceSignalAPI, TechnicalType, WINDOW

class DoubleMovingAverageAPI(PriceSignalAPI):

    Type = TechnicalType.Baseline
    Parameters = (WINDOW, MOVING, MODE)

    def __init__(self, name: str, window: int, type: MovingAverageType, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.TypeMA: MovingAverageType = type

    def _compose_(self, series: pl.Series, guard: bool) -> Union[pl.Series, None]:
        ma1 = MovingAverageAPI._batch_(series, self.Window, self.TypeMA)
        valid = ma1.fill_nan(None).drop_nulls()
        if guard and valid.is_empty(): return None
        return 2 * ma1 - MovingAverageAPI._nest_(valid, self.Window, self.TypeMA, len(series))

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        dma = self._compose_(data, True)
        return self._pad_() if dma is None else pl.DataFrame({self.Name: dma})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        series = data.tail(self.Window * 5)
        if len(series) < self.Window * 2: return self._pad_()
        return self._scalar_(self._compose_(series, False)[-1])