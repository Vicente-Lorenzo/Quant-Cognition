from __future__ import annotations

from dataclasses import dataclass
from typing import Union, ClassVar

from Library.Auth.User import UserAPI
from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Database.Datapoint import DatapointAPI

@dataclass
class WorkflowAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Scheduler"
    Table: ClassVar[str] = "Workflow"

    UID: Union[str, None] = None
    Name: Union[str, None] = None
    Owner: Union[str, None] = None
    Description: Union[str, None] = None
    Schedule: Union[str, None] = None
    Enabled: Union[bool, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Name: pl.String(),
            self.ID.Owner: ForeignKey(pl.String, reference=f'"{UserAPI.Schema}"."{UserAPI.Table}"("{UserAPI.ID.UID}")'),
            self.ID.Description: pl.String(),
            self.ID.Schedule: pl.String(),
            self.ID.Enabled: pl.Boolean(),
            **super().Structure
        }