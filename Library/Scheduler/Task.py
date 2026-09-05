from dataclasses import dataclass
from typing import Union, ClassVar

from Library.Auth.User import UserAPI
from Library.Scheduler.Workflow import WorkflowAPI, Kind
from Library.Utility.Enumeration import EnumerationAPI
from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Database.Datapoint import DatapointAPI

class TaskType(EnumerationAPI):

    Batch = 0
    Shell = 1
    Python = 2

@dataclass
class TaskAPI(DatapointAPI):

    Schema: ClassVar[str] = WorkflowAPI.Schema
    Table: ClassVar[str] = "Task"
    Enums: ClassVar[dict] = {"Type": TaskType, "Kind": Kind}

    Defaults: ClassVar[dict] = {"Enabled": True, "Kind": Kind.Scheduled.name, "Type": TaskType.Python.name, "RequiresApproval": False, "RequiresReview": False, "MaxRetry": 0, "RetryDelay": 0, "Waits": True, "Tolerates": True}

    UID: Union[str, None] = None
    WID: Union[str, None] = None
    Name: Union[str, None] = None
    Owner: Union[str, None] = None
    Enabled: Union[bool, None] = None
    Kind: Union[str, Kind, None] = None
    Type: Union[str, TaskType, None] = None
    Schedule: Union[str, None] = None
    Path: Union[str, None] = None
    Arguments: Union[str, None] = None
    Waits: Union[bool, None] = None
    Tolerates: Union[bool, None] = None
    RequiresApproval: Union[bool, None] = None
    RequiresReview: Union[bool, None] = None
    MaxRetry: Union[int, None] = None
    RetryDelay: Union[int, None] = None
    Description: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.WID: ForeignKey(pl.String, reference=f'"{WorkflowAPI.Schema}"."{WorkflowAPI.Table}"("{WorkflowAPI.ID.UID}")'),
            self.ID.Name: pl.String(),
            self.ID.Owner: ForeignKey(pl.String, reference=f'"{UserAPI.Schema}"."{UserAPI.Table}"("{UserAPI.ID.UID}")'),
            self.ID.Enabled: pl.Boolean(),
            self.ID.Kind: pl.String(),
            self.ID.Type: pl.String(),
            self.ID.Schedule: pl.String(),
            self.ID.Path: pl.String(),
            self.ID.Arguments: pl.String(),
            self.ID.Waits: pl.Boolean(),
            self.ID.Tolerates: pl.Boolean(),
            self.ID.RequiresApproval: pl.Boolean(),
            self.ID.RequiresReview: pl.Boolean(),
            self.ID.MaxRetry: pl.Int64(),
            self.ID.RetryDelay: pl.Int64(),
            self.ID.Description: pl.String(),
            **super().Structure
        }