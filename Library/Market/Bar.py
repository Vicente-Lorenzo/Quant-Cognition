from datetime import datetime
from typing import Union, ClassVar
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataclass import DataclassAPI, overridefield, coerce
from Library.Database.Datapoint import DatapointAPI
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Point import PointAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Typing import MISSING

@dataclass
class BarAPI(DataclassAPI):

    _flatten_: ClassVar[tuple[str, ...]] = ("GapPoint", "OpenPoint", "HighPoint", "LowPoint", "ClosePoint")

    Security: InitVar[Union[int, SecurityAPI, None]] = field(default=MISSING)
    Timeframe: InitVar[Union[str, TimeframeAPI, None]] = field(default=MISSING)
    Timestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)
    GapPoint: Union[PointAPI, None] = None
    OpenPoint: Union[PointAPI, None] = None
    HighPoint: Union[PointAPI, None] = None
    LowPoint: Union[PointAPI, None] = None
    ClosePoint: Union[PointAPI, None] = None
    Volume: Union[float, None] = None

    _security_: Union[SecurityAPI, None] = field(default=None, init=False, repr=False)
    _timeframe_: Union[TimeframeAPI, None] = field(default=None, init=False, repr=False)
    _timestamp_: Union[TimestampAPI, None] = field(default=None, init=False, repr=False)

    def __post_init__(self,
                      security: Union[int, SecurityAPI, None],
                      timeframe: Union[str, TimeframeAPI, None],
                      timestamp: Union[datetime, TimestampAPI, None]) -> None:
        security = coerce(security)
        timeframe = coerce(timeframe)
        timestamp = coerce(timestamp)
        self._security_ = DatapointAPI._relate_(security, SecurityAPI)
        self._timeframe_ = DatapointAPI._relate_(timeframe, TimeframeAPI)
        self._timestamp_ = TimestampAPI.assign(None, timestamp)

    def _ticks_(self) -> list:
        return [tick for point in (self.GapPoint, self.OpenPoint, self.HighPoint, self.LowPoint, self.ClosePoint) if point is not None for tick in (point.AskTick, point.BidTick) if tick is not None]

    @property
    @overridefield
    def Security(self) -> Union[SecurityAPI, None]:
        return self._security_
    @Security.setter
    def Security(self, val: Union[int, SecurityAPI, None]) -> None:
        if val is not None: self._security_ = DatapointAPI._relate_(val, SecurityAPI)
        for tick in self._ticks_(): tick.Security = self._security_

    @property
    @overridefield
    def Timeframe(self) -> Union[TimeframeAPI, None]:
        return self._timeframe_
    @Timeframe.setter
    def Timeframe(self, val: Union[str, TimeframeAPI, None]) -> None:
        if val is not None: self._timeframe_ = DatapointAPI._relate_(val, TimeframeAPI)

    @property
    @overridefield
    def Timestamp(self) -> Union[TimestampAPI, None]:
        return self._timestamp_
    @Timestamp.setter
    def Timestamp(self, val: Union[datetime, TimestampAPI, None]) -> None:
        self._timestamp_ = TimestampAPI.assign(self._timestamp_, val)