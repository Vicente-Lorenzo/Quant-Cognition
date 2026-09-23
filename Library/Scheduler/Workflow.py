from dataclasses import dataclass
from typing import Union, ClassVar

from Library.Auth.Role import RoleAPI
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
    Enums: ClassVar[dict] = {"Kind": Kind, "RunRole": RoleAPI, "EditRole": RoleAPI}

    Defaults: ClassVar[dict] = {"Enabled": True, "Waits": True}

    UID: Union[str, None] = None
    Name: Union[str, None] = None
    Owner: Union[str, None] = None
    RunRole: Union[str, RoleAPI, None] = None
    EditRole: Union[str, RoleAPI, None] = None
    Enabled: Union[bool, None] = None
    Kind: Union[str, Kind, None] = None
    Schedule: Union[str, None] = None
    Zone: Union[str, None] = None
    Waits: Union[bool, None] = None
    Description: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Name: pl.String(),
            self.ID.Owner: ForeignKey(pl.String, reference=UserAPI.reference()),
            self.ID.RunRole: pl.String(),
            self.ID.EditRole: pl.String(),
            self.ID.Enabled: pl.Boolean(),
            self.ID.Kind: pl.String(),
            self.ID.Schedule: pl.String(),
            self.ID.Zone: pl.String(),
            self.ID.Waits: pl.Boolean(),
            self.ID.Description: pl.String(),
            **super().Structure
        }