from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey
from Library.Universe.Universe import UniverseAPI

if TYPE_CHECKING: from Library.Database import DatabaseAPI

_UNIT_MAP_ = {"S": "Second", "M": "Minute", "H": "Hour", "D": "Day", "W": "Week", "MN": "Month", "Y": "Year"}
_MINUTES_MAP_ = {"S": 1 / 60, "M": 1, "H": 60, "D": 1440, "W": 10080, "MN": 43200, "Y": 525600}
_NAME_TO_UNIT_ = {v: k for k, v in _UNIT_MAP_.items()}
_UID_PATTERN_ = re.compile(r"^([A-Z]+)(\d*)$")
_ALIAS_UID_PATTERN_ = re.compile(r"^(\d*)([A-Z]+)(\d*)$")

@dataclass
class TimeframeAPI(UniverseAPI):

    Table: ClassVar[str] = "Timeframe"

    UID: str | None = None
    Name: str | None = None
    Unit: str | None = None
    Value: int | None = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Name: pl.String(),
            self.ID.Unit: pl.String(),
            self.ID.Value: pl.Int32(),
            **super().Structure
        }

    @staticmethod
    def normalize(uid: str | None) -> str:
        if not uid: return ""
        uid = str(uid).strip().upper()
        if uid in ["DAILY", "D", "DAY", "1D"]: return "D1"
        if uid in ["WEEKLY", "W", "WEEK", "1W"]: return "W1"
        if uid in ["MONTHLY", "MN", "MONTH", "1MN"]: return "MN1"
        if uid in ["HOURLY", "H", "HOUR", "1H", "60", "60M"]: return "H1"
        if uid in ["MINUTELY", "M", "MINUTE", "1M"]: return "M1"
        if uid in ["SECONDLY", "S", "SECOND", "1S"]: return "S1"
        if uid in ["YEARLY", "Y", "YEAR", "1Y"]: return "Y1"
        match = _ALIAS_UID_PATTERN_.match(uid)
        if match:
            prefix, unit, suffix = match.groups()
            v = int(prefix or suffix or 1)
            if unit.startswith("MN"): unit = "MN"
            elif unit.startswith("M"): unit = "M"
            elif unit.startswith("H"): unit = "H"
            elif unit.startswith("D"): unit = "D"
            elif unit.startswith("W"): unit = "W"
            elif unit.startswith("S"): unit = "S"
            elif unit.startswith("Y"): unit = "Y"
            return f"{unit}{v}"
        return uid

    def __post_init__(self,
                      db: DatabaseAPI | None,
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        if self.UID: self.UID = self.normalize(self.UID)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        if not self.Unit: self._infer_()

    def _infer_(self) -> None:
        if not self.UID: return
        match = _UID_PATTERN_.match(self.UID)
        if not match: return
        unit, suffix = match.groups()
        v = int(suffix or 1)
        self.Unit, self.Value = unit, v
        name = _UNIT_MAP_.get(unit, "Minute")
        self.Name = name if v == 1 else f"{name}{v}"

    def _pull_(self, overload: bool) -> dict | None:
        condition, parameters = None, None
        if not self.UID and self.Name:
            condition, parameters = '"Name" = :value:', {"value": self.Name}
        row = super()._pull_(overload=overload) if condition is None else self._fetch_(condition=condition, parameters=parameters, overload=overload)
        if not row and not condition:
            if self.Unit is None and not _UID_PATTERN_.match(self.UID): raise ValueError(f"Timeframe '{self.UID}' not found in database and lacks correct format for creation.")
        return row

    @property
    def Hours(self) -> float | None:
        minutes = self.Minutes
        return minutes / 60 if minutes is not None else None

    @property
    def Minutes(self) -> float | None:
        if self.Value is None or self.Unit is None: return None
        return self.Value * _MINUTES_MAP_.get(self.Unit, 1)

    @property
    def Seconds(self) -> float | None:
        minutes = self.Minutes
        return minutes * 60 if minutes is not None else None