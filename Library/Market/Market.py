from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Market.Price import PriceMode
from Library.Market.Series import SeriesAPI
from Library.Market.Tape import TapeAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Datetime import datetime_to_epoch
from Library.Utility.Typing import MISSING, Missing

if TYPE_CHECKING:
    from Library.Database.Database import DatabaseAPI
    from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
    from Library.Market.Tick import TickAPI
    from Library.Market.Bar import BarAPI

@dataclass(kw_only=True)
class MarketAPI(DatapointAPI):

    Schema: ClassVar[str] = "Market"
    Table: ClassVar[str] = "Market"

    mode: PriceMode = field(default=PriceMode.Bid, repr=False)
    _offset_: int = field(default=1, init=False)
    _data_: Union[pl.DataFrame, None] = field(default=None, init=False)

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autoload: bool,
                      autooverload: bool,
                      autosave: bool) -> None:
        self.Ticks = SeriesAPI("", multiple=True, mode=self.mode)
        self.GapPoints = SeriesAPI("GapPoint", point=True, mode=self.mode)
        self.OpenPoints = SeriesAPI("OpenPoint", point=True, mode=self.mode)
        self.HighPoints = SeriesAPI("HighPoint", point=True, mode=self.mode)
        self.LowPoints = SeriesAPI("LowPoint", point=True, mode=self.mode)
        self.ClosePoints = SeriesAPI("ClosePoint", point=True, mode=self.mode)
        self.Volume = SeriesAPI("Volume", multiple=False, mode=self.mode)
        super().__post_init__(db=db, migrate=migrate, autoload=autoload, autooverload=autooverload, autosave=autosave)

    def _bind_(self, bar: bool) -> None:
        if bar:
            self.GapPoints.init_data(self._data_)
            self.OpenPoints.init_data(self._data_)
            self.HighPoints.init_data(self._data_)
            self.LowPoints.init_data(self._data_)
            self.ClosePoints.init_data(self._data_)
            self.Volume.init_data(self._data_)
        else:
            self.Ticks.init_data(self._data_)

    @staticmethod
    def pull_ticks(db: PostgresDatabaseAPI, security: int, start: datetime, stop: datetime) -> pl.DataFrame:
        return TapeAPI.read(db, security, start, stop).frame()

    @staticmethod
    def pull_bars(db: PostgresDatabaseAPI, security: int, timeframe: Union[str, TimeframeAPI], start: Union[datetime, Missing] = MISSING, stop: Union[datetime, Missing] = MISSING, limit: Union[int, Missing] = MISSING) -> pl.DataFrame:
        timeframe = timeframe if isinstance(timeframe, TimeframeAPI) else TimeframeAPI(UID=timeframe)
        if limit is not MISSING:
            tape, bars = TapeAPI.before(db, security, timeframe, stop, int(limit))
        else:
            tape, bars = TapeAPI.span(db, security, timeframe, start, stop)
            bars = bars.filter(pl.col("Timestamp") >= datetime_to_epoch(start))
        return tape.materialize(bars, timeframe)

    def dataframe(self) -> pl.DataFrame:
        if self._data_ is None: return pl.DataFrame()
        return self._data_

    def head(self, n: int = MISSING) -> pl.DataFrame:
        return self.dataframe().head(n) if n is not MISSING else self.dataframe()

    def tail(self, n: int = MISSING) -> pl.DataFrame:
        return self.dataframe().tail(n) if n is not MISSING else self.dataframe()

    def last(self, shift: int = 0) -> pl.DataFrame:
        return self.dataframe()[-(self._offset_ + shift)]

    def init_data(self, data: pl.DataFrame) -> None:
        from Library.Market.Bar import BarAPI
        self._data_ = data.rechunk()
        self._bind_(str(BarAPI.ID.Timeframe) in data.columns)

    def update_data(self, data: Union[TickAPI, BarAPI, pl.DataFrame]) -> None:
        from Library.Market.Bar import BarAPI
        if isinstance(data, pl.DataFrame):
            df, bar = data, str(BarAPI.ID.Timeframe) in data.columns
        else:
            df, bar = pl.DataFrame([data.dict(flatten=True)], strict=False), isinstance(data, BarAPI)
        if self._data_ is None or self._data_.width == 0:
            self._data_ = df.rechunk()
            self._bind_(bar)
        else:
            self._data_.extend(df)

    def update_offset(self, offset: int = 1) -> None:
        self._offset_ = offset
        self.Ticks.update_offset(offset)
        self.GapPoints.update_offset(offset)
        self.OpenPoints.update_offset(offset)
        self.HighPoints.update_offset(offset)
        self.LowPoints.update_offset(offset)
        self.ClosePoints.update_offset(offset)
        self.Volume.update_offset(offset)

    def __repr__(self) -> str:
        return repr(self.dataframe())