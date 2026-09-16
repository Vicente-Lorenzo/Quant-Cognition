from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from importlib import import_module
from typing import Any, TYPE_CHECKING, Union

from Library.Utility.Enumeration import EnumerationAPI
from Library.Utility.Path import inspect_module

if TYPE_CHECKING:
    from Library.Indicator.Technical.Technical import TechnicalAPI
    from Library.Indicator.Fundamental.Fundamental import FundamentalAPI
    from Library.Indicator.Sentimental.Sentimental import SentimentalAPI
    from Library.Market.Market import MarketAPI

class IndicatorMode(EnumerationAPI):

    Off = 0
    Filter = 1
    Signal = 2

class CompositeAPI:

    def __init__(self, name: str, window: int, mode: IndicatorMode, **indicators) -> None:
        self.Name: str = name
        self.Mode: IndicatorMode = mode
        self._indicators_: list = list(indicators.values())
        for k, v in indicators.items():
            setattr(self, k, v)
        self.Window: int = self._window_() or window

    def _window_(self) -> int:
        return max((ind.Window for ind in self._indicators_ if hasattr(ind, "Window")), default=0)

    def init_data(self, market: MarketAPI) -> None:
        for ind in self._indicators_:
            if hasattr(ind, "init_data"): ind.init_data(market)

    def update_data(self, market: MarketAPI) -> None:
        for ind in self._indicators_:
            if hasattr(ind, "update_data"): ind.update_data(market)

    def update_offset(self, offset: int = 1) -> None:
        for ind in self._indicators_:
            if hasattr(ind, "update_offset"): ind.update_offset(offset)

@dataclass
class IndicatorAPI:

    Technical: TechnicalAPI = None
    Fundamental: FundamentalAPI = None
    Sentimental: SentimentalAPI = None

    def __init__(self, technical: Union[dict, None] = None, fundamental: Union[dict, None] = None, sentimental: Union[dict, None] = None):
        self.Technical = self.parse_technical(technical)
        self.Fundamental = self.parse_fundamental(fundamental)
        self.Sentimental = self.parse_sentimental(sentimental)

    @staticmethod
    @cache
    def catalog() -> dict:
        technical = inspect_module(__file__) / "Technical"
        return {path.stem: f"{__package__}.Technical.{path.parent.name}.{path.stem}"
                for path in sorted(technical.glob("*/*.py")) if not path.stem.startswith("_")}

    @staticmethod
    @cache
    def _resolve_(module: str) -> Union[type, None]:
        from Library.Indicator.Technical.Technical import TechnicalAPI
        imported = import_module(module)
        return next((member for member in vars(imported).values()
                     if isinstance(member, type) and issubclass(member, TechnicalAPI) and member.__module__ == module), None)

    @staticmethod
    def _parse_(api: type, parameters: Union[dict, None]) -> CompositeAPI:
        return api(name=api.__name__.removesuffix("API"), window=0, mode=IndicatorMode.Off)

    @classmethod
    def resolve_technical(cls, acronym: Any) -> Union[type, None]:
        module = cls.catalog().get(acronym) if isinstance(acronym, str) else None
        return cls._resolve_(module) if module is not None else None

    @classmethod
    def parse_technical(cls, parameters: Union[dict, None]) -> TechnicalAPI:
        from Library.Indicator.Technical.Technical import TechnicalAPI
        if not parameters:
            return TechnicalAPI(name="Technical", window=0, mode=IndicatorMode.Off)
        indicators = {}
        for name, config in parameters.items():
            if not config: continue
            indicator = cls.resolve_technical(config[0])
            if indicator is None: continue
            indicators[name] = indicator.compose(name, config)
        return TechnicalAPI(name="Technical", window=0, mode=IndicatorMode.Off, **indicators)

    @classmethod
    def parse_fundamental(cls, parameters: Union[dict, None]) -> FundamentalAPI:
        from Library.Indicator.Fundamental.Fundamental import FundamentalAPI
        return cls._parse_(FundamentalAPI, parameters)

    @classmethod
    def parse_sentimental(cls, parameters: Union[dict, None]) -> SentimentalAPI:
        from Library.Indicator.Sentimental.Sentimental import SentimentalAPI
        return cls._parse_(SentimentalAPI, parameters)

    def init_data(self, market: MarketAPI) -> None:
        if self.Technical: self.Technical.init_data(market)
        if self.Fundamental: self.Fundamental.init_data(market)
        if self.Sentimental: self.Sentimental.init_data(market)

    def update_data(self, market: MarketAPI) -> None:
        if self.Technical: self.Technical.update_data(market)
        if self.Fundamental: self.Fundamental.update_data(market)
        if self.Sentimental: self.Sentimental.update_data(market)