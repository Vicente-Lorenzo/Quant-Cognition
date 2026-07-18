from __future__ import annotations

import uuid
from datetime import datetime
from typing import Union

from Library.Logging import HandlerLoggingAPI
from Library.Utility.Runtime import terminate
from Library.Scheduler.Workflow import WorkflowAPI, Kind
from Library.Scheduler.Task import TaskAPI
from Library.Scheduler.Dependency import DependencyAPI
from Library.Scheduler.Cycle import CycleAPI
from Library.Scheduler.Run import RunAPI, RunStatus, RunEvent
from Library.Scheduler.Executor import ExecutorAPI
from Library.Scheduler.Coordinator import CoordinatorAPI
from Library.Database import PostgresDatabaseAPI, QueryAPI
from Library.Utility.Typing import MISSING, Missing

class ManagerAPI:

    _OPEN_: tuple = (RunStatus.Running.name, RunStatus.Approving.name, RunStatus.Reviewing.name)

    def __init__(self, *, database: str = "Quant") -> None:
        self._database_ = database
        self._log_ = HandlerLoggingAPI(Class=type(self).__name__, Subclass=database)

    @staticmethod
    def _clean_(fields: dict) -> dict:
        return {key: value for key, value in fields.items() if value is not None}

    def _select_(self, schema: str, table: str, condition: Union[str, None] = None, parameters: Union[dict, None] = None, order: Union[str, None] = None, limit: Union[int, None] = None) -> list[dict]:
        with PostgresDatabaseAPI(database=self._database_) as db:
            frame = db.select(schema=schema, table=table, condition=condition, order=order, limit=limit, parameters=parameters, legacy=False)
        return frame.to_dicts()

    def fingerprint(self, schema: str, *tables: str, condition: Union[str, None] = None, parameters: Union[dict, None] = None) -> str:
        with PostgresDatabaseAPI(database=self._database_) as db:
            return "·".join(db.fingerprint(schema=schema, table=table, condition=condition, parameters=parameters) for table in tables)

    def _delete_(self, schema: str, table: str, condition: str, parameters: dict) -> None:
        with PostgresDatabaseAPI(database=self._database_) as db:
            db.execute(QueryAPI(f'DELETE FROM {db._target_(schema, table)} WHERE {condition}'), [parameters])

    def _erase_(self, schema: str, table: str, uid: str, columns: list) -> None:
        with PostgresDatabaseAPI(database=self._database_) as db:
            sets = ", ".join(f'"{column}" = NULL' for column in columns)
            db.execute(QueryAPI(f'UPDATE {db._target_(schema, table)} SET {sets} WHERE "UID" = :uid:'), [{"uid": uid}])

    def _save_(self, datapoint) -> None:
        with PostgresDatabaseAPI(database=self._database_) as db:
            datapoint._db_ = db
            datapoint.save(by="Manager")
        datapoint._db_ = None

    def _spawn_(self, tid: str, cycle: Union[str, None] = None, retry: int = 0, manual: bool = False) -> None:
        ExecutorAPI.spawn(tid, database=self._database_, cycle=cycle, retry=retry, manual=manual)

    @staticmethod
    def _coherent_(kind, schedule: Union[str, None]) -> None:
        parsed = Kind.parse(kind)
        if not isinstance(parsed, Kind): return
        if parsed is Kind.Scheduled and not schedule: raise ValueError("A Scheduled workflow requires a Schedule")
        if parsed is not Kind.Scheduled and schedule: raise ValueError(f"A {parsed.name} workflow cannot have a Schedule")

    def _lawful_(self, task: TaskAPI) -> None:
        kind = Kind.parse(task.Kind)
        if kind is not Kind.Scheduled and task.Schedule: raise ValueError(f"A {kind.name} task cannot have a Schedule")
        if kind is Kind.Manual and task.WID: raise ValueError("A Manual task cannot join a workflow")
        if task.WID:
            row = self.workflow(task.WID)
            if row is not None and Kind.parse(row["Kind"]) is Kind.Service and kind is not Kind.Service: raise ValueError("A Service workflow only accepts Service tasks")
        self._fit_(task.WID, task.Schedule)

    def _fit_(self, wid: Union[str, None], schedule: Union[str, None]) -> None:
        if not wid or not schedule: return
        row = self.workflow(wid)
        if row is None or not row["Schedule"]: return
        if not CoordinatorAPI.fits(row["Schedule"], schedule): raise ValueError(f"Task schedule '{schedule}' does not fit inside workflow schedule '{row['Schedule']}'")

    def task(self, uid: str) -> Union[dict, None]:
        rows = self._select_(TaskAPI.Schema, TaskAPI.Table, '"UID" = :uid:', {"uid": uid}, limit=1)
        return rows[0] if rows else None

    def tasks(self, *, workflow: Union[str, None, Missing] = MISSING, enabled: Union[bool, Missing] = MISSING) -> list[dict]:
        conditions, parameters = [], {}
        if workflow is None: conditions = conditions + ['"WID" IS NULL']
        elif workflow is not MISSING: conditions, parameters = conditions + ['"WID" = :wid:'], {**parameters, "wid": workflow}
        if enabled is not MISSING and enabled is not None: conditions, parameters = conditions + ['"Enabled" = :enabled:'], {**parameters, "enabled": enabled}
        return self._select_(TaskAPI.Schema, TaskAPI.Table, " AND ".join(conditions) or None, parameters or None, order='"UID" ASC')

    def create_task(self, **fields) -> TaskAPI:
        task = TaskAPI(**{**TaskAPI.DEFAULTS, **self._clean_(fields)})
        self._lawful_(task)
        self._save_(task)
        self._log_.info(lambda: f"Task Create: Saved ({task.UID}) · {task.Name}")
        return task

    def update_task(self, uid: str, **fields) -> Union[TaskAPI, None]:
        row = self.task(uid)
        if row is None: return None
        task = TaskAPI(**{**self._clean_(row), **fields})
        self._lawful_(task)
        self._save_(task)
        cleared = [name for name, value in fields.items() if value is None and row.get(name) is not None]
        if cleared: self._erase_(TaskAPI.Schema, TaskAPI.Table, uid, cleared)
        self._log_.info(lambda: f"Task Update: Saved ({uid})")
        return task

    def delete_task(self, uid: str) -> bool:
        if self.task(uid) is None: return False
        self._delete_(DependencyAPI.Schema, DependencyAPI.Table, '"Predecessor" = :a: OR "Successor" = :b:', {"a": uid, "b": uid})
        self._delete_(RunAPI.Schema, RunAPI.Table, '"TID" = :uid:', {"uid": uid})
        self._delete_(TaskAPI.Schema, TaskAPI.Table, '"UID" = :uid:', {"uid": uid})
        self._log_.info(lambda: f"Task Delete: Removed ({uid})")
        return True

    def enable_task(self, uid: str) -> bool:
        return self.update_task(uid, Enabled=True) is not None

    def disable_task(self, uid: str) -> bool:
        return self.update_task(uid, Enabled=False) is not None

    def run_task(self, uid: str, *, wait: bool = False) -> Union[RunAPI, None]:
        row = self.task(uid)
        if row is None or Kind.parse(row["Kind"]) is Kind.Service: return None
        cid = None
        if row["WID"] is not None:
            cycles = self.cycles(workflow=row["WID"], limit=1)
            if cycles and cycles[0]["Status"] in self._OPEN_: cid = cycles[0]["UID"]
        if wait: return ExecutorAPI(database=self._database_).run(TaskAPI(**self._clean_(row)), cycle=cid, manual=True)
        self._spawn_(uid, cycle=cid, manual=True)
        self._log_.info(lambda: f"Task Run: Dispatched ({uid})")
        return None

    @staticmethod
    def _outcome_(task: dict, failure: bool) -> str:
        machine = RunAPI.machine()
        machine.perform(RunEvent.Start, None)
        if failure: machine.perform(RunEvent.RequireReview if task["RequiresReview"] else RunEvent.Fail, None)
        else: machine.perform(RunEvent.RequireApproval if task["RequiresApproval"] else RunEvent.Complete, None)
        return machine.At.Name

    def skip(self, uid: str, *, failure: bool = False, by: Union[str, None] = None) -> Union[RunAPI, None]:
        row = self.task(uid)
        if row is None or Kind.parse(row["Kind"]) is Kind.Service: return None
        cid = None
        if row["WID"] is not None:
            cycles = self.cycles(workflow=row["WID"], limit=1)
            if not cycles or cycles[0]["Status"] not in self._OPEN_: return None
            cid = cycles[0]["UID"]
        now = datetime.now()
        run = RunAPI(UID=uuid.uuid4().hex, CID=cid, TID=uid, Kind=Kind.Manual.name, Retry=0, Duration=0.0, Auditor=by, StartedAt=now, StoppedAt=now)
        run.Status = self._outcome_(row, failure)
        self._save_(run)
        self._log_.info(lambda run=run: f"Task Skip: {run.Status} ({uid})")
        return run

    def workflow(self, uid: str) -> Union[dict, None]:
        rows = self._select_(WorkflowAPI.Schema, WorkflowAPI.Table, '"UID" = :uid:', {"uid": uid}, limit=1)
        return rows[0] if rows else None

    def workflows(self, *, enabled: Union[bool, Missing] = MISSING) -> list[dict]:
        conditions, parameters = [], {}
        if enabled is not MISSING and enabled is not None: conditions, parameters = ['"Enabled" = :enabled:'], {"enabled": enabled}
        return self._select_(WorkflowAPI.Schema, WorkflowAPI.Table, " AND ".join(conditions) or None, parameters or None, order='"UID" ASC')

    def create_workflow(self, **fields) -> WorkflowAPI:
        fields = {**WorkflowAPI.DEFAULTS, **self._clean_(fields)}
        if not fields.get("Kind"): fields["Kind"] = Kind.Scheduled.name if fields.get("Schedule") else Kind.Manual.name
        workflow = WorkflowAPI(**fields)
        self._coherent_(workflow.Kind, workflow.Schedule)
        self._save_(workflow)
        self._log_.info(lambda: f"Workflow Create: Saved ({workflow.UID}) · {workflow.Name}")
        return workflow

    def update_workflow(self, uid: str, **fields) -> Union[WorkflowAPI, None]:
        row = self.workflow(uid)
        if row is None: return None
        workflow = WorkflowAPI(**{**self._clean_(row), **fields})
        self._coherent_(workflow.Kind, workflow.Schedule)
        members = self.tasks(workflow=uid)
        if Kind.parse(workflow.Kind) is Kind.Service and any(Kind.parse(member["Kind"]) is not Kind.Service for member in members): raise ValueError("A Service workflow only accepts Service tasks")
        if workflow.Schedule:
            for member in members:
                if member["Schedule"] and not CoordinatorAPI.fits(workflow.Schedule, member["Schedule"]): raise ValueError(f"Task schedule '{member['Schedule']}' of '{member['UID']}' does not fit inside workflow schedule '{workflow.Schedule}'")
        self._save_(workflow)
        cleared = [name for name, value in fields.items() if value is None and row.get(name) is not None]
        if cleared: self._erase_(WorkflowAPI.Schema, WorkflowAPI.Table, uid, cleared)
        self._log_.info(lambda: f"Workflow Update: Saved ({uid})")
        return workflow

    def delete_workflow(self, uid: str) -> bool:
        if self.workflow(uid) is None: return False
        self._delete_(DependencyAPI.Schema, DependencyAPI.Table, '"WID" = :uid:', {"uid": uid})
        with PostgresDatabaseAPI(database=self._database_) as db:
            db.execute(QueryAPI(f'UPDATE {db._target_(TaskAPI.Schema, TaskAPI.Table)} SET "WID" = NULL WHERE "WID" = :uid:'), [{"uid": uid}])
            db.execute(QueryAPI(f'UPDATE {db._target_(RunAPI.Schema, RunAPI.Table)} SET "CID" = NULL WHERE "CID" IN (SELECT "UID" FROM {db._target_(CycleAPI.Schema, CycleAPI.Table)} WHERE "WID" = :uid:)'), [{"uid": uid}])
        self._delete_(CycleAPI.Schema, CycleAPI.Table, '"WID" = :uid:', {"uid": uid})
        self._delete_(WorkflowAPI.Schema, WorkflowAPI.Table, '"UID" = :uid:', {"uid": uid})
        self._log_.info(lambda: f"Workflow Delete: Removed ({uid})")
        return True

    def enable_workflow(self, uid: str) -> bool:
        return self.update_workflow(uid, Enabled=True) is not None

    def disable_workflow(self, uid: str) -> bool:
        return self.update_workflow(uid, Enabled=False) is not None

    def run_workflow(self, uid: str) -> Union[str, None]:
        if self.workflow(uid) is None: return None
        members = self.tasks(workflow=uid, enabled=True)
        rows = {member["UID"]: member for member in members if Kind.parse(member["Kind"]) is Kind.Scheduled}
        with PostgresDatabaseAPI(database=self._database_) as db:
            edges = CoordinatorAPI.edges(db, uid)
            cid = uuid.uuid4().hex
            CycleAPI(UID=cid, WID=uid, Kind=Kind.Manual.name, Status=RunStatus.Running.name, StartedAt=datetime.now(), db=db).save(by="Manager")
        waits = {member: row["Waits"] is not False for member, row in rows.items()}
        tolerates = {member: row["Tolerates"] is not False for member, row in rows.items()}
        for tid in CoordinatorAPI.eligible(list(rows), edges, {}, waits=waits, tolerates=tolerates): self._spawn_(tid, cycle=cid)
        self._log_.info(lambda: f"Workflow Run: Dispatched ({uid}) · {cid}")
        return cid

    def cycle(self, uid: str) -> Union[dict, None]:
        rows = self._select_(CycleAPI.Schema, CycleAPI.Table, '"UID" = :uid:', {"uid": uid}, limit=1)
        return rows[0] if rows else None

    def cycles(self, *, workflow: Union[str, Missing] = MISSING, limit: Union[int, None] = None) -> list[dict]:
        conditions, parameters = [], {}
        if workflow is not MISSING and workflow is not None: conditions, parameters = ['"WID" = :wid:'], {"wid": workflow}
        return self._select_(CycleAPI.Schema, CycleAPI.Table, " AND ".join(conditions) or None, parameters or None, order='"StartedAt" DESC', limit=limit)

    def dependencies(self, uid: str) -> list[dict]:
        return self._select_(DependencyAPI.Schema, DependencyAPI.Table, '"WID" = :uid:', {"uid": uid})

    def link(self, uid: str, predecessor: str, successor: str) -> Union[DependencyAPI, None]:
        with PostgresDatabaseAPI(database=self._database_) as db:
            dependency = CoordinatorAPI.link(db, uid, predecessor, successor, by="Manager")
        if dependency is not None: self._log_.info(lambda: f"Workflow Link: Added ({uid}) · {predecessor} → {successor}")
        return dependency

    def unlink(self, uid: str, predecessor: str, successor: str) -> bool:
        self._delete_(DependencyAPI.Schema, DependencyAPI.Table, '"WID" = :uid: AND "Predecessor" = :p: AND "Successor" = :s:', {"uid": uid, "p": predecessor, "s": successor})
        self._log_.info(lambda: f"Workflow Unlink: Removed ({uid}) · {predecessor} → {successor}")
        return True

    def run(self, uid: str) -> Union[dict, None]:
        rows = self._select_(RunAPI.Schema, RunAPI.Table, '"UID" = :uid:', {"uid": uid}, limit=1)
        return rows[0] if rows else None

    def latest(self) -> dict:
        with PostgresDatabaseAPI(database=self._database_) as db:
            frame = db.executeone(QueryAPI(f'SELECT DISTINCT ON ("TID") "TID", "Status" FROM {db._target_(RunAPI.Schema, RunAPI.Table)} ORDER BY "TID", "StartedAt" DESC'), schema=RunAPI.Schema, table=RunAPI.Table).fetchall(legacy=False)
        return {row["TID"]: row["Status"] for row in frame.to_dicts()}

    def runs(self, *, task: Union[str, Missing] = MISSING, cycle: Union[str, None, Missing] = MISSING, status: Union[str, Missing] = MISSING, limit: Union[int, None] = None) -> list[dict]:
        conditions, parameters = [], {}
        if task is not MISSING and task is not None: conditions, parameters = conditions + ['"TID" = :tid:'], {**parameters, "tid": task}
        if cycle is None: conditions = conditions + ['"CID" IS NULL']
        elif cycle is not MISSING: conditions, parameters = conditions + ['"CID" = :cid:'], {**parameters, "cid": cycle}
        if status is not MISSING and status is not None: conditions, parameters = conditions + ['"Status" = :status:'], {**parameters, "status": status}
        return self._select_(RunAPI.Schema, RunAPI.Table, " AND ".join(conditions) or None, parameters or None, order='"StartedAt" DESC', limit=limit)

    def cancel(self, uid: str, *, failure: bool = False, by: Union[str, None] = None) -> bool:
        row = self.run(uid)
        if row is None or row["Status"] not in RunAPI.Live: return False
        task = self.task(row["TID"])
        if task is None: return False
        terminate(row["PID"])
        now = datetime.now()
        duration = (now - row["StartedAt"]).total_seconds() if row["StartedAt"] else None
        run = RunAPI(UID=uid, CID=row["CID"], TID=row["TID"], Kind=Kind.Manual.name, ExitCode=row["ExitCode"], Retry=row["Retry"], Duration=duration, PID=row["PID"], Auditor=by, Log=row["Log"], StartedAt=row["StartedAt"], StoppedAt=now)
        run.Status = self._outcome_(task, failure)
        self._save_(run)
        self._log_.info(lambda run=run: f"Run Cancel: {run.Status} ({uid})")
        return True

    def approve(self, uid: str, by: Union[str, None] = None) -> bool:
        with PostgresDatabaseAPI(database=self._database_) as db:
            run = RunAPI(UID=uid, db=db, autoload=True)
            resolved = run.accept(by) if run.Status is not None else False
        if resolved: self._log_.info(lambda: f"Run Approve: Accepted ({uid}) · {by}")
        return resolved

    def reject(self, uid: str, by: Union[str, None] = None) -> bool:
        with PostgresDatabaseAPI(database=self._database_) as db:
            run = RunAPI(UID=uid, db=db, autoload=True)
            resolved = run.reject(by) if run.Status is not None else False
        if resolved: self._log_.info(lambda: f"Run Reject: Rejected ({uid}) · {by}")
        return resolved