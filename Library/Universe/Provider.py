from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Enumeration import Enumeration, as_enum
from Library.Universe.Universe import UniverseAPI

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

class Provider(Enumeration):
    Spotware = 0
    Pepperstone = 1
    ICMarkets = 2
    Bloomberg = 3
    Yahoo = 4

class Platform(Enumeration):
    cTrader = 0
    MetaTrader4 = 1
    MetaTrader5 = 2
    NinjaTrader = 3
    QuantConnect = 4
    API = 5

@dataclass
class ProviderAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Universe"
    Table: ClassVar[str] = "Provider"

    UID: str | None = None
    Platform: Platform | str | None = None
    Name: str | None = None
    Abbreviation: str | None = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Platform: pl.Enum([p.name for p in Platform]),
            self.ID.Name: pl.String(),
            self.ID.Abbreviation: pl.String(),
            **super().Structure
        }

    @staticmethod
    def normalize(uid: str) -> str:
        return uid.replace("-", " ")

    def __post_init__(self,
                      db: DatabaseAPI | None,
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        self.Platform = as_enum(Platform, self.Platform)
        if self.UID:
            self.UID = self.normalize(self.UID)
        elif self.Abbreviation and self.Platform:
            self.UID = f"{self.Abbreviation} ({self.Platform.name})"
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _pull_(self, overload: bool) -> dict | None:
        condition, parameters = None, None
        if not self.UID and (self.Name or self.Abbreviation):
            clauses, params = [], {}
            if self.Name:
                clauses.append('"Name" = :name:')
                params["name"] = self.Name
            if self.Abbreviation:
                clauses.append('"Abbreviation" = :abbr:')
                params["abbr"] = self.Abbreviation
            condition, parameters = " OR ".join(clauses), params
        row = super()._pull_(overload=overload) if condition is None else self._fetch_(condition=condition, parameters=parameters, overload=overload)
        if row:
            self.Platform = as_enum(Platform, self.Platform)
        elif not row and not condition:
            if self.Platform is None or self.Abbreviation is None:
                raise ValueError(f"Provider '{self.UID or self.Name or self.Abbreviation}' not found in database and lacks required fields for creation.")
        return row