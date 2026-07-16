from __future__ import annotations

from dataclasses import dataclass
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Auth.User import UserAPI
from Library.Utility.Enumeration import EnumerationAPI
from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Database.Datapoint import DatapointAPI

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

class Kind(EnumerationAPI):
    Manual = 0
    Scheduled = 1
    Service = 2

@dataclass
class WorkflowAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Scheduler"
    Table: ClassVar[str] = "Workflow"

    UID: Union[str, None] = None
    Enabled: Union[bool, None] = None
    Schedule: Union[str, None] = None
    Kind: Union[str, Kind, None] = None
    Waits: Union[bool, None] = None
    Name: Union[str, None] = None
    Owner: Union[str, None] = None
    Description: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Enabled: pl.Boolean(),
            self.ID.Schedule: pl.String(),
            self.ID.Kind: pl.String(),
            self.ID.Waits: pl.Boolean(),
            self.ID.Name: pl.String(),
            self.ID.Owner: ForeignKey(pl.String, reference=f'"{UserAPI.Schema}"."{UserAPI.Table}"("{UserAPI.ID.UID}")'),
            self.ID.Description: pl.String(),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        self.Kind = Kind.parse(self.Kind)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)