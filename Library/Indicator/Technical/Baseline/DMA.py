from __future__ import annotations

from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Indicator import IndicatorMode
from Library.Indicator.Technical.Baseline.MA import MovingAverageType, MovingAverageAPI
from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class DoubleMovingAverageAPI(TechnicalAPI):

    Type = TechnicalType.Baseline

    def __init__(self, name: str, window: int, type: MovingAverageType, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=window, mode=mode)
        self.TypeMA: MovingAverageType = type

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        ma1 = MovingAverageAPI._batch_(data, self.Window, self.TypeMA)
        s_valid = ma1.fill_nan(None).drop_nulls()
        if s_valid.is_empty(): return self._pad_()
        ma2_valid = MovingAverageAPI._batch_(s_valid, self.Window, self.TypeMA)
        nulls = [None] * (len(data) - len(ma2_valid))
        ma2 = pl.Series(nulls + ma2_valid.to_list())
        dma = 2 * ma1 - ma2
        return pl.DataFrame({self.Name: dma})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        series = data.tail(self.Window * 5)
        if len(series) < self.Window * 2: return self._pad_()
        ma1 = MovingAverageAPI._batch_(series, self.Window, self.TypeMA)
        s_valid = ma1.fill_nan(None).drop_nulls()
        ma2_valid = MovingAverageAPI._batch_(s_valid, self.Window, self.TypeMA)
        nulls = [None] * (len(series) - len(ma2_valid))
        ma2 = pl.Series(nulls + ma2_valid.to_list())
        dma = 2 * ma1 - ma2
        return pl.DataFrame({self.Name: pl.Series([dma.to_list()[-1]], dtype=pl.Float64)})

    def filter_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.over(self.Result))

    def filter_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.under(self.Result))

    def signal_buy(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossover(self.Result))

    def signal_sell(self, market: MarketAPI) -> bool:
        return bool(market.CloseTicks.Price.crossunder(self.Result))