from datetime import datetime
from dataclasses import dataclass
from typing import Union, ClassVar

from Library.Auth.User import UserAPI
from Library.Logging.Log import LogAPI
from Library.Engine.Machine import MachineAPI
from Library.Scheduler.Task import TaskAPI
from Library.Scheduler.Cycle import CycleAPI
from Library.Utility.Enumeration import EnumerationAPI
from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Database import PrimaryKey, ForeignKey

class RunStatus(EnumerationAPI):

    Waiting = 0
    Running = 1
    Approving = 2
    Reviewing = 3
    Retrying = 4
    Success = 5
    Failure = 6

class RetentionLevel(EnumerationAPI):

    Temporary = 0
    Persistent = 1
    Favorite = 2

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

    Schema: ClassVar[str] = TaskAPI.Schema
    Table: ClassVar[str] = "Run"
    Enums: ClassVar[dict] = {"Status": RunStatus, "Retention": RetentionLevel}

    Busy: ClassVar[tuple] = (RunStatus.Waiting.name, RunStatus.Running.name)
    Live: ClassVar[tuple] = (RunStatus.Waiting.name, RunStatus.Running.name, RunStatus.Retrying.name)
    Active: ClassVar[tuple] = (RunStatus.Waiting.name, RunStatus.Running.name, RunStatus.Approving.name, RunStatus.Reviewing.name, RunStatus.Retrying.name)
    Open: ClassVar[tuple] = (RunStatus.Running.name, RunStatus.Approving.name, RunStatus.Reviewing.name)

    UID: Union[str, None] = None
    CID: Union[str, None] = None
    TID: Union[str, None] = None
    Kind: Union[str, None] = None
    Status: Union[str, RunStatus, None] = None
    Retention: Union[str, RetentionLevel, None] = None
    Arguments: Union[str, None] = None
    StartedAt: Union[datetime, None] = None
    StoppedAt: Union[datetime, None] = None
    Duration: Union[float, None] = None
    Heartbeat: Union[datetime, None] = None
    ExitCode: Union[int, None] = None
    Retry: Union[int, None] = None
    Memory: Union[int, None] = None
    PID: Union[int, None] = None
    Auditor: Union[str, None] = None
    LID: Union[str, None] = None
    Log: Union[str, None] = None
    Progress: Union[float, None] = None
    Stage: Union[str, None] = None
    Remaining: Union[float, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.CID: ForeignKey(pl.String, reference=f'"{CycleAPI.Schema}"."{CycleAPI.Table}"("{CycleAPI.ID.UID}")'),
            self.ID.TID: ForeignKey(pl.String, reference=f'"{TaskAPI.Schema}"."{TaskAPI.Table}"("{TaskAPI.ID.UID}")'),
            self.ID.Kind: pl.String(),
            self.ID.Status: pl.String(),
            self.ID.Retention: pl.String(),
            self.ID.Arguments: pl.String(),
            self.ID.StartedAt: pl.Datetime(),
            self.ID.StoppedAt: pl.Datetime(),
            self.ID.Duration: pl.Float64(),
            self.ID.Heartbeat: pl.Datetime(),
            self.ID.ExitCode: pl.Int64(),
            self.ID.Retry: pl.Int64(),
            self.ID.Memory: pl.Int64(),
            self.ID.PID: pl.Int64(),
            self.ID.Auditor: ForeignKey(pl.String, reference=f'"{UserAPI.Schema}"."{UserAPI.Table}"("{UserAPI.ID.UID}")'),
            self.ID.LID: ForeignKey(pl.String, reference=f'"{LogAPI.Schema}"."{LogAPI.Table}"("{LogAPI.ID.UID}") ON DELETE SET NULL'),
            self.ID.Log: pl.String(),
            self.ID.Progress: pl.Float64(),
            self.ID.Stage: pl.String(),
            self.ID.Remaining: pl.Float64(),
            **super().Structure
        }

    def _resolve_(self, event: RunEvent, by: str) -> bool:
        if self.Status not in (RunStatus.Approving.name, RunStatus.Reviewing.name): return False
        machine = RunAPI.machine()
        machine.perform(RunEvent.Start, None)
        machine.perform(RunEvent.RequireApproval if self.Status == RunStatus.Approving.name else RunEvent.RequireReview, None)
        machine.perform(event, None)
        self.Status, self.Auditor, self.StoppedAt = machine.At.Name, by, self.StoppedAt or datetime.now()
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