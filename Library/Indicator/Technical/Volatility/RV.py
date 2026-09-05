from __future__ import annotations

import math
from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import MODE, PERIOD, TechnicalAPI, TechnicalType

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class RealizedVolatilityAPI(TechnicalAPI):

    Type = TechnicalType.Volatility
    Parameters = (PERIOD.revised(default=16), MODE)

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        log_returns = (data / data.shift(1)).log().fill_null(0.0)
        variance = log_returns.pow(2).ewm_mean(alpha=1.0 / self.Window, adjust=False)
        rv = variance.sqrt()
        nulls = [None] * self.Window
        if len(rv) > self.Window:
            rv = pl.Series(nulls + rv.to_list()[self.Window:])
        else:
            rv = pl.Series([None] * len(rv), dtype=pl.Float64)
        return pl.DataFrame({self.Name: rv})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        prev_rv = self.Result.last()
        new_close = (data[-1] if len(data) > 0 else None)
        prev_close = (data[-2] if len(data) > 1 else None)
        if new_close is None or prev_close is None or new_close <= 0 or prev_close <= 0: return self._pad_()
        log_return = math.log(new_close / prev_close)
        if prev_rv is None:
            if len(data) < self.Window + 1: return self._pad_()
            log_returns = (data / data.shift(1)).log().fill_null(0.0)
            variance = log_returns.pow(2).ewm_mean(alpha=1.0 / self.Window, adjust=False)
            return pl.DataFrame({self.Name: pl.Series([math.sqrt(float(variance[-1]))], dtype=pl.Float64)})
        variance = (prev_rv * prev_rv * (self.Window - 1) + log_return * log_return) / self.Window
        return pl.DataFrame({self.Name: pl.Series([math.sqrt(variance)], dtype=pl.Float64)})

    def filter_buy(self, market: MarketAPI) -> bool:
        return True

    def filter_sell(self, market: MarketAPI) -> bool:
        return True

    def signal_buy(self, market: MarketAPI) -> bool:
        return False

    def signal_sell(self, market: MarketAPI) -> bool:
        return False