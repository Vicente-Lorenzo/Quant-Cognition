from __future__ import annotations

from typing import Union, TYPE_CHECKING
from Library.Database.Dataframe import pl
from Library.Indicator.Base import BaseIndicatorAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI
    from Library.Indicator.Configuration import IndicatorConfigurationAPI

class LegacyIndicatorAPI(BaseIndicatorAPI):

    def __init__(self, indicator_name: str, parameters: Union[list, None] = None) -> None:
        super().__init__()
        from Library.Indicator.Indicators import IndicatorsAPI
        self._indicator_: IndicatorConfigurationAPI = getattr(IndicatorsAPI, indicator_name)
        self._parameters_: dict = dict(zip(self._indicator_.Parameter.keys(), parameters))
        self._sids_ = [f"{indicator_name}_{'_'.join(map(str, parameters)) + '_' if parameters else ''}{output}" for output in self._indicator_.Output]

    def calculate(self, market: MarketAPI, window: Union[int, None] = None) -> pl.DataFrame:
        input_series = [tseries.tail(window) if window else tseries.dataframe() for tseries in self._indicator_.Input(market)]
        df = pl.DataFrame(self._indicator_.Function(input_series, **self._parameters_))
        df.columns = self._sids_
        return df

    def filter_buy(self, market: Union[MarketAPI, None] = None, shift: int = 0) -> bool:
        return self._indicator_.FilterBuy(market, self, shift)

    def filter_sell(self, market: Union[MarketAPI, None] = None, shift: int = 0) -> bool:
        return self._indicator_.FilterSell(market, self, shift)

    def signal_buy(self, market: Union[MarketAPI, None] = None, shift: int = 0) -> bool:
        return self._indicator_.SignalBuy(market, self, shift)

    def signal_sell(self, market: Union[MarketAPI, None] = None, shift: int = 0) -> bool:
        return self._indicator_.SignalSell(market, self, shift)