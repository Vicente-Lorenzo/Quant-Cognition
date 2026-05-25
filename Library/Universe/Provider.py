from __future__ import annotations

from dataclasses import dataclass
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey
from Library.Database.Datapoint import DatapointAPI
from Library.Universe.Universe import UniverseAPI
from Library.Utility.Enumeration import EnumerationAPI

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

class Provider(EnumerationAPI):
    Spotware = 0
    Pepperstone = 1
    ICMarkets = 2
    Bloomberg = 3
    Yahoo = 4

class Platform(EnumerationAPI):
    cTrader = 0
    MetaTrader4 = 1
    MetaTrader5 = 2
    NinjaTrader = 3
    QuantConnect = 4
    API = 5

@dataclass
class ProviderAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = UniverseAPI.Schema
    Table: ClassVar[str] = "Provider"

    UID: Union[str, None] = None
    Platform: Union[Platform, str, None] = None
    Name: Union[str, None] = None
    Abbreviation: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Platform: pl.String(),
            self.ID.Name: pl.String(),
            self.ID.Abbreviation: pl.String(),
            **super().Structure
        }

    @staticmethod
    def normalize(name: str) -> str:
        name = name.replace("-", " ")
        for suffix in (" Demo", " Live"):
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        return name.replace(" ", "")

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        self.Platform = Platform.parse(self.Platform)
        if self.Abbreviation and self.Platform and not self.UID:
            self.UID = f"{self.Abbreviation}({self.Platform.name})"
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        clauses, params = [], {}
        if self.UID:
            clauses.append('"UID" = :uid: OR "Abbreviation" = :uid: OR "Name" = :uid: OR POSITION("Abbreviation" IN :uid:) = 1')
            params["uid"] = self.UID
        if self.Name:
            clauses.append('"Name" = :name:')
            params["name"] = self.Name
        if self.Abbreviation:
            clauses.append('"Abbreviation" = :abbr:')
            params["abbr"] = self.Abbreviation
        if not clauses: return None
        row = self._fetch_(condition=" OR ".join(clauses), parameters=params, overload=overload)
        if row:
            self.UID = row.get("UID", self.UID)
            self.Platform = Platform.parse(self.Platform)
        elif self.Platform is None or self.Abbreviation is None:
            raise ValueError(f"Provider '{self.UID or self.Name or self.Abbreviation}' not found in database and lacks required fields for creation.")
        return row