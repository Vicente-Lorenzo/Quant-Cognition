from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Indicator import IndicatorMode
from Library.Market.Series import SeriesAPI
from Library.Utility.Enumeration import EnumerationAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class TechnicalType(EnumerationAPI):
    Baseline = 0
    Overlap = 1
    Momentum = 2
    Volume = 3
    Volatility = 4
    Pattern = 5
    Other = 6

class TechnicalAPI:

    Type: ClassVar[TechnicalType] = TechnicalType.Other

    def __init__(self, name: str, window: int, mode: IndicatorMode, **indicators) -> None:
        self.Name: str = name
        self.Mode: IndicatorMode = mode
        self.Result: SeriesAPI = SeriesAPI(self.Name)
        self._data_: Union[pl.DataFrame, None] = None
        self._indicators_: list = list(indicators.values())
        for k, v in indicators.items():
            setattr(self, k, v)
        self.Window: int = self._window_() or window

    def _window_(self) -> int:
        return max((ind.Window for ind in self._indicators_ if hasattr(ind, "Window")), default=0)

    def _extract_(self, market: MarketAPI) -> Union[pl.Series, pl.DataFrame]:
        return market.CloseTicks.Price.tail()

    def _pad_(self) -> pl.DataFrame:
        return pl.DataFrame({self.Name: pl.Series([None], dtype=pl.Float64)})

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        return self._pad_()

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        return self._pad_()

    def calculate(self, data: Union[pl.Series, pl.DataFrame], batch: bool = False) -> pl.DataFrame:
        return self.batch(data) if batch else self.stream(data)

    def init_data(self, market: MarketAPI) -> None:
        self._data_ = self.calculate(self._extract_(market), batch=True)
        self.Result.init_data(self._data_)
        for ind in self._indicators_:
            if hasattr(ind, "init_data"): ind.init_data(market)

    def update_data(self, market: MarketAPI) -> None:
        if self._data_ is None: return self.init_data(market)
        df = self.calculate(self._extract_(market), batch=False)
        self._data_ = self._data_.vstack(df)
        self.Result.init_data(self._data_)
        for ind in self._indicators_:
            if hasattr(ind, "update_data"): ind.update_data(market)

    def update_offset(self, offset: int = 1) -> None:
        self.Result.update_offset(offset)
        for ind in self._indicators_:
            if hasattr(ind, "update_offset"): ind.update_offset(offset)

    def filter_buy(self, market: MarketAPI) -> bool:
        return False

    def filter_sell(self, market: MarketAPI) -> bool:
        return False

    def signal_buy(self, market: MarketAPI) -> bool:
        return False

    def signal_sell(self, market: MarketAPI) -> bool:
        return False