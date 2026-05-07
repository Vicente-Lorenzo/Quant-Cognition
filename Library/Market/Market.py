from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field
from collections.abc import Sequence
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Query import QueryAPI
from Library.Market.Series import SeriesAPI

if TYPE_CHECKING: 
    from Library.Database.Database import DatabaseAPI
    from Library.Market.Tick import TickAPI
    from Library.Market.Bar import BarAPI

@dataclass(kw_only=True)
class MarketAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Market"
    Table: ClassVar[str] = "Market"

    _offset_: int = field(default=1, init=False)
    _data_: Union[pl.DataFrame, None] = field(default=None, init=False)

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        self.Ticks = SeriesAPI("", multiple=True)
        self.GapTicks = SeriesAPI("GapTick", multiple=True)
        self.OpenTicks = SeriesAPI("OpenTick", multiple=True)
        self.HighTicks = SeriesAPI("HighTick", multiple=True)
        self.LowTicks = SeriesAPI("LowTick", multiple=True)
        self.CloseTicks = SeriesAPI("CloseTick", multiple=True)
        self.Volume = SeriesAPI("Volume", multiple=False)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    @staticmethod
    def load_ticks(data: Union[TickAPI, Sequence[TickAPI]]) -> None:
        if isinstance(data, (list, tuple)):
            for tick in data: tick.load()
        else:
            data.load()

    @staticmethod
    def save_ticks(data: Union[TickAPI, Sequence[TickAPI]], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for tick in data: tick.save(by=by)
        else:
            data.save(by=by)

    @staticmethod
    def pull_ticks(db: DatabaseAPI, security: int, start: datetime, stop: datetime) -> pl.DataFrame:
        from Library.Market.Tick import TickAPI
        sql = f'''
        SELECT * FROM "{TickAPI.Schema}"."{TickAPI.Table}"
        WHERE "{TickAPI.ID.Security}" = :security: AND "{TickAPI.ID.Timestamp}" BETWEEN :start: AND :stop:
        ORDER BY "{TickAPI.ID.Timestamp}"
        '''
        df = db.executeone(QueryAPI(sql), security=security, start=start, stop=stop, schema=TickAPI.Schema, table=TickAPI.Table).fetchall(legacy=False)
        return df

    @staticmethod
    def push_ticks(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Market.Tick import TickAPI
        db.upsert(schema=TickAPI.Schema, table=TickAPI.Table, data=data, key=[str(TickAPI.ID.Timestamp), str(TickAPI.ID.Security)], exclude=["CreatedAt", "CreatedBy"])

    @staticmethod
    def load_bars(data: Union[BarAPI, Sequence[BarAPI]]) -> None:
        if isinstance(data, (list, tuple)):
            for bar in data: bar.load()
        else:
            data.load()

    @staticmethod
    def save_bars(data: Union[BarAPI, Sequence[BarAPI]], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for bar in data: bar.save(by=by)
        else:
            data.save(by=by)

    @staticmethod
    def pull_bars(db: DatabaseAPI, security: int, timeframe: str, start: datetime, stop: datetime) -> pl.DataFrame:
        from Library.Market.Bar import BarAPI
        from Library.Market.Tick import TickAPI
        sql = f'''
        SELECT b."{BarAPI.ID.UID}", b."{BarAPI.ID.Timestamp}", b."{BarAPI.ID.Security}", b."{BarAPI.ID.Timeframe}",
               b."{BarAPI.ID.GapTick}", b."{BarAPI.ID.OpenTick}", b."{BarAPI.ID.HighTick}", b."{BarAPI.ID.LowTick}", b."{BarAPI.ID.CloseTick}",
               b."{BarAPI.ID.Volume}", b."CreatedAt", b."CreatedBy", b."UpdatedAt", b."UpdatedBy",
               g."{TickAPI.ID.UID}" AS "{BarAPI.OID.GapTick.UID}", g."{TickAPI.ID.Timestamp}" AS "{BarAPI.OID.GapTick.Timestamp}", g."{TickAPI.ID.Security}" AS "{BarAPI.OID.GapTick.Security}",
               g."{TickAPI.ID.Ask}" AS "{BarAPI.OID.GapTick.Ask}", g."{TickAPI.ID.Bid}" AS "{BarAPI.OID.GapTick.Bid}",
               g."{TickAPI.ID.AskBaseConversion}" AS "{BarAPI.OID.GapTick.AskBaseConversion}", g."{TickAPI.ID.BidBaseConversion}" AS "{BarAPI.OID.GapTick.BidBaseConversion}",
               g."{TickAPI.ID.AskQuoteConversion}" AS "{BarAPI.OID.GapTick.AskQuoteConversion}", g."{TickAPI.ID.BidQuoteConversion}" AS "{BarAPI.OID.GapTick.BidQuoteConversion}",
               g."{TickAPI.ID.Volume}" AS "{BarAPI.OID.GapTick.Volume}",
               g."CreatedAt" AS "{BarAPI.OID.GapTick}.CreatedAt", g."CreatedBy" AS "{BarAPI.OID.GapTick}.CreatedBy",
               g."UpdatedAt" AS "{BarAPI.OID.GapTick}.UpdatedAt", g."UpdatedBy" AS "{BarAPI.OID.GapTick}.UpdatedBy",
               o."{TickAPI.ID.UID}" AS "{BarAPI.OID.OpenTick.UID}", o."{TickAPI.ID.Timestamp}" AS "{BarAPI.OID.OpenTick.Timestamp}", o."{TickAPI.ID.Security}" AS "{BarAPI.OID.OpenTick.Security}",
               o."{TickAPI.ID.Ask}" AS "{BarAPI.OID.OpenTick.Ask}", o."{TickAPI.ID.Bid}" AS "{BarAPI.OID.OpenTick.Bid}",
               o."{TickAPI.ID.AskBaseConversion}" AS "{BarAPI.OID.OpenTick.AskBaseConversion}", o."{TickAPI.ID.BidBaseConversion}" AS "{BarAPI.OID.OpenTick.BidBaseConversion}",
               o."{TickAPI.ID.AskQuoteConversion}" AS "{BarAPI.OID.OpenTick.AskQuoteConversion}", o."{TickAPI.ID.BidQuoteConversion}" AS "{BarAPI.OID.OpenTick.BidQuoteConversion}",
               o."{TickAPI.ID.Volume}" AS "{BarAPI.OID.OpenTick.Volume}",
               o."CreatedAt" AS "{BarAPI.OID.OpenTick}.CreatedAt", o."CreatedBy" AS "{BarAPI.OID.OpenTick}.CreatedBy",
               o."UpdatedAt" AS "{BarAPI.OID.OpenTick}.UpdatedAt", o."UpdatedBy" AS "{BarAPI.OID.OpenTick}.UpdatedBy",
               h."{TickAPI.ID.UID}" AS "{BarAPI.OID.HighTick.UID}", h."{TickAPI.ID.Timestamp}" AS "{BarAPI.OID.HighTick.Timestamp}", h."{TickAPI.ID.Security}" AS "{BarAPI.OID.HighTick.Security}",
               h."{TickAPI.ID.Ask}" AS "{BarAPI.OID.HighTick.Ask}", h."{TickAPI.ID.Bid}" AS "{BarAPI.OID.HighTick.Bid}",
               h."{TickAPI.ID.AskBaseConversion}" AS "{BarAPI.OID.HighTick.AskBaseConversion}", h."{TickAPI.ID.BidBaseConversion}" AS "{BarAPI.OID.HighTick.BidBaseConversion}",
               h."{TickAPI.ID.AskQuoteConversion}" AS "{BarAPI.OID.HighTick.AskQuoteConversion}", h."{TickAPI.ID.BidQuoteConversion}" AS "{BarAPI.OID.HighTick.BidQuoteConversion}",
               h."{TickAPI.ID.Volume}" AS "{BarAPI.OID.HighTick.Volume}",
               h."CreatedAt" AS "{BarAPI.OID.HighTick}.CreatedAt", h."CreatedBy" AS "{BarAPI.OID.HighTick}.CreatedBy",
               h."UpdatedAt" AS "{BarAPI.OID.HighTick}.UpdatedAt", h."UpdatedBy" AS "{BarAPI.OID.HighTick}.UpdatedBy",
               l."{TickAPI.ID.UID}" AS "{BarAPI.OID.LowTick.UID}", l."{TickAPI.ID.Timestamp}" AS "{BarAPI.OID.LowTick.Timestamp}", l."{TickAPI.ID.Security}" AS "{BarAPI.OID.LowTick.Security}",
               l."{TickAPI.ID.Ask}" AS "{BarAPI.OID.LowTick.Ask}", l."{TickAPI.ID.Bid}" AS "{BarAPI.OID.LowTick.Bid}",
               l."{TickAPI.ID.AskBaseConversion}" AS "{BarAPI.OID.LowTick.AskBaseConversion}", l."{TickAPI.ID.BidBaseConversion}" AS "{BarAPI.OID.LowTick.BidBaseConversion}",
               l."{TickAPI.ID.AskQuoteConversion}" AS "{BarAPI.OID.LowTick.AskQuoteConversion}", l."{TickAPI.ID.BidQuoteConversion}" AS "{BarAPI.OID.LowTick.BidQuoteConversion}",
               l."{TickAPI.ID.Volume}" AS "{BarAPI.OID.LowTick.Volume}",
               l."CreatedAt" AS "{BarAPI.OID.LowTick}.CreatedAt", l."CreatedBy" AS "{BarAPI.OID.LowTick}.CreatedBy",
               l."UpdatedAt" AS "{BarAPI.OID.LowTick}.UpdatedAt", l."UpdatedBy" AS "{BarAPI.OID.LowTick}.UpdatedBy",
               c."{TickAPI.ID.UID}" AS "{BarAPI.OID.CloseTick.UID}", c."{TickAPI.ID.Timestamp}" AS "{BarAPI.OID.CloseTick.Timestamp}", c."{TickAPI.ID.Security}" AS "{BarAPI.OID.CloseTick.Security}",
               c."{TickAPI.ID.Ask}" AS "{BarAPI.OID.CloseTick.Ask}", c."{TickAPI.ID.Bid}" AS "{BarAPI.OID.CloseTick.Bid}",
               c."{TickAPI.ID.AskBaseConversion}" AS "{BarAPI.OID.CloseTick.AskBaseConversion}", c."{TickAPI.ID.BidBaseConversion}" AS "{BarAPI.OID.CloseTick.BidBaseConversion}",
               c."{TickAPI.ID.AskQuoteConversion}" AS "{BarAPI.OID.CloseTick.AskQuoteConversion}", c."{TickAPI.ID.BidQuoteConversion}" AS "{BarAPI.OID.CloseTick.BidQuoteConversion}",
               c."{TickAPI.ID.Volume}" AS "{BarAPI.OID.CloseTick.Volume}",
               c."CreatedAt" AS "{BarAPI.OID.CloseTick}.CreatedAt", c."CreatedBy" AS "{BarAPI.OID.CloseTick}.CreatedBy",
               c."UpdatedAt" AS "{BarAPI.OID.CloseTick}.UpdatedAt", c."UpdatedBy" AS "{BarAPI.OID.CloseTick}.UpdatedBy"
        FROM "{BarAPI.Schema}"."{BarAPI.Table}" b
        LEFT JOIN "{TickAPI.Schema}"."{TickAPI.Table}" g ON b."{BarAPI.ID.GapTick}"   = g."{TickAPI.ID.UID}"
        LEFT JOIN "{TickAPI.Schema}"."{TickAPI.Table}" o ON b."{BarAPI.ID.OpenTick}"  = o."{TickAPI.ID.UID}"
        LEFT JOIN "{TickAPI.Schema}"."{TickAPI.Table}" h ON b."{BarAPI.ID.HighTick}"  = h."{TickAPI.ID.UID}"
        LEFT JOIN "{TickAPI.Schema}"."{TickAPI.Table}" l ON b."{BarAPI.ID.LowTick}"   = l."{TickAPI.ID.UID}"
        LEFT JOIN "{TickAPI.Schema}"."{TickAPI.Table}" c ON b."{BarAPI.ID.CloseTick}" = c."{TickAPI.ID.UID}"
        WHERE b."{BarAPI.ID.Security}" = :security: AND b."{BarAPI.ID.Timeframe}" = :timeframe:
          AND b."{BarAPI.ID.Timestamp}" BETWEEN :start: AND :stop:
        ORDER BY b."{BarAPI.ID.Timestamp}"
        '''
        df = db.executeone(QueryAPI(sql), security=security, timeframe=timeframe, start=start, stop=stop, schema=BarAPI.Schema, table=BarAPI.Table).fetchall(legacy=False)
        return df

    @staticmethod
    def push_bars(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Market.Bar import BarAPI
        db.upsert(schema=BarAPI.Schema, table=BarAPI.Table, data=data, key=[str(BarAPI.ID.Timestamp), str(BarAPI.ID.Security), str(BarAPI.ID.Timeframe)], exclude=["CreatedAt", "CreatedBy"])

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
        if str(BarAPI.ID.Timeframe) in data.columns:
            self.GapTicks.init_data(self._data_)
            self.OpenTicks.init_data(self._data_)
            self.HighTicks.init_data(self._data_)
            self.LowTicks.init_data(self._data_)
            self.CloseTicks.init_data(self._data_)
            self.Volume.init_data(self._data_)
        else:
            self.Ticks.init_data(self._data_)

    def update_data(self, data: Union[TickAPI, BarAPI]) -> None:
        from Library.Market.Bar import BarAPI
        df = pl.DataFrame([data.dict()], strict=False)
        self._data_.extend(df)
        if isinstance(data, BarAPI):
            self.GapTicks.init_data(self._data_)
            self.OpenTicks.init_data(self._data_)
            self.HighTicks.init_data(self._data_)
            self.LowTicks.init_data(self._data_)
            self.CloseTicks.init_data(self._data_)
            self.Volume.init_data(self._data_)
        else:
            self.Ticks.init_data(self._data_)

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