from __future__ import annotations

from typing import ClassVar
from datetime import datetime
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import IdentityKey, PrimaryKey, ForeignKey, DatabaseAPI
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Dataclass import overridefield, coerce
from Library.Market.Market import MarketAPI
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Tick import TickAPI
from Library.Market.Price import PriceAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Typing import MISSING

@dataclass
class BarAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = MarketAPI.Schema
    Table: ClassVar[str] = "Bar"

    UID: int | None = field(default=None, kw_only=True)
    Security: InitVar[int | SecurityAPI | None] = field(default=MISSING)
    Timeframe: InitVar[str | TimeframeAPI | None] = field(default=MISSING)
    Timestamp: InitVar[datetime | TimestampAPI | None] = field(default=MISSING)

    GapTick: InitVar[int | TickAPI | None] = field(default=MISSING)
    OpenTick: InitVar[int | TickAPI | None] = field(default=MISSING)
    HighTick: InitVar[int | TickAPI | None] = field(default=MISSING)
    LowTick: InitVar[int | TickAPI | None] = field(default=MISSING)
    CloseTick: InitVar[int | TickAPI | None] = field(default=MISSING)

    Volume: float | None = None

    _security_: SecurityAPI | None = field(default=None, init=False, repr=False)
    _timeframe_: TimeframeAPI | None = field(default=None, init=False, repr=False)
    _timestamp_: TimestampAPI | None = field(default=None, init=False, repr=False)
    _gap_tick_: TickAPI | None = field(default=None, init=False, repr=False)
    _open_tick_: TickAPI | None = field(default=None, init=False, repr=False)
    _high_tick_: TickAPI | None = field(default=None, init=False, repr=False)
    _low_tick_: TickAPI | None = field(default=None, init=False, repr=False)
    _close_tick_: TickAPI | None = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: IdentityKey(pl.Int64),
            self.ID.Timestamp: PrimaryKey(pl.Datetime),
            self.ID.Security: ForeignKey(pl.Int64, reference=f'"{SecurityAPI.Schema}"."{SecurityAPI.Table}"("{SecurityAPI.ID.UID}")', primary=True),
            self.ID.Timeframe: ForeignKey(pl.String, reference=f'"{TimeframeAPI.Schema}"."{TimeframeAPI.Table}"("{TimeframeAPI.ID.UID}")', primary=True),
            self.ID.GapTick: ForeignKey(pl.Int64, reference=f'"{TickAPI.Schema}"."{TickAPI.Table}"("{TickAPI.ID.UID}")'),
            self.ID.OpenTick: ForeignKey(pl.Int64, reference=f'"{TickAPI.Schema}"."{TickAPI.Table}"("{TickAPI.ID.UID}")'),
            self.ID.HighTick: ForeignKey(pl.Int64, reference=f'"{TickAPI.Schema}"."{TickAPI.Table}"("{TickAPI.ID.UID}")'),
            self.ID.LowTick: ForeignKey(pl.Int64, reference=f'"{TickAPI.Schema}"."{TickAPI.Table}"("{TickAPI.ID.UID}")'),
            self.ID.CloseTick: ForeignKey(pl.Int64, reference=f'"{TickAPI.Schema}"."{TickAPI.Table}"("{TickAPI.ID.UID}")'),
            self.ID.Volume: pl.Float64(),
            **super().Structure
        }

    def __post_init__(self,
                      db: DatabaseAPI | None,
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool,
                      security: int | SecurityAPI | None,
                      timeframe: str | TimeframeAPI | None,
                      timestamp: datetime | TimestampAPI | None,
                      gap_tick: int | TickAPI | None,
                      open_tick: int | TickAPI | None,
                      high_tick: int | TickAPI | None,
                      low_tick: int | TickAPI | None,
                      close_tick: int | TickAPI | None) -> None:
        security = coerce(security)
        timeframe = coerce(timeframe)
        timestamp = coerce(timestamp)
        gap_tick = coerce(gap_tick)
        open_tick = coerce(open_tick)
        high_tick = coerce(high_tick)
        low_tick = coerce(low_tick)
        close_tick = coerce(close_tick)
        if isinstance(security, SecurityAPI): self._security_ = security
        elif security is not MISSING and security is not None:
            self._security_ = SecurityAPI(UID=security, db=db, autoload=autoload)
        if isinstance(timeframe, TimeframeAPI): self._timeframe_ = timeframe
        elif timeframe is not MISSING and timeframe is not None:
            self._timeframe_ = TimeframeAPI(UID=timeframe, db=db, autoload=autoload)
        if isinstance(timestamp, TimestampAPI): self._timestamp_ = timestamp
        elif timestamp is not MISSING and timestamp is not None:
            self._timestamp_ = TimestampAPI(DateTime=timestamp)
        def _init_tick_(val: int | TickAPI | None) -> TickAPI | None:
            if isinstance(val, TickAPI): return val
            if val is not MISSING and val is not None:
                return TickAPI(UID=val, db=db, autoload=autoload)
            return None
        self._gap_tick_ = _init_tick_(gap_tick)
        self._open_tick_ = _init_tick_(open_tick)
        self._high_tick_ = _init_tick_(high_tick)
        self._low_tick_ = _init_tick_(low_tick)
        self._close_tick_ = _init_tick_(close_tick)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def save(self, by: str = "Autosave") -> None:
        for t in (self._gap_tick_, self._open_tick_, self._high_tick_, self._low_tick_, self._close_tick_):
            if t: t.save(by=by)
        super().save(by=by)
        if self.UID is None: self.load()

    @property
    @overridefield
    def Security(self) -> SecurityAPI | None:
        return self._security_
    @Security.setter
    def Security(self, val: int | SecurityAPI | None) -> None:
        if isinstance(val, SecurityAPI): self._security_ = val
        elif val is not None: self._security_ = SecurityAPI(UID=val, db=self._db_, autoload=self._autoload_)
        for t in (self._gap_tick_, self._open_tick_, self._high_tick_, self._low_tick_, self._close_tick_):
            if t: t.Security = self._security_

    @property
    @overridefield
    def Timeframe(self) -> TimeframeAPI | None:
        return self._timeframe_
    @Timeframe.setter
    def Timeframe(self, val: str | TimeframeAPI | None) -> None:
        if isinstance(val, TimeframeAPI): self._timeframe_ = val
        elif val is not None: self._timeframe_ = TimeframeAPI(UID=val, db=self._db_, autoload=self._autoload_)

    @property
    @overridefield
    def Timestamp(self) -> TimestampAPI | None:
        return self._timestamp_
    @Timestamp.setter
    def Timestamp(self, val: datetime | TimestampAPI | None) -> None:
        if isinstance(val, TimestampAPI): self._timestamp_ = val
        elif val is not None:
            if self._timestamp_: self._timestamp_.DateTime = val
            else: self._timestamp_ = TimestampAPI(DateTime=val)

    @property
    @overridefield
    def GapTick(self) -> TickAPI | None:
        return self._gap_tick_
    @GapTick.setter
    def GapTick(self, val: int | TickAPI | None) -> None:
        if isinstance(val, TickAPI): self._gap_tick_ = val
        elif val is not None: self._gap_tick_ = TickAPI(UID=val, db=self._db_, autoload=self._autoload_)

    @property
    @overridefield
    def OpenTick(self) -> TickAPI | None:
        return self._open_tick_
    @OpenTick.setter
    def OpenTick(self, val: int | TickAPI | None) -> None:
        if isinstance(val, TickAPI): self._open_tick_ = val
        elif val is not None: self._open_tick_ = TickAPI(UID=val, db=self._db_, autoload=self._autoload_)

    @property
    @overridefield
    def HighTick(self) -> TickAPI | None:
        return self._high_tick_
    @HighTick.setter
    def HighTick(self, val: int | TickAPI | None) -> None:
        if isinstance(val, TickAPI): self._high_tick_ = val
        elif val is not None: self._high_tick_ = TickAPI(UID=val, db=self._db_, autoload=self._autoload_)

    @property
    @overridefield
    def LowTick(self) -> TickAPI | None:
        return self._low_tick_
    @LowTick.setter
    def LowTick(self, val: int | TickAPI | None) -> None:
        if isinstance(val, TickAPI): self._low_tick_ = val
        elif val is not None: self._low_tick_ = TickAPI(UID=val, db=self._db_, autoload=self._autoload_)

    @property
    @overridefield
    def CloseTick(self) -> TickAPI | None:
        return self._close_tick_
    @CloseTick.setter
    def CloseTick(self, val: int | TickAPI | None) -> None:
        if isinstance(val, TickAPI): self._close_tick_ = val
        elif val is not None: self._close_tick_ = TickAPI(UID=val, db=self._db_, autoload=self._autoload_)

    @property
    def RangeTick(self) -> PriceAPI | None:
        h = self._high_tick_
        l = self._low_tick_
        if h is None or l is None or h.Bid is None or l.Bid is None: return None
        return PriceAPI(Price=h.Bid.Price - l.Bid.Price, Reference=h.Bid.Price, Contract=h.Bid.Contract)