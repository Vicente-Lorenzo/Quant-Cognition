from __future__ import annotations

from typing import Union
from abc import ABC, abstractmethod
from Library.Database.Dataframe import pl
from Library.Market.Series import SeriesAPI
from Library.Market.Market import MarketAPI

class BaseIndicatorAPI(ABC):
    MARGIN: int = 200

    def __init__(self) -> None:
        self._offset_: int = 1
        self._series_: list[SeriesAPI] = []
        self._data_: Union[pl.DataFrame, None] = None

    def dataframe(self) -> pl.DataFrame:
        return self._data_ if self._data_ is not None else pl.DataFrame()

    def last(self, shift: int = 0) -> pl.DataFrame:
        return self.dataframe()[-(self._offset_ + shift)]

    def head(self, n: Union[int, None] = None) -> pl.DataFrame:
        return self.dataframe().head(n)

    def tail(self, n: Union[int, None] = None) -> pl.DataFrame:
        return self.dataframe().tail(n)

    @abstractmethod
    def calculate(self, market: MarketAPI, window: Union[int, None] = None) -> pl.DataFrame:
        pass

    @abstractmethod
    def filter_buy(self, market: Union[MarketAPI, None] = None, shift: int = 0) -> bool:
        pass

    @abstractmethod
    def filter_sell(self, market: Union[MarketAPI, None] = None, shift: int = 0) -> bool:
        pass

    @abstractmethod
    def signal_buy(self, market: Union[MarketAPI, None] = None, shift: int = 0) -> bool:
        pass

    @abstractmethod
    def signal_sell(self, market: Union[MarketAPI, None] = None, shift: int = 0) -> bool:
        pass

    def init_data(self, market: MarketAPI) -> None:
        self._series_ = []
        self._data_ = pl.DataFrame()
        output_df = self.calculate(market)
        
        for name, series in output_df.iter_columns():
            series = series.fill_nan(None)
            tseries = SeriesAPI(name)
            setattr(self, name.split("_")[-1], tseries)
            self._series_.append(tseries)
            self._data_ = self._data_.with_columns(series)
            
        self._data_ = self._data_.rechunk()
        for tseries in self._series_:
            tseries.init_data(self._data_)

    def update_data(self, market: MarketAPI, window: int) -> None:
        self._data_.extend(self.calculate(market, window).tail(1))

    def update_offset(self, offset: int) -> None:
        self._offset_ = offset
        for tseries in self._series_:
            tseries.update_offset(offset)

    def __repr__(self) -> str:
        return repr(self.dataframe())