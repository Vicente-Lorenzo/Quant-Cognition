from __future__ import annotations

import math
from datetime import datetime
from calendar import monthrange, isleap
from dataclasses import dataclass, field

from Library.Database.Dataclass import DataclassAPI

@dataclass(kw_only=True)
class CycleAPI(DataclassAPI):

    Value: float = field(init=True, repr=True)
    Period: int | None = field(default=None, init=True, repr=True)

    @property
    def UID(self) -> float:
        return self.Value
    @UID.setter
    def UID(self, val) -> None:
        pass

    @property
    def Normalized(self) -> float | None:
        if not self.Period: return None
        return self.Value / self.Period
    @property
    def Radian(self) -> float | None:
        if not self.Period: return None
        return 2 * math.pi * self.Value / self.Period
    @property
    def Sin(self) -> float | None:
        radian = self.Radian
        return math.sin(radian) if radian is not None else None
    @property
    def Cos(self) -> float | None:
        radian = self.Radian
        return math.cos(radian) if radian is not None else None

@dataclass(kw_only=True)
class TimestampAPI(DataclassAPI):

    DateTime: datetime = field(init=True, repr=True)

    @property
    def UID(self) -> datetime:
        return self.DateTime
    @UID.setter
    def UID(self, val) -> None:
        pass

    @property
    def Epoch(self) -> float:
        return self.DateTime.timestamp()
    @property
    def Year(self) -> CycleAPI:
        return CycleAPI(Value=self.DateTime.year)
    @property
    def Yearday(self) -> CycleAPI:
        return CycleAPI(Value=self.DateTime.timetuple().tm_yday, Period=366 if isleap(self.DateTime.year) else 365)
    @property
    def Month(self) -> CycleAPI:
        return CycleAPI(Value=self.DateTime.month, Period=12)
    @property
    def Week(self) -> CycleAPI:
        return CycleAPI(Value=self.DateTime.isocalendar()[1], Period=52)
    @property
    def Weekday(self) -> CycleAPI:
        return CycleAPI(Value=self.DateTime.weekday(), Period=7)
    @property
    def Day(self) -> CycleAPI:
        return CycleAPI(Value=self.DateTime.day, Period=monthrange(self.DateTime.year, self.DateTime.month)[1])
    @property
    def Hour(self) -> CycleAPI:
        return CycleAPI(Value=self.DateTime.hour, Period=24)
    @property
    def Minute(self) -> CycleAPI:
        return CycleAPI(Value=self.DateTime.minute, Period=60)
    @property
    def Second(self) -> CycleAPI:
        return CycleAPI(Value=self.DateTime.second, Period=60)
    @property
    def Millisecond(self) -> CycleAPI:
        return CycleAPI(Value=self.DateTime.microsecond // 1000, Period=1000)