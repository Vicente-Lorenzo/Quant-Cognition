import uuid
from typing import Union

from Library.Utility.Datetime import utc_now, zones
from Library.Logging import LoggingAPI
from Library.Utility.Runtime import terminate
from Library.Scheduler.Workflow import WorkflowAPI, Kind
from Library.Scheduler.Task import TaskAPI
from Library.Scheduler.Dependency import DependencyAPI
from Library.Scheduler.Cycle import CycleAPI
from Library.Scheduler.Run import RunAPI, RetentionLevel
from Library.Scheduler.Executor import ExecutorAPI
from Library.Scheduler.Coordinator import CoordinatorAPI
from Library.Database import PostgresDatabaseAPI, QueryAPI
from Library.Utility.Typing import MISSING, Missing

class ManagerAPI:

    def __init__(self, *, database: str = "Quant") -> None:
        self._database_ = database
        self._log_ = LoggingAPI(database)

    def scope(self):
        return PostgresDatabaseAPI.scope(database=self._database_)

    @staticmethod
    def _clean_(fields: dict) -> dict:
        return {key: value for key, value in fields.items() if value is not None}

    def _select_(self, model, *, order: Union[str, None] = None, limit: Union[int, None] = None, **columns) -> list[dict]:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            condition, parameters = db.where(**columns)
            return db.records(schema=model.Schema, table=model.Table, condition=condition, order=order, limit=limit, parameters=parameters)

    def _one_(self, model, uid: str) -> Union[dict, None]:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            condition, parameters = db.where(UID=uid)
            return db.first(schema=model.Schema, table=model.Table, condition=condition, parameters=parameters)

    def _recent_(self, model, key: str) -> dict:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            frame = db.executeone(QueryAPI(f'SELECT DISTINCT ON ("{key}") "{key}", "Status" FROM {db._target_(model.Schema, model.Table)} ORDER BY "{key}", "StartedAt" DESC NULLS LAST'), schema=model.Schema, table=model.Table).fetchall(legacy=False)
        return {row[key]: row["Status"] for row in frame.to_dicts()}

    def fingerprint(self, schema: str, *tables: str, condition: Union[str, None] = None, parameters: Union[dict, None] = None) -> str:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            return "·".join(db.fingerprint(schema=schema, table=table, condition=condition, parameters=parameters) for table in tables)

    def _delete_(self, schema: str, table: str, condition: str, parameters: dict) -> None:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            db.remove(schema=schema, table=table, condition=condition, parameters=parameters)

    def _erase_(self, model, uid: str, row: dict, fields: dict) -> None:
        cleared = [name for name, value in fields.items() if value is None and row.get(name) is not None]
        if not cleared: return
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            db.update(schema=model.Schema, table=model.Table, data={column: None for column in cleared}, condition='"UID" = :uid:', parameters={"uid": uid})

    def _save_(self, datapoint) -> None:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            datapoint._db_ = db
            datapoint.save(by="Manager")
        datapoint._db_ = None

    def _spawn_(self, tid: str, cycle: Union[str, None] = None, retry: int = 0, manual: bool = False, arguments: Union[str, None] = None) -> None:
        ExecutorAPI.spawn(tid, database=self._database_, cycle=cycle, retry=retry, manual=manual, arguments=arguments)

    @staticmethod
    def _coherent_(kind, schedule: Union[str, None]) -> None:
        parsed = Kind.parse(kind)
        if not isinstance(parsed, Kind): return
        if parsed is Kind.Scheduled and not schedule: raise ValueError("A Scheduled workflow requires a Schedule")
        if parsed is not Kind.Scheduled and schedule: raise ValueError(f"A {parsed.name} workflow cannot have a Schedule")

    @staticmethod
    def _zoned_(zone: Union[str, None]) -> None:
        if zone and zone not in zones(): raise ValueError(f"Unknown time zone '{zone}'")

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
        if not CoordinatorAPI.fits(row["Schedule"], schedule, zone=row.get("Zone")): raise ValueError(f"Task schedule '{schedule}' does not fit inside workflow schedule '{row['Schedule']}'")

    def task(self, uid: str) -> Union[dict, None]:
        return self._one_(TaskAPI, uid)

    def tasks(self, *, workflow: Union[str, None, Missing] = MISSING, enabled: Union[bool, Missing] = MISSING) -> list[dict]:
        return self._select_(TaskAPI, order='"UID" ASC', WID=workflow, Enabled=MISSING if enabled is None else enabled)

    def create_task(self, **fields) -> TaskAPI:
        task = TaskAPI(**{**TaskAPI.Defaults, **self._clean_(fields)})
        self._lawful_(task)
        self._save_(task)
        self._log_.info(lambda: f"Task Create: Saved ({task.UID}) · {task.Name}")
        return task

    def update_task(self, uid: str, **fields) -> Union[TaskAPI, None]:
        row = self.task(uid)
        if row is None: return None
        task = TaskAPI.parse(row, **fields)
        self._lawful_(task)
        self._save_(task)
        self._erase_(TaskAPI, uid, row, fields)
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

    def run_task(self, uid: str, *, wait: bool = False, arguments: Union[str, None] = None) -> Union[RunAPI, None]:
        row = self.task(uid)
        if row is None or Kind.parse(row["Kind"]) is Kind.Service: return None
        cid = None
        if row["WID"] is not None:
            cycles = self.cycles(workflow=row["WID"], limit=1)
            if cycles and cycles[0]["Status"] in RunAPI.Open: cid = cycles[0]["UID"]
        if wait: return ExecutorAPI(database=self._database_).run(TaskAPI.parse(row), cycle=cid, manual=True, arguments=arguments)
        self._spawn_(uid, cycle=cid, manual=True, arguments=arguments)
        self._log_.info(lambda: f"Task Run: Dispatched ({uid})")
        return None

    def skip(self, uid: str, *, failure: bool = False, by: Union[str, None] = None) -> Union[RunAPI, None]:
        row = self.task(uid)
        if row is None or Kind.parse(row["Kind"]) is Kind.Service: return None
        cid = None
        if row["WID"] is not None:
            cycles = self.cycles(workflow=row["WID"], limit=1)
            if not cycles or cycles[0]["Status"] not in RunAPI.Open: return None
            cid = cycles[0]["UID"]
        now = utc_now()
        run = RunAPI(UID=uuid.uuid4().hex, CID=cid, TID=uid, Kind=Kind.Manual.name, Retry=0, Duration=0.0, Auditor=by, StartedAt=now, StoppedAt=now)
        run.Status = RunAPI.outcome(failure=failure, approval=row["RequiresApproval"], review=row["RequiresReview"])
        self._save_(run)
        self._log_.info(lambda run=run: f"Task Skip: {run.Status} ({uid})")
        return run

    def workflow(self, uid: str) -> Union[dict, None]:
        return self._one_(WorkflowAPI, uid)

    def workflows(self, *, enabled: Union[bool, Missing] = MISSING) -> list[dict]:
        return self._select_(WorkflowAPI, order='"UID" ASC', Enabled=MISSING if enabled is None else enabled)

    def create_workflow(self, **fields) -> WorkflowAPI:
        fields = {**WorkflowAPI.Defaults, **self._clean_(fields)}
        if not fields.get("Kind"): fields["Kind"] = Kind.Scheduled.name if fields.get("Schedule") else Kind.Manual.name
        workflow = WorkflowAPI(**fields)
        self._coherent_(workflow.Kind, workflow.Schedule)
        self._zoned_(workflow.Zone)
        self._save_(workflow)
        self._log_.info(lambda: f"Workflow Create: Saved ({workflow.UID}) · {workflow.Name}")
        return workflow

    def update_workflow(self, uid: str, **fields) -> Union[WorkflowAPI, None]:
        row = self.workflow(uid)
        if row is None: return None
        workflow = WorkflowAPI.parse(row, **fields)
        self._coherent_(workflow.Kind, workflow.Schedule)
        self._zoned_(workflow.Zone)
        members = self.tasks(workflow=uid)
        if Kind.parse(workflow.Kind) is Kind.Service and any(Kind.parse(member["Kind"]) is not Kind.Service for member in members): raise ValueError("A Service workflow only accepts Service tasks")
        if workflow.Schedule:
            for member in members:
                if member["Schedule"] and not CoordinatorAPI.fits(workflow.Schedule, member["Schedule"], zone=workflow.Zone): raise ValueError(f"Task schedule '{member['Schedule']}' of '{member['UID']}' does not fit inside workflow schedule '{workflow.Schedule}'")
        self._save_(workflow)
        self._erase_(WorkflowAPI, uid, row, fields)
        self._log_.info(lambda: f"Workflow Update: Saved ({uid})")
        return workflow

    def delete_workflow(self, uid: str) -> bool:
        if self.workflow(uid) is None: return False
        self._delete_(DependencyAPI.Schema, DependencyAPI.Table, '"WID" = :uid:', {"uid": uid})
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            db.update(schema=TaskAPI.Schema, table=TaskAPI.Table, data={"WID": None}, condition='"WID" = :uid:', parameters={"uid": uid})
            db.update(schema=RunAPI.Schema, table=RunAPI.Table, data={"CID": None}, condition=f'"CID" IN (SELECT "UID" FROM {db._target_(CycleAPI.Schema, CycleAPI.Table)} WHERE "WID" = :uid:)', parameters={"uid": uid})
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
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            edges = CoordinatorAPI.edges(db, uid)
            cid = CycleAPI.start(db, uid, Kind.Manual.name, utc_now(), "Manager").UID
        waits, tolerates = CoordinatorAPI.gates(rows)
        for tid in CoordinatorAPI.eligible(list(rows), edges, {}, waits=waits, tolerates=tolerates): self._spawn_(tid, cycle=cid)
        self._log_.info(lambda: f"Workflow Run: Dispatched ({uid}) · {cid}")
        return cid

    def cycle(self, uid: str) -> Union[dict, None]:
        return self._one_(CycleAPI, uid)

    def cycles(self, *, workflow: Union[str, Missing] = MISSING, limit: Union[int, None] = None) -> list[dict]:
        return self._select_(CycleAPI, order='"StartedAt" DESC NULLS LAST', limit=limit, WID=MISSING if workflow is None else workflow)

    def dependencies(self, uid: str) -> list[dict]:
        return self._select_(DependencyAPI, WID=uid)

    def link(self, uid: str, predecessor: str, successor: str) -> Union[DependencyAPI, None]:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            dependency = CoordinatorAPI.link(db, uid, predecessor, successor, by="Manager")
        if dependency is not None: self._log_.info(lambda: f"Workflow Link: Added ({uid}) · {predecessor} → {successor}")
        return dependency

    def unlink(self, uid: str, predecessor: str, successor: str) -> bool:
        self._delete_(DependencyAPI.Schema, DependencyAPI.Table, '"WID" = :uid: AND "Predecessor" = :p: AND "Successor" = :s:', {"uid": uid, "p": predecessor, "s": successor})
        self._log_.info(lambda: f"Workflow Unlink: Removed ({uid}) · {predecessor} → {successor}")
        return True

    def run(self, uid: str) -> Union[dict, None]:
        return self._one_(RunAPI, uid)

    def delete_run(self, uid: str) -> bool:
        row = self.run(uid)
        if row is None: return False
        if row["Status"] in RunAPI.Active: return False
        self._delete_(RunAPI.Schema, RunAPI.Table, '"UID" = :uid:', {"uid": uid})
        self._log_.info(lambda: f"Run Delete: Removed ({uid})")
        return True

    def latest(self) -> dict:
        return self._recent_(RunAPI, "TID")

    def cycled(self) -> dict:
        return self._recent_(CycleAPI, "WID")

    def runs(self, *, task: Union[str, Missing] = MISSING, cycle: Union[str, None, Missing] = MISSING, status: Union[str, Missing] = MISSING, limit: Union[int, None] = None) -> list[dict]:
        return self._select_(RunAPI, order='"StartedAt" DESC NULLS LAST', limit=limit, TID=MISSING if task is None else task, CID=cycle, Status=MISSING if status is None else status)

    def retain(self, uid: str, *, level: Union[str, RetentionLevel] = RetentionLevel.Persistent) -> bool:
        row = self.run(uid)
        if row is None: return False
        resolved = RetentionLevel.parse(level)
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            db.update(schema=RunAPI.Schema, table=RunAPI.Table, data={"Retention": resolved.name}, condition='"UID" = :uid:', parameters={"uid": uid})
        if row["Status"] not in RunAPI.Active: self._settle_(uid, resolved)
        self._log_.info(lambda: f"Retain Run: Marked {resolved.name} ({uid})")
        return True

    def _settle_(self, uid: str, level: RetentionLevel) -> None:
        try: ExecutorAPI.relocate(uid, level is not RetentionLevel.Temporary)
        except Exception as error:
            self._log_.warning(lambda error=error: f"Retain Run: Unmoved ({uid}) · {error}")

    def retained(self) -> set:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            rows = db.records(schema=RunAPI.Schema, table=RunAPI.Table, condition='"Retention" IN (:persistent:, :favorite:)', parameters={"persistent": RetentionLevel.Persistent.name, "favorite": RetentionLevel.Favorite.name})
        return {row["UID"] for row in rows}

    def cancel(self, uid: str, *, failure: bool = False, by: Union[str, None] = None) -> bool:
        row = self.run(uid)
        if row is None or row["Status"] not in RunAPI.Live: return False
        task = self.task(row["TID"])
        if task is None: return False
        terminate(row["PID"])
        run = RunAPI.closed(row, utc_now(), Kind=Kind.Manual.name, Auditor=by, Status=RunAPI.outcome(failure=failure, approval=task["RequiresApproval"], review=task["RequiresReview"]))
        self._save_(run)
        self._log_.info(lambda run=run: f"Run Cancel: {run.Status} ({uid})")
        return True

    def approve(self, uid: str, by: Union[str, None] = None) -> bool:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            run = RunAPI(UID=uid, db=db, autoload=True)
            resolved = run.accept(by) if run.Status is not None else False
        if resolved: self._log_.info(lambda: f"Run Approve: Accepted ({uid}) · {by}")
        return resolved

    def reject(self, uid: str, by: Union[str, None] = None) -> bool:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            run = RunAPI(UID=uid, db=db, autoload=True)
            resolved = run.reject(by) if run.Status is not None else False
        if resolved: self._log_.info(lambda: f"Run Reject: Rejected ({uid}) · {by}")
        return resolved