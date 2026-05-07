from typing import Union
from Library.Database.Dataframe import pl
from Library.Utility import IndicatorConfigurationAPI
from Library.Analyst import SeriesAPI, MarketAPI, IndicatorsAPI

class IndicatorAPI:

    def __init__(self, indicator: str, parameters: Union[list, None] = None):
        self._offset: int = 1

        self._indicator: IndicatorConfigurationAPI = getattr(IndicatorsAPI, indicator)
        self._parameters: dict = dict(zip(self._indicator.Parameters.keys(), parameters))
        self._sids = [f"{indicator}_{'_'.join(map(str, parameters)) + '_' if parameters else ''}{output}" for output in self._indicator.Output]

        self._series: Union[list[SeriesAPI], None] = None
        self._data: Union[pl.DataFrame, None] = None

    def data(self) -> pl.DataFrame:
        return self._data if self._data is not None else pl.DataFrame()

    def head(self, n: Union[int, None] = None) -> pl.DataFrame:
        return self._data.head(n)

    def tail(self, n: Union[int, None] = None) -> pl.DataFrame:
        return self._data.tail(n)

    def last(self, shift: int = 0) -> pl.DataFrame:
        return self.data()[-(self._offset + shift)]

    def calculate(self, market: MarketAPI, window: Union[int, None] = None) -> pl.DataFrame:
        input_series = [tseries.tail(window) if window else tseries.data() for tseries in self._indicator.Input(market)]
        df = pl.DataFrame(self._indicator.Function(input_series, **self._parameters))
        df.columns = self._sids
        return df

    def init_data(self, market: MarketAPI) -> None:
        self._series = []
        self._data = pl.DataFrame()
        output_df = self.calculate(market)
        for name, sid, series in zip(self._indicator.Output, self._sids, output_df):
            series = series.fill_nan(None)
            tseries = SeriesAPI(sid)
            setattr(self, name, tseries)
            self._series.append(tseries)
            self._data = self._data.with_columns(series)
        self._data = self._data.rechunk()
        for tseries in self._series:
            tseries.init_data(self._data)

    def update_data(self, market: MarketAPI, window: int) -> None:
        self._data.extend(self.calculate(market, window)[-1])

    def update_offset(self, offset: int) -> None:
        self._offset = offset
        for tseries in self._series:
            tseries.update_offset(offset)

    def filter_buy(self, market: Union[MarketAPI, None] = None, shift: int = 0) -> bool:
        return self._indicator.FilterBuy(market, self, shift)

    def filter_sell(self, market: Union[MarketAPI, None] = None, shift: int = 0) -> bool:
        return self._indicator.FilterSell(market, self, shift)

    def signal_buy(self, market: Union[MarketAPI, None] = None, shift: int = 0) -> bool:
        return self._indicator.SignalBuy(market, self, shift)

    def signal_sell(self, market: Union[MarketAPI, None] = None, shift: int = 0) -> bool:
        return self._indicator.SignalSell(market, self, shift)

    def __repr__(self) -> str:
        return repr(self.data())
