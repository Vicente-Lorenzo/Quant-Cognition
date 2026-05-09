from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType
from Library.Indicator.Indicator import IndicatorMode
from Library.Market.Series import SeriesAPI
from Library.Indicator.Technical.Baseline.MA import MovingAverageType, MovingAverageAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class TripleMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline

    def __init__(self, name: str, window: int, type: MovingAverageType, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.TypeMA = type
        self.Result = SeriesAPI(self.Name)
        self._data_ = None

    def init_data(self, market: MarketAPI) -> None:
        self._data_ = self.calculate(market, batch=True)
        return self.Result.init_data(self._data_)

    def update_data(self, market: MarketAPI) -> None:
        if self._data_ is None: return self.init_data(market)
        df = self.calculate(market, batch=False)
        self._data_ = self._data_.vstack(df)
        return self.Result.init_data(self._data_)

    def update_offset(self, offset: int = 1) -> None:
        self.Result.update_offset(offset)

    def _pad_(self) -> pl.DataFrame:
        return pl.DataFrame({self.Name: pl.Series([None], dtype=pl.Float64)})

    def calculate(self, market: MarketAPI, batch: bool = False) -> pl.DataFrame:
        if batch: return self.batch(market)
        return self.stream(market)

    def batch(self, market: MarketAPI) -> pl.DataFrame:
        series = market.CloseTicks.Bid.tail(dataframe=True)
        if series.is_empty(): return self._pad_()
        ma1 = MovingAverageAPI._batch_(series, self.Window, self.TypeMA)
        s1_valid = ma1.drop_nulls()
        if s1_valid.is_empty(): return self._pad_()
        ma2_valid = MovingAverageAPI._batch_(s1_valid, self.Window, self.TypeMA)
        nulls2 = [None] * (len(series) - len(ma2_valid))
        ma2 = pl.Series(nulls2 + ma2_valid.to_list())
        s2_valid = ma2.drop_nulls()
        if s2_valid.is_empty(): return self._pad_()
        ma3_valid = MovingAverageAPI._batch_(s2_valid, self.Window, self.TypeMA)
        nulls3 = [None] * (len(series) - len(ma3_valid))
        ma3 = pl.Series(nulls3 + ma3_valid.to_list())
        tma = 3 * ma1 - 3 * ma2 + ma3
        return pl.DataFrame({self.Name: tma})

    def stream(self, market: MarketAPI) -> pl.DataFrame:
        required_bars = self.Window * 7
        series = market.CloseTicks.Bid.tail(required_bars, dataframe=True)
        if len(series) < self.Window * 3: return self._pad_()
        ma1 = MovingAverageAPI._batch_(series, self.Window, self.TypeMA)
        s1_valid = ma1.drop_nulls()
        ma2_valid = MovingAverageAPI._batch_(s1_valid, self.Window, self.TypeMA)
        nulls2 = [None] * (len(series) - len(ma2_valid))
        ma2 = pl.Series(nulls2 + ma2_valid.to_list())
        s2_valid = ma2.drop_nulls()
        ma3_valid = MovingAverageAPI._batch_(s2_valid, self.Window, self.TypeMA)
        nulls3 = [None] * (len(series) - len(ma3_valid))
        ma3 = pl.Series(nulls3 + ma3_valid.to_list())
        tma = 3 * ma1 - 3 * ma2 + ma3
        return pl.DataFrame({self.Name: pl.Series([tma.to_list()[-1]], dtype=pl.Float64)})