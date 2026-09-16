import uuid
from datetime import datetime
from dataclasses import dataclass
from typing_extensions import Self
from typing import Union, ClassVar

from Library.Scheduler.Workflow import WorkflowAPI, Kind
from Library.Database.Dataframe import pl
from Library.Database.Database import DatabaseAPI, PrimaryKey, ForeignKey
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
            self.ID.WID: ForeignKey(pl.String, reference=WorkflowAPI.reference()),
            self.ID.Kind: pl.String(),
            self.ID.Status: pl.String(),
            self.ID.StartedAt: pl.Datetime(),
            self.ID.StoppedAt: pl.Datetime(),
            **super().Structure
        }

    @classmethod
    def start(cls, db: DatabaseAPI, wid: str, kind: str, started: datetime, by: str) -> Self:
        from Library.Scheduler.Run import RunStatus
        cycle = cls(UID=uuid.uuid4().hex, WID=wid, Kind=kind, Status=RunStatus.Running.name, StartedAt=started, db=db)
        cycle.save(by=by)
        return cycle