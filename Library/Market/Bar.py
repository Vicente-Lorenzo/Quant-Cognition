from datetime import datetime
from typing import Union, ClassVar
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey, DatabaseAPI
from Library.Database.Datapoint import DatapointAPI
from Library.Market.Market import MarketAPI
from Library.Database.Dataclass import overridefield, coerce
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Tick import TickAPI
from Library.Market.Price import PriceAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Typing import MISSING

@dataclass
class BarAPI(DatapointAPI):

    Schema: ClassVar[str] = MarketAPI.Schema
    Table: ClassVar[str] = "Bar"

    _flatten_: ClassVar[tuple[str, ...]] = ("GapTick", "OpenTick", "HighTick", "LowTick", "CloseTick")

    UID: Union[int, None] = field(default=None, kw_only=True)
    Security: InitVar[Union[int, SecurityAPI, None]] = field(default=MISSING)
    Timeframe: InitVar[Union[str, TimeframeAPI, None]] = field(default=MISSING)
    Timestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)

    GapTick: InitVar[Union[int, TickAPI, None]] = field(default=MISSING)
    OpenTick: InitVar[Union[int, TickAPI, None]] = field(default=MISSING)
    HighTick: InitVar[Union[int, TickAPI, None]] = field(default=MISSING)
    LowTick: InitVar[Union[int, TickAPI, None]] = field(default=MISSING)
    CloseTick: InitVar[Union[int, TickAPI, None]] = field(default=MISSING)

    Volume: Union[float, None] = None

    _security_: Union[SecurityAPI, None] = field(default=None, init=False, repr=False)
    _timeframe_: Union[TimeframeAPI, None] = field(default=None, init=False, repr=False)
    _timestamp_: Union[TimestampAPI, None] = field(default=None, init=False, repr=False)
    _gap_tick_: Union[TickAPI, None] = field(default=None, init=False, repr=False)
    _open_tick_: Union[TickAPI, None] = field(default=None, init=False, repr=False)
    _high_tick_: Union[TickAPI, None] = field(default=None, init=False, repr=False)
    _low_tick_: Union[TickAPI, None] = field(default=None, init=False, repr=False)
    _close_tick_: Union[TickAPI, None] = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        return {
            self.ID.Security: ForeignKey(pl.Int64, reference=SecurityAPI.reference(), primary=True),
            self.ID.Timeframe: ForeignKey(pl.String, reference=TimeframeAPI.reference(), primary=True),
            self.ID.Timestamp: PrimaryKey(pl.Datetime),
            self.ID.GapTick: ForeignKey(pl.Int64, reference=TickAPI.reference()),
            self.ID.OpenTick: ForeignKey(pl.Int64, reference=TickAPI.reference()),
            self.ID.HighTick: ForeignKey(pl.Int64, reference=TickAPI.reference()),
            self.ID.LowTick: ForeignKey(pl.Int64, reference=TickAPI.reference()),
            self.ID.CloseTick: ForeignKey(pl.Int64, reference=TickAPI.reference()),
            self.ID.Volume: pl.Float64(),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autoload: bool,
                      autooverload: bool,
                      autosave: bool,
                      security: Union[int, SecurityAPI, None],
                      timeframe: Union[str, TimeframeAPI, None],
                      timestamp: Union[datetime, TimestampAPI, None],
                      gap_tick: Union[int, TickAPI, None],
                      open_tick: Union[int, TickAPI, None],
                      high_tick: Union[int, TickAPI, None],
                      low_tick: Union[int, TickAPI, None],
                      close_tick: Union[int, TickAPI, None]) -> None:
        security = coerce(security)
        timeframe = coerce(timeframe)
        timestamp = coerce(timestamp)
        gap_tick = coerce(gap_tick)
        open_tick = coerce(open_tick)
        high_tick = coerce(high_tick)
        low_tick = coerce(low_tick)
        close_tick = coerce(close_tick)
        self._security_ = self._relate_(security, SecurityAPI, db=db, autoload=autoload)
        self._timeframe_ = self._relate_(timeframe, TimeframeAPI, db=db, autoload=autoload)
        self._timestamp_ = TimestampAPI.assign(None, timestamp)
        self._gap_tick_ = self._relate_(gap_tick, TickAPI, db=db, autoload=autoload)
        self._open_tick_ = self._relate_(open_tick, TickAPI, db=db, autoload=autoload)
        self._high_tick_ = self._relate_(high_tick, TickAPI, db=db, autoload=autoload)
        self._low_tick_ = self._relate_(low_tick, TickAPI, db=db, autoload=autoload)
        self._close_tick_ = self._relate_(close_tick, TickAPI, db=db, autoload=autoload)
        super().__post_init__(db=db, migrate=migrate, autoload=autoload, autooverload=autooverload, autosave=autosave)

    def save(self, by: str = "Autosave") -> None:
        for t in (self._gap_tick_, self._open_tick_, self._high_tick_, self._low_tick_, self._close_tick_):
            if t: t.save(by=by)
        super().save(by=by)

    @property
    @overridefield
    def Security(self) -> Union[SecurityAPI, None]:
        return self._security_
    @Security.setter
    def Security(self, val: Union[int, SecurityAPI, None]) -> None:
        if val is not None: self._security_ = self._relate_(val, SecurityAPI, db=self._db_, autoload=self._autoload_)
        for t in (self._gap_tick_, self._open_tick_, self._high_tick_, self._low_tick_, self._close_tick_):
            if t: t.Security = self._security_

    @property
    @overridefield
    def Timeframe(self) -> Union[TimeframeAPI, None]:
        return self._timeframe_
    @Timeframe.setter
    def Timeframe(self, val: Union[str, TimeframeAPI, None]) -> None:
        if val is not None: self._timeframe_ = self._relate_(val, TimeframeAPI, db=self._db_, autoload=self._autoload_)

    @property
    @overridefield
    def Timestamp(self) -> Union[TimestampAPI, None]:
        return self._timestamp_
    @Timestamp.setter
    def Timestamp(self, val: Union[datetime, TimestampAPI, None]) -> None:
        self._timestamp_ = TimestampAPI.assign(self._timestamp_, val)

    @property
    @overridefield
    def GapTick(self) -> Union[TickAPI, None]:
        return self._gap_tick_
    @GapTick.setter
    def GapTick(self, val: Union[int, TickAPI, None]) -> None:
        if val is not None: self._gap_tick_ = self._relate_(val, TickAPI, db=self._db_, autoload=self._autoload_)

    @property
    @overridefield
    def OpenTick(self) -> Union[TickAPI, None]:
        return self._open_tick_
    @OpenTick.setter
    def OpenTick(self, val: Union[int, TickAPI, None]) -> None:
        if val is not None: self._open_tick_ = self._relate_(val, TickAPI, db=self._db_, autoload=self._autoload_)

    @property
    @overridefield
    def HighTick(self) -> Union[TickAPI, None]:
        return self._high_tick_
    @HighTick.setter
    def HighTick(self, val: Union[int, TickAPI, None]) -> None:
        if val is not None: self._high_tick_ = self._relate_(val, TickAPI, db=self._db_, autoload=self._autoload_)

    @property
    @overridefield
    def LowTick(self) -> Union[TickAPI, None]:
        return self._low_tick_
    @LowTick.setter
    def LowTick(self, val: Union[int, TickAPI, None]) -> None:
        if val is not None: self._low_tick_ = self._relate_(val, TickAPI, db=self._db_, autoload=self._autoload_)

    @property
    @overridefield
    def CloseTick(self) -> Union[TickAPI, None]:
        return self._close_tick_
    @CloseTick.setter
    def CloseTick(self, val: Union[int, TickAPI, None]) -> None:
        if val is not None: self._close_tick_ = self._relate_(val, TickAPI, db=self._db_, autoload=self._autoload_)

    @property
    def RangeTick(self) -> Union[PriceAPI, None]:
        h = self._high_tick_
        l = self._low_tick_
        if h is None or l is None or h.Bid is None or l.Bid is None: return None
        return PriceAPI(Price=h.Bid.Price - l.Bid.Price, Reference=h.Bid.Price, Contract=h.Bid.Contract)