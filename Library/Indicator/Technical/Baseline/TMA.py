from __future__ import annotations

from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Indicator import IndicatorMode
from Library.Indicator.Technical.Baseline.MA import MovingAverageType, MovingAverageAPI
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class TripleMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline

    def __init__(self, name: str, window: int, type: MovingAverageType, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.TypeMA: MovingAverageType = type

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        ma1 = MovingAverageAPI._batch_(data, self.Window, self.TypeMA)
        s1_valid = ma1.drop_nulls()
        if s1_valid.is_empty(): return self._pad_()
        ma2_valid = MovingAverageAPI._batch_(s1_valid, self.Window, self.TypeMA)
        nulls2 = [None] * (len(data) - len(ma2_valid))
        ma2 = pl.Series(nulls2 + ma2_valid.to_list())
        s2_valid = ma2.drop_nulls()
        if s2_valid.is_empty(): return self._pad_()
        ma3_valid = MovingAverageAPI._batch_(s2_valid, self.Window, self.TypeMA)
        nulls3 = [None] * (len(data) - len(ma3_valid))
        ma3 = pl.Series(nulls3 + ma3_valid.to_list())
        tma = 3 * ma1 - 3 * ma2 + ma3
        return pl.DataFrame({self.Name: tma})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        series = data.tail(self.Window * 7)
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

    def filter_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.over(self.Result))

    def filter_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.under(self.Result))

    def signal_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossover(self.Result))

    def signal_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossunder(self.Result))