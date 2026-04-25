from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey
from Library.Database.Datapoint import DatapointAPI
from Library.Universe.Universe import UniverseAPI

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

@dataclass
class CategoryAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Universe"
    Table: ClassVar[str] = "Category"

    UID: str | None = None
    Primary: str | None = None
    Secondary: str | None = None
    Alternative: str | None = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Primary: pl.String(),
            self.ID.Secondary: pl.String(),
            self.ID.Alternative: pl.String(),
            **super().Structure
        }

    def __post_init__(self,
                      db: DatabaseAPI | None,
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        if not self.UID and self.Primary and self.Secondary:
            self.UID = f"{self.Primary} ({self.Secondary})"
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _pull_(self, overload: bool) -> dict | None:
        if self._db_ is None: return None
        if not self.UID and not self.Primary: return None
        condition, parameters = None, None
        if self.UID:
            condition = '"UID" = :value: OR "Primary" = :value: OR "Secondary" = :value: OR "Alternative" = :value:'
            parameters = {"value": self.UID}
        elif self.Primary and self.Secondary:
            condition = '"Primary" = :primary: AND "Secondary" = :secondary:'
            parameters = {"primary": self.Primary, "secondary": self.Secondary}
        row = super()._pull_(overload=overload) if condition is None else self._fetch_(condition=condition, parameters=parameters, overload=overload)
        if not row and not condition:
            if self.Primary is None or self.Secondary is None:
                raise ValueError(f"Category '{self.UID or self.Primary}' not found in database and lacks required fields for creation.")
        return row