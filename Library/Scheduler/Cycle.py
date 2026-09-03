from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from typing import Union, ClassVar

from Library.Scheduler.Workflow import WorkflowAPI, Kind
from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Database.Datapoint import DatapointAPI

@dataclass
class CycleAPI(DatapointAPI):

    Schema: ClassVar[str] = WorkflowAPI.Schema
    Table: ClassVar[str] = "Cycle"

    UID: Union[str, None] = None
    WID: Union[str, None] = None
    Kind: Union[str, Kind, None] = None
    Status: Union[str, None] = None
    StartedAt: Union[datetime, None] = None
    StoppedAt: Union[datetime, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.WID: ForeignKey(pl.String, reference=f'"{WorkflowAPI.Schema}"."{WorkflowAPI.Table}"("{WorkflowAPI.ID.UID}")'),
            self.ID.Kind: pl.String(),
            self.ID.Status: pl.String(),
            self.ID.StartedAt: pl.Datetime(),
            self.ID.StoppedAt: pl.Datetime(),
            **super().Structure
        }