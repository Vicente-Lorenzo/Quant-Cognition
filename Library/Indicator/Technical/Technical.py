from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, ClassVar, TYPE_CHECKING, Union

from typing_extensions import Self

from Library.Database.Dataframe import pl
from Library.Indicator.Indicator import IndicatorMode
from Library.Market.Series import SeriesAPI
from Library.Utility.Enumeration import EnumerationAPI

if TYPE_CHECKING:
    from Library.Market.Market import MarketAPI

class TechnicalType(EnumerationAPI):
    Baseline = 0
    Overlap = 1
    Momentum = 2
    Volume = 3
    Volatility = 4
    Pattern = 5
    Other = 6

@dataclass(frozen=True, kw_only=True)
class SlotAPI:

    name: str
    default: Any = None
    parser: Union[Callable, None] = None
    ladder: tuple = ()

    def cast(self, value: Any) -> Any:
        return self.parser(value) if self.parser is not None else value

    def revised(self, **changes) -> Self:
        return replace(self, **changes)

WINDOW = SlotAPI(name="window", default=14, ladder=((5, 100, 5), (-8, 8, 2), (-3, 3, 1)))
PERIOD = SlotAPI(name="window", default=14, ladder=((5, 50, 5), (-4, 4, 2), (-2, 2, 1)))
FAST = SlotAPI(name="fast_window", default=5, ladder=((2, 30, 2), (-4, 4, 1)))
SLOW = SlotAPI(name="slow_window", default=20, ladder=((10, 100, 5), (-8, 8, 2), (-3, 3, 1)))
MODE = SlotAPI(name="mode", default=IndicatorMode.Off, parser=IndicatorMode.parse)

class TechnicalAPI:

    Type: ClassVar[TechnicalType] = TechnicalType.Other
    Parameters: ClassVar[tuple] = ()

    @classmethod
    def admits(cls, values: dict) -> bool:
        return True

    @classmethod
    def compose(cls, name: str, config: list) -> TechnicalAPI:
        values = {slot.name: slot.cast(config[position] if len(config) > position else slot.default)
                  for position, slot in enumerate(cls.Parameters, start=1)}
        return cls(name=name, **values)

    def __init__(self, name: str, window: int, mode: IndicatorMode, **indicators) -> None:
        self.Name: str = name
        self.Mode: IndicatorMode = mode
        self.Result: SeriesAPI = SeriesAPI(self.Name)
        self._data_: Union[pl.DataFrame, None] = None
        self._composite_: bool = type(self).batch is TechnicalAPI.batch and type(self).stream is TechnicalAPI.stream
        self._indicators_: list = list(indicators.values())
        for k, v in indicators.items():
            setattr(self, k, v)
        self.Window: int = self._window_() or window

    def _window_(self) -> int:
        return max((ind.Window for ind in self._indicators_ if hasattr(ind, "Window")), default=0)

    def _extract_(self, market: MarketAPI) -> Union[pl.Series, pl.DataFrame]:
        return market.CloseTicks.Price.tail()

    def _pad_(self) -> pl.DataFrame:
        return pl.DataFrame({self.Name: pl.Series([None], dtype=pl.Float64)})

    def batch(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        return self._pad_()

    def stream(self, data: Union[pl.Series, pl.DataFrame]) -> pl.DataFrame:
        return self._pad_()

    def calculate(self, data: Union[pl.Series, pl.DataFrame], batch: bool = False) -> pl.DataFrame:
        return self.batch(data) if batch else self.stream(data)

    def init_data(self, market: MarketAPI) -> None:
        if not self._composite_:
            self._data_ = self.calculate(self._extract_(market), batch=True)
            self.Result.init_data(self._data_)
        for ind in self._indicators_:
            if hasattr(ind, "init_data"): ind.init_data(market)

    def update_data(self, market: MarketAPI) -> None:
        if not self._composite_:
            if self._data_ is None:
                self._data_ = self.calculate(self._extract_(market), batch=True)
            else:
                self._data_.extend(self.calculate(self._extract_(market), batch=False))
            self.Result.init_data(self._data_)
        for ind in self._indicators_:
            if hasattr(ind, "update_data"): ind.update_data(market)

    def update_offset(self, offset: int = 1) -> None:
        self.Result.update_offset(offset)
        for ind in self._indicators_:
            if hasattr(ind, "update_offset"): ind.update_offset(offset)

    def filter_buy(self, market: MarketAPI) -> bool:
        return False

    def filter_sell(self, market: MarketAPI) -> bool:
        return False

    def signal_buy(self, market: MarketAPI) -> bool:
        return False

    def signal_sell(self, market: MarketAPI) -> bool:
        return False