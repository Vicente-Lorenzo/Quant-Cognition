from __future__ import annotations

from typing import TYPE_CHECKING

from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType
from Library.Indicator.Indicator import IndicatorMode

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class FalseTrueAPI(TechnicalAPI):

    Type = TechnicalType.Other

    def __init__(self, name: str, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=None, mode=mode)

    def filter_buy(self, market: MarketAPI) -> bool:
        return True

    def filter_sell(self, market: MarketAPI) -> bool:
        return True

    def signal_buy(self, market: MarketAPI) -> bool:
        return False

    def signal_sell(self, market: MarketAPI) -> bool:
        return False