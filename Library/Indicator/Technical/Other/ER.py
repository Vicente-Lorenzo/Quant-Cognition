from __future__ import annotations

from typing import TYPE_CHECKING, Union

from Library.Database.Dataframe import pl
from Library.Indicator.Technical.Technical import MODE, PERIOD, TechnicalAPI, TechnicalType

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class EfficiencyRatioAPI(TechnicalAPI):

    Type = TechnicalType.Other
    Parameters = (PERIOD.revised(default=24), MODE)

    def _extract_(self, market: MarketAPI) -> Union[pl.Series, pl.DataFrame]:
        return market.CloseTicks.Price.tail()

    def _ratio_(self, data: Union[pl.Series, pl.DataFrame]) -> Union[float, None]:
        window = data.tail(self.Window + 1)
        if len(window) < self.Window + 1: return None
        direction = abs(float(window[-1]) - float(window[0]))
        volatility = float(window.diff().abs().sum())
        return direction / volatility if volatility > 0.0 else 0.0

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        if data.is_empty(): return self._pad_()
        moves = data.diff().abs()
        direction = (data - data.shift(self.Window)).abs()
        volatility = moves.rolling_sum(window_size=self.Window)
        ratio = pl.Series([
            None if d is None or v is None else (d / v if v > 0.0 else 0.0)
            for d, v in zip(direction.to_list(), volatility.to_list())
        ], dtype=pl.Float64)
        return pl.DataFrame({self.Name: ratio})

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        ratio = self._ratio_(data)
        if ratio is None: return self._pad_()
        return pl.DataFrame({self.Name: pl.Series([ratio], dtype=pl.Float64)})

    def filter_buy(self, market: MarketAPI) -> bool:
        return True

    def filter_sell(self, market: MarketAPI) -> bool:
        return True

    def signal_buy(self, market: MarketAPI) -> bool:
        return False

    def signal_sell(self, market: MarketAPI) -> bool:
        return False