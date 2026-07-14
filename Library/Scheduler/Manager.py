from __future__ import annotations

import uuid
from typing import Union

from Library.Logging import HandlerLoggingAPI
from Library.Scheduler.Task import TaskAPI
from Library.Scheduler.Workflow import WorkflowAPI
from Library.Scheduler.Dependency import DependencyAPI
from Library.Scheduler.Run import RunAPI
from Library.Scheduler.Executor import ExecutorAPI
from Library.Scheduler.Coordinator import CoordinatorAPI
from Library.Database import PostgresDatabaseAPI, QueryAPI

class ManagerAPI:

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

    def fingerprint(self, schema: str, table: str, condition: Union[str, None] = None, parameters: Union[dict, None] = None) -> str:
        with PostgresDatabaseAPI(database=self._database_) as db:
            return db.fingerprint(schema=schema, table=table, condition=condition, parameters=parameters)

    def _delete_(self, schema: str, table: str, condition: str, parameters: dict) -> None:
        with PostgresDatabaseAPI(database=self._database_) as db:
            db.execute(QueryAPI(f'DELETE FROM {db._target_(schema, table)} WHERE {condition}'), [parameters])

    def _save_(self, datapoint) -> None:
        with PostgresDatabaseAPI(database=self._database_) as db:
            datapoint._db_ = db
            datapoint.save(by="Manager")
        datapoint._db_ = None

    def _spawn_(self, tid: str, workflow_run: Union[str, None] = None, attempt: int = 1) -> None:
        ExecutorAPI.spawn(tid, database=self._database_, workflow_run=workflow_run, attempt=attempt)

    def task(self, uid: str) -> Union[dict, None]:
        rows = self._select_(TaskAPI.Schema, TaskAPI.Table, '"UID" = :uid:', {"uid": uid}, limit=1)
        return rows[0] if rows else None

    def tasks(self, *, workflow: Union[str, None] = None, enabled: Union[bool, None] = None) -> list[dict]:
        conditions, parameters = [], {}
        if workflow is not None: conditions, parameters = conditions + ['"WID" = :wid:'], {**parameters, "wid": workflow}
        if enabled is not None: conditions, parameters = conditions + ['"Enabled" = :enabled:'], {**parameters, "enabled": enabled}
        return self._select_(TaskAPI.Schema, TaskAPI.Table, " AND ".join(conditions) or None, parameters or None, order='"UID" ASC')

    def create_task(self, **fields) -> TaskAPI:
        task = TaskAPI(**self._clean_(fields))
        self._save_(task)
        self._log_.info(lambda: f"Task Create: Saved ({task.UID}) · {task.Name}")
        return task

    def update_task(self, uid: str, **fields) -> Union[TaskAPI, None]:
        row = self.task(uid)
        if row is None: return None
        task = TaskAPI(**self._clean_({**row, **fields}))
        self._save_(task)
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
        if row is None: return None
        if wait: return ExecutorAPI(database=self._database_).run(TaskAPI(**self._clean_(row)))
        self._spawn_(uid)
        self._log_.info(lambda: f"Task Run: Dispatched ({uid})")
        return None

    def workflow(self, uid: str) -> Union[dict, None]:
        rows = self._select_(WorkflowAPI.Schema, WorkflowAPI.Table, '"UID" = :uid:', {"uid": uid}, limit=1)
        return rows[0] if rows else None

    def workflows(self, *, enabled: Union[bool, None] = None) -> list[dict]:
        conditions, parameters = [], {}
        if enabled is not None: conditions, parameters = ['"Enabled" = :enabled:'], {"enabled": enabled}
        return self._select_(WorkflowAPI.Schema, WorkflowAPI.Table, " AND ".join(conditions) or None, parameters or None, order='"UID" ASC')

    def create_workflow(self, **fields) -> WorkflowAPI:
        workflow = WorkflowAPI(**self._clean_(fields))
        self._save_(workflow)
        self._log_.info(lambda: f"Workflow Create: Saved ({workflow.UID}) · {workflow.Name}")
        return workflow

    def update_workflow(self, uid: str, **fields) -> Union[WorkflowAPI, None]:
        row = self.workflow(uid)
        if row is None: return None
        workflow = WorkflowAPI(**self._clean_({**row, **fields}))
        self._save_(workflow)
        self._log_.info(lambda: f"Workflow Update: Saved ({uid})")
        return workflow

    def delete_workflow(self, uid: str) -> bool:
        if self.workflow(uid) is None: return False
        self._delete_(DependencyAPI.Schema, DependencyAPI.Table, '"WID" = :uid:', {"uid": uid})
        with PostgresDatabaseAPI(database=self._database_) as db:
            db.execute(QueryAPI(f'UPDATE {db._target_(TaskAPI.Schema, TaskAPI.Table)} SET "WID" = NULL WHERE "WID" = :uid:'), [{"uid": uid}])
        self._delete_(WorkflowAPI.Schema, WorkflowAPI.Table, '"UID" = :uid:', {"uid": uid})
        self._log_.info(lambda: f"Workflow Delete: Removed ({uid})")
        return True

    def enable_workflow(self, uid: str) -> bool:
        return self.update_workflow(uid, Enabled=True) is not None

    def disable_workflow(self, uid: str) -> bool:
        return self.update_workflow(uid, Enabled=False) is not None

    def run_workflow(self, uid: str) -> Union[str, None]:
        if self.workflow(uid) is None: return None
        members = [row["UID"] for row in self.tasks(workflow=uid, enabled=True)]
        with PostgresDatabaseAPI(database=self._database_) as db:
            edges = CoordinatorAPI.edges(db, uid)
        workflow_run = uuid.uuid4().hex
        for tid in CoordinatorAPI.eligible(members, edges, {}): self._spawn_(tid, workflow_run=workflow_run)
        self._log_.info(lambda: f"Workflow Run: Dispatched ({uid}) · {workflow_run}")
        return workflow_run

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

    def runs(self, *, task: Union[str, None] = None, workflow_run: Union[str, None] = None, status: Union[str, None] = None, limit: Union[int, None] = None) -> list[dict]:
        conditions, parameters = [], {}
        if task is not None: conditions, parameters = conditions + ['"TID" = :tid:'], {**parameters, "tid": task}
        if workflow_run is not None: conditions, parameters = conditions + ['"WorkflowRun" = :wr:'], {**parameters, "wr": workflow_run}
        if status is not None: conditions, parameters = conditions + ['"Status" = :status:'], {**parameters, "status": status}
        return self._select_(RunAPI.Schema, RunAPI.Table, " AND ".join(conditions) or None, parameters or None, order='"StartedAt" DESC', limit=limit)

    def approve(self, uid: str, by: str = "CLI") -> bool:
        with PostgresDatabaseAPI(database=self._database_) as db:
            run = RunAPI(UID=uid, db=db, autoload=True)
            resolved = run.accept(by) if run.Status is not None else False
        if resolved: self._log_.info(lambda: f"Run Approve: Accepted ({uid}) · {by}")
        return resolved

    def reject(self, uid: str, by: str = "CLI") -> bool:
        with PostgresDatabaseAPI(database=self._database_) as db:
            run = RunAPI(UID=uid, db=db, autoload=True)
            resolved = run.reject(by) if run.Status is not None else False
        if resolved: self._log_.info(lambda: f"Run Reject: Rejected ({uid}) · {by}")
        return resolved