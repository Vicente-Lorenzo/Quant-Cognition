from __future__ import annotations

import math
from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import MODE, PERIOD, TechnicalAPI, TechnicalType

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class RateOfChangeAPI(TechnicalAPI):

    Type = TechnicalType.Momentum
    Parameters = (PERIOD.revised(default=12), MODE)

    def _extract_(self, market: MarketAPI) -> Union[pl.Series, pl.DataFrame]:
        return market.CloseTicks.Price.tail()

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        roc = (data / data.shift(self.Window)).log()
        return pl.DataFrame({self.Name: roc})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        new_close = (data[-1] if len(data) > 0 else None)
        old_close = (data[-(self.Window + 1)] if len(data) > self.Window else None)
        if new_close is None or old_close is None or new_close <= 0 or old_close <= 0: return self._pad_()
        return pl.DataFrame({self.Name: pl.Series([math.log(new_close / old_close)], dtype=pl.Float64)})

    def filter_buy(self, market: MarketAPI) -> bool:
        return True

    def filter_sell(self, market: MarketAPI) -> bool:
        return True

    def signal_buy(self, market: MarketAPI) -> bool:
        return False

    def signal_sell(self, market: MarketAPI) -> bool:
        return False