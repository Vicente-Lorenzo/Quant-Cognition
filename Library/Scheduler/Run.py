from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Auth.User import UserAPI
from Library.Engine.Machine import MachineAPI
from Library.Scheduler.Task import TaskAPI
from Library.Utility.Enumeration import EnumerationAPI
from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Database import PrimaryKey, ForeignKey

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

class RunStatus(EnumerationAPI):
    Waiting = 0
    Running = 1
    Approving = 2
    Reviewing = 3
    Retrying = 4
    Success = 5
    Failure = 6

class RunEvent(EnumerationAPI):
    Start = 0
    Complete = 1
    RequireApproval = 2
    RequireReview = 3
    Retry = 4
    Fail = 5
    Accept = 6
    Reject = 7

@dataclass
class RunAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Scheduler"
    Table: ClassVar[str] = "Run"

    UID: Union[str, None] = None
    TID: Union[str, None] = None
    WorkflowRun: Union[str, None] = None
    Status: Union[str, RunStatus, None] = None
    Attempt: Union[int, None] = None
    StartedAt: Union[datetime, None] = None
    FinishedAt: Union[datetime, None] = None
    Heartbeat: Union[datetime, None] = None
    Duration: Union[float, None] = None
    Memory: Union[int, None] = None
    ExitCode: Union[int, None] = None
    Approver: Union[str, None] = None
    Log: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.TID: ForeignKey(pl.String, reference=f'"{TaskAPI.Schema}"."{TaskAPI.Table}"("{TaskAPI.ID.UID}")'),
            self.ID.WorkflowRun: pl.String(),
            self.ID.Status: pl.String(),
            self.ID.Attempt: pl.Int64(),
            self.ID.StartedAt: pl.Datetime(),
            self.ID.FinishedAt: pl.Datetime(),
            self.ID.Heartbeat: pl.Datetime(),
            self.ID.Duration: pl.Float64(),
            self.ID.Memory: pl.Int64(),
            self.ID.ExitCode: pl.Int64(),
            self.ID.Approver: ForeignKey(pl.String, reference=f'"{UserAPI.Schema}"."{UserAPI.Table}"("{UserAPI.ID.UID}")'),
            self.ID.Log: pl.String(),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        self.Status = RunStatus.parse(self.Status)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _resolve_(self, event: RunEvent, by: str) -> bool:
        if self.Status not in (RunStatus.Approving.name, RunStatus.Reviewing.name): return False
        machine = RunAPI.machine()
        machine.perform(RunEvent.Start, None)
        machine.perform(RunEvent.RequireApproval if self.Status == RunStatus.Approving.name else RunEvent.RequireReview, None)
        machine.perform(event, None)
        self.Status, self.Approver, self.FinishedAt = machine.At.Name, by, self.FinishedAt or datetime.now()
        self.save(by=by)
        return True

    def accept(self, by: str = "User") -> bool:
        return self._resolve_(RunEvent.Accept, by)

    def reject(self, by: str = "User") -> bool:
        return self._resolve_(RunEvent.Reject, by)

    @staticmethod
    def machine() -> MachineAPI:
        machine = MachineAPI(Name="Run", Events=len(RunEvent))
        waiting = machine.state(name="Waiting")
        running = machine.state(name="Running")
        approving = machine.state(name="Approving")
        reviewing = machine.state(name="Reviewing")
        retrying = machine.state(name="Retrying", end=True)
        success = machine.state(name="Success", end=True)
        failure = machine.state(name="Failure", end=True)
        waiting.on(event=RunEvent.Start, to=running, action=None, reason="Started")
        running.on(event=RunEvent.Complete, to=success, action=None, reason="Completed")
        running.on(event=RunEvent.RequireApproval, to=approving, action=None, reason="Awaiting Approval")
        running.on(event=RunEvent.RequireReview, to=reviewing, action=None, reason="Awaiting Review")
        running.on(event=RunEvent.Retry, to=retrying, action=None, reason="Retrying")
        running.on(event=RunEvent.Fail, to=failure, action=None, reason="Failed")
        approving.on(event=RunEvent.Accept, to=success, action=None, reason="Approved")
        approving.on(event=RunEvent.Reject, to=failure, action=None, reason="Rejected")
        reviewing.on(event=RunEvent.Accept, to=success, action=None, reason="Salvaged")
        reviewing.on(event=RunEvent.Reject, to=failure, action=None, reason="Confirmed Failure")
        return machine