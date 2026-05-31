from __future__ import annotations

from Library.Indicator.Technical.Technical import TechnicalAPI, TechnicalType
from Library.Indicator.Indicator import IndicatorMode

class FalseFalseAPI(TechnicalAPI):

    Type = TechnicalType.Other

    def __init__(self, name: str, mode: IndicatorMode) -> None:
        super().__init__(name=name, window=None, mode=mode)