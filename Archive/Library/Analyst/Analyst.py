import math
from typing import Union

from Library.Database.Dataframe import pl
from Library.Database import DatabaseAPI
from Library.Utility import BarAPI
from Library.Parameters import Parameters

from Library.Analyst import MARGIN, MarketAPI, IndicatorAPI

class AnalystAPI:

    def __init__(self, analyst_management: Parameters):
        self.AnalystManagement: Parameters = analyst_management
        self.Window: int = MARGIN
        self.Market: MarketAPI = MarketAPI()

        self._indicators: list[IndicatorAPI] = []
        analyst_management = analyst_management if analyst_management else {}
        for indicator_name, indicator_configuration in analyst_management.items() or {}:
            indicator_function, *indicator_parameters = indicator_configuration
            indicator = IndicatorAPI(indicator=indicator_function, parameters=indicator_parameters)
            setattr(self, indicator_name, indicator)
            self._indicators.append(indicator)
            indicator_max = max(indicator_parameters) if indicator_parameters else 0
            self.Window = math.ceil(max(self.Window, indicator_max + MARGIN))

    def data(self) -> pl.DataFrame:
        result = pl.DataFrame()
        result = result.hstack(self.Market.data())
        for indicator in self._indicators:
            result = result.hstack(indicator.data())
        return result

    def head(self, n: Union[int, None] = None) -> pl.DataFrame:
        return self.data().head(n)

    def tail(self, n: Union[int, None] = None) -> pl.DataFrame:
        return self.data().tail(n)

    def init_market_data(self, data: Union[pl.DataFrame, list[BarAPI]]) -> None:
        data_df = DatabaseAPI.format_market_data(data)
        self.Market.init_data(data_df)
        for indicator in self._indicators:
            indicator.init_data(self.Market)

    def update_market_data(self, data: BarAPI) -> None:
        data_df = DatabaseAPI.format_market_data(data)
        self.Market.update_data(data_df)
        for indicator in self._indicators:
            indicator.update_data(self.Market, self.Window)

    def update_market_offset(self, offset: int) -> None:
        self.Market.update_offset(offset)
        for indicator in self._indicators:
            indicator.update_offset(offset)

    def __repr__(self) -> str:
        return repr(self.data())