from dataclasses import dataclass
from typing import Union, ClassVar

from Library.Auth.User import UserAPI
from Library.Utility.Enumeration import EnumerationAPI
from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Database.Datapoint import DatapointAPI

class Kind(EnumerationAPI):

    Manual = 0
    Scheduled = 1
    Service = 2

@dataclass
class WorkflowAPI(DatapointAPI):

    Schema: ClassVar[str] = "Scheduler"
    Table: ClassVar[str] = "Workflow"
    Enums: ClassVar[dict] = {"Kind": Kind}

    Defaults: ClassVar[dict] = {"Enabled": True, "Waits": True}

    UID: Union[str, None] = None
    Name: Union[str, None] = None
    Owner: Union[str, None] = None
    Enabled: Union[bool, None] = None
    Kind: Union[str, Kind, None] = None
    Schedule: Union[str, None] = None
    Waits: Union[bool, None] = None
    Description: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Name: pl.String(),
            self.ID.Owner: ForeignKey(pl.String, reference=f'"{UserAPI.Schema}"."{UserAPI.Table}"("{UserAPI.ID.UID}")'),
            self.ID.Enabled: pl.Boolean(),
            self.ID.Kind: pl.String(),
            self.ID.Schedule: pl.String(),
            self.ID.Waits: pl.Boolean(),
            self.ID.Description: pl.String(),
            **super().Structure
        }