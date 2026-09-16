from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Query import QueryAPI
from Library.Market.Price import PriceMode
from Library.Market.Series import SeriesAPI

if TYPE_CHECKING:
    from Library.Database.Database import DatabaseAPI
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
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        self.Ticks = SeriesAPI("", multiple=True, mode=self.mode)
        self.GapTicks = SeriesAPI("GapTick", multiple=True, mode=self.mode)
        self.OpenTicks = SeriesAPI("OpenTick", multiple=True, mode=self.mode)
        self.HighTicks = SeriesAPI("HighTick", multiple=True, mode=self.mode)
        self.LowTicks = SeriesAPI("LowTick", multiple=True, mode=self.mode)
        self.CloseTicks = SeriesAPI("CloseTick", multiple=True, mode=self.mode)
        self.Volume = SeriesAPI("Volume", multiple=False, mode=self.mode)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    @staticmethod
    def _project_(alias: str, name: str) -> str:
        from Library.Market.Tick import TickAPI
        columns = (TickAPI.ID.UID, TickAPI.ID.Timestamp, TickAPI.ID.Security, TickAPI.ID.Ask, TickAPI.ID.Mid, TickAPI.ID.Bid, TickAPI.ID.AskBaseConversion, TickAPI.ID.BidBaseConversion, TickAPI.ID.AskQuoteConversion, TickAPI.ID.BidQuoteConversion, TickAPI.ID.Volume)
        return ", ".join(f'{alias}."{column}" AS "{name}.{column}"' for column in columns)

    def _bind_(self, bar: bool) -> None:
        if bar:
            self.GapTicks.init_data(self._data_)
            self.OpenTicks.init_data(self._data_)
            self.HighTicks.init_data(self._data_)
            self.LowTicks.init_data(self._data_)
            self.CloseTicks.init_data(self._data_)
            self.Volume.init_data(self._data_)
        else:
            self.Ticks.init_data(self._data_)

    @staticmethod
    def pull_ticks(db: DatabaseAPI, security: int, start: datetime, stop: datetime, columns: Union[list[str], None] = None) -> pl.DataFrame:
        from Library.Market.Tick import TickAPI
        lo, hi = TickAPI.encode(security, start), TickAPI.encode(security, stop)
        projection = ", ".join(f'"{column}"' for column in columns) if columns else "*"
        sql = f'''
        SELECT {projection} FROM "{TickAPI.Schema}"."{TickAPI.Table}"
        WHERE "{TickAPI.ID.UID}" BETWEEN :lo: AND :hi:
        ORDER BY "{TickAPI.ID.UID}"
        '''
        return db.executeone(QueryAPI(sql), lo=lo, hi=hi, schema=TickAPI.Schema, table=TickAPI.Table).fetchall(legacy=False)

    @staticmethod
    def count_ticks(db: DatabaseAPI, security: int, start: datetime, stop: datetime) -> int:
        from Library.Market.Tick import TickAPI
        lo, hi = TickAPI.encode(security, start), TickAPI.encode(security, stop)
        sql = f'SELECT COUNT(*) AS "Count" FROM "{TickAPI.Schema}"."{TickAPI.Table}" WHERE "{TickAPI.ID.UID}" BETWEEN :lo: AND :hi:'
        df = db.executeone(QueryAPI(sql), lo=lo, hi=hi, schema=TickAPI.Schema, table=TickAPI.Table).fetchall(legacy=False)
        return int(df["Count"][0]) if df.height else 0

    @staticmethod
    def last_tick_uid(db: DatabaseAPI, security: int, start: datetime, stop: datetime) -> int:
        from Library.Market.Tick import TickAPI
        lo, hi = TickAPI.encode(security, start), TickAPI.encode(security, stop)
        sql = f'SELECT MAX("{TickAPI.ID.UID}") AS "Token" FROM "{TickAPI.Schema}"."{TickAPI.Table}" WHERE "{TickAPI.ID.UID}" BETWEEN :lo: AND :hi:'
        df = db.executeone(QueryAPI(sql), lo=lo, hi=hi, schema=TickAPI.Schema, table=TickAPI.Table).fetchall(legacy=False)
        return int(df["Token"][0]) if df.height and df["Token"][0] is not None else 0

    @staticmethod
    def push_ticks(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Market.Tick import TickAPI
        if isinstance(data, pl.DataFrame): data = TickAPI.encode(data)
        db.upsert(schema=TickAPI.Schema, table=TickAPI.Table, data=data, key=[str(TickAPI.ID.UID)])

    @staticmethod
    def pull_bars(db: DatabaseAPI, security: int, timeframe: str, start: Union[datetime, None] = None, stop: Union[datetime, None] = None, limit: Union[int, None] = None) -> pl.DataFrame:
        from Library.Market.Bar import BarAPI
        from Library.Market.Tick import TickAPI
        select = f'''
        SELECT b."{BarAPI.ID.Timestamp}", b."{BarAPI.ID.Security}", b."{BarAPI.ID.Timeframe}",
               b."{BarAPI.ID.GapTick}", b."{BarAPI.ID.OpenTick}", b."{BarAPI.ID.HighTick}", b."{BarAPI.ID.LowTick}", b."{BarAPI.ID.CloseTick}",
               b."{BarAPI.ID.Volume}", b."{BarAPI.ID.UpdatedBy}", b."{BarAPI.ID.UpdatedAt}",
               {MarketAPI._project_("g", BarAPI.ID.GapTick)},
               {MarketAPI._project_("o", BarAPI.ID.OpenTick)},
               {MarketAPI._project_("h", BarAPI.ID.HighTick)},
               {MarketAPI._project_("l", BarAPI.ID.LowTick)},
               {MarketAPI._project_("c", BarAPI.ID.CloseTick)}
        FROM "{BarAPI.Schema}"."{BarAPI.Table}" b
        LEFT JOIN "{TickAPI.Schema}"."{TickAPI.Table}" g ON b."{BarAPI.ID.GapTick}"   = g."{TickAPI.ID.UID}"
        LEFT JOIN "{TickAPI.Schema}"."{TickAPI.Table}" o ON b."{BarAPI.ID.OpenTick}"  = o."{TickAPI.ID.UID}"
        LEFT JOIN "{TickAPI.Schema}"."{TickAPI.Table}" h ON b."{BarAPI.ID.HighTick}"  = h."{TickAPI.ID.UID}"
        LEFT JOIN "{TickAPI.Schema}"."{TickAPI.Table}" l ON b."{BarAPI.ID.LowTick}"   = l."{TickAPI.ID.UID}"
        LEFT JOIN "{TickAPI.Schema}"."{TickAPI.Table}" c ON b."{BarAPI.ID.CloseTick}" = c."{TickAPI.ID.UID}"
        '''
        if limit is not None:
            sql = select + f'''
        WHERE b."{BarAPI.ID.Security}" = :security: AND b."{BarAPI.ID.Timeframe}" = :timeframe:
          AND b."{BarAPI.ID.Timestamp}" < :stop:
        ORDER BY b."{BarAPI.ID.Timestamp}" DESC
        LIMIT {int(limit)}
        '''
            df = db.executeone(QueryAPI(sql), security=security, timeframe=timeframe, stop=stop, schema=BarAPI.Schema, table=BarAPI.Table).fetchall(legacy=False)
            return df.reverse() if df.height else df
        sql = select + f'''
        WHERE b."{BarAPI.ID.Security}" = :security: AND b."{BarAPI.ID.Timeframe}" = :timeframe:
          AND b."{BarAPI.ID.Timestamp}" BETWEEN :start: AND :stop:
        ORDER BY b."{BarAPI.ID.Timestamp}"
        '''
        return db.executeone(QueryAPI(sql), security=security, timeframe=timeframe, start=start, stop=stop, schema=BarAPI.Schema, table=BarAPI.Table).fetchall(legacy=False)

    @staticmethod
    def push_bars(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Market.Bar import BarAPI
        db.upsert(schema=BarAPI.Schema, table=BarAPI.Table, data=data, key=[str(BarAPI.ID.Timestamp), str(BarAPI.ID.Security), str(BarAPI.ID.Timeframe)])

    def dataframe(self) -> pl.DataFrame:
        if self._data_ is None: return pl.DataFrame()
        return self._data_

    def head(self, n: Union[int, None] = None) -> pl.DataFrame:
        return self.dataframe().head(n)

    def tail(self, n: Union[int, None] = None) -> pl.DataFrame:
        return self.dataframe().tail(n)

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
        else:
            self._data_.extend(df)
        self._bind_(bar)

    def update_offset(self, offset: int = 1) -> None:
        self._offset_ = offset
        self.Ticks.update_offset(offset)
        self.GapTicks.update_offset(offset)
        self.OpenTicks.update_offset(offset)
        self.HighTicks.update_offset(offset)
        self.LowTicks.update_offset(offset)
        self.CloseTicks.update_offset(offset)
        self.Volume.update_offset(offset)

    def __repr__(self) -> str:
        return repr(self.dataframe())