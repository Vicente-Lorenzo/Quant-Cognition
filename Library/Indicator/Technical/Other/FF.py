from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Indicator.Indicator import IndicatorMode
from Library.Indicator.Technical.Technical import MODE, TechnicalAPI, TechnicalType

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class FalseFalseAPI(TechnicalAPI):

    Type = TechnicalType.Other
    Parameters = (MODE,)

    def __init__(self, name: str, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=0, mode=mode)

    def init_data(self, market: MarketAPI) -> None:
        pass

    def update_data(self, market: MarketAPI) -> None:
        pass

    def update_offset(self, offset: int = 1) -> None:
        pass

    def filter_buy(self, market: MarketAPI) -> bool:
        return False

    def filter_sell(self, market: MarketAPI) -> bool:
        return False

    def signal_buy(self, market: MarketAPI) -> bool:
        return False

    def signal_sell(self, market: MarketAPI) -> bool:
        return False