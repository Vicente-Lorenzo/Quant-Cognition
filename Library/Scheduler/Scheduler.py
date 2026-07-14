from __future__ import annotations

import time
import uuid
import subprocess
from datetime import datetime, timedelta
from typing import Union

import psutil
from croniter import croniter

from Library.Logging import HandlerLoggingAPI
from Library.Scheduler.Task import TaskAPI, TaskKind
from Library.Scheduler.Workflow import WorkflowAPI
from Library.Scheduler.Run import RunAPI, RunStatus, RunEvent
from Library.Scheduler.Executor import ExecutorAPI
from Library.Scheduler.Coordinator import CoordinatorAPI
from Library.Database import PostgresDatabaseAPI

class SchedulerAPI:

    _INTERVAL_: int = 30
    _CONCURRENCY_: int = 4
    _LEASE_: int = 90
    _ACTIVE_: tuple = (RunStatus.Waiting.name, RunStatus.Running.name, RunStatus.Approving.name, RunStatus.Reviewing.name, RunStatus.Retrying.name)
    _BUSY_: tuple = (RunStatus.Waiting.name, RunStatus.Running.name)

    def __init__(self, *, database: str = "Quant", interval: Union[int, None] = None, concurrency: Union[int, None] = None) -> None:
        self._database_ = database
        self._interval_ = interval or self._INTERVAL_
        self._concurrency_ = concurrency or self._CONCURRENCY_
        self._services_ = {}
        self._running_ = False
        self._started_ = datetime.now()
        self._launch_ = None
        self._log_ = HandlerLoggingAPI(Class=type(self).__name__, Subclass=database)

    @staticmethod
    def _members_(status: tuple) -> str:
        return ", ".join(f"'{name}'" for name in status)

    @staticmethod
    def _due_(schedule: Union[str, None], last: Union[datetime, None], now: datetime) -> bool:
        if not schedule: return False
        if last is None: return True
        return croniter(schedule, last).get_next(datetime) <= now

    def _spawn_(self, tid: str, workflow_run: Union[str, None] = None, attempt: int = 1) -> subprocess.Popen:
        return ExecutorAPI.spawn(tid, database=self._database_, workflow_run=workflow_run, attempt=attempt)

    def _task_(self, db: PostgresDatabaseAPI, tid: str) -> TaskAPI:
        task = TaskAPI(UID=tid, db=db, autoload=True)
        task._db_ = None
        return task

    def _tasks_(self, db: PostgresDatabaseAPI) -> list[dict]:
        frame = db.select(schema=TaskAPI.Schema, table=TaskAPI.Table, condition='"Enabled" = :enabled:', parameters={"enabled": True}, legacy=False)
        return frame.to_dicts()

    def _latest_(self, db: PostgresDatabaseAPI, tid: str) -> Union[dict, None]:
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, condition='"TID" = :tid:', order='"StartedAt" DESC', limit=1, parameters={"tid": tid}, legacy=False)
        return None if frame.is_empty() else frame.row(0, named=True)

    def _dedup_(self, db: PostgresDatabaseAPI, tid: str) -> bool:
        row = self._latest_(db, tid)
        return row is not None and row["Status"] in self._ACTIVE_

    def _is_latest_(self, db: PostgresDatabaseAPI, row: dict) -> bool:
        condition = '"TID" = :tid: AND "StartedAt" > :started:'
        parameters = {"tid": row["TID"], "started": row["StartedAt"]}
        if row["WorkflowRun"] is None: condition += ' AND "WorkflowRun" IS NULL'
        else: condition, parameters = condition + ' AND "WorkflowRun" = :wr:', {**parameters, "wr": row["WorkflowRun"]}
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, columns=["UID"], condition=condition, limit=1, parameters=parameters, legacy=False)
        return frame.is_empty()

    def _retry_(self, db: PostgresDatabaseAPI, now: datetime, budget: int) -> int:
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, condition='"Status" = :retrying:', parameters={"retrying": RunStatus.Retrying.name}, legacy=False)
        for row in frame.to_dicts():
            if budget <= 0: break
            if not self._is_latest_(db, row): continue
            task = self._task_(db, row["TID"])
            if row["FinishedAt"] is None or row["FinishedAt"] + timedelta(seconds=task.RetryDelay or 0) > now: continue
            attempt = (row["Attempt"] or 1) + 1
            self._spawn_(row["TID"], workflow_run=row["WorkflowRun"], attempt=attempt)
            budget -= 1
            self._log_.info(lambda row=row, attempt=attempt: f"Run Retry: Dispatched ({row['TID']}) · Attempt {attempt}")
        return budget

    def _busy_(self, db: PostgresDatabaseAPI, scheduled: set) -> int:
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, columns=["TID"], condition=f'"Status" IN ({self._members_(self._BUSY_)})', legacy=False)
        return sum(1 for tid in frame["TID"].to_list() if tid in scheduled)

    def _reap_(self, db: PostgresDatabaseAPI, now: datetime) -> None:
        stale = now - timedelta(seconds=self._LEASE_)
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, condition=f'"Status" IN ({self._members_(self._BUSY_)}) AND "Heartbeat" < :stale:', parameters={"stale": stale}, legacy=False)
        for row in frame.to_dicts():
            task = self._task_(db, row["TID"])
            machine = RunAPI.machine()
            machine.perform(RunEvent.Start, None)
            if (row["Attempt"] or 1) < (task.MaxAttempts or 1): machine.perform(RunEvent.Retry, None)
            else: machine.perform(RunEvent.RequireReview if task.RequiresReview else RunEvent.Fail, None)
            duration = (now - row["StartedAt"]).total_seconds() if row["StartedAt"] else None
            run = RunAPI(UID=row["UID"], TID=row["TID"], WorkflowRun=row["WorkflowRun"], Status=machine.At.Name, Attempt=row["Attempt"], StartedAt=row["StartedAt"], FinishedAt=now, Duration=duration, db=db)
            run.save(by="Reaper")
            self._log_.warning(lambda row=row, run=run: f"Run Reap: {run.Status} ({row['UID']}) · Due to stale heartbeat")

    @staticmethod
    def _terminate_(handle: subprocess.Popen) -> None:
        try: parent = psutil.Process(handle.pid)
        except psutil.Error: return
        processes = parent.children(recursive=True) + [parent]
        for process in processes:
            try: process.terminate()
            except psutil.Error: pass
        for process in psutil.wait_procs(processes, timeout=5)[1]:
            try: process.kill()
            except psutil.Error: pass

    def _paused_(self, db: PostgresDatabaseAPI, tasks: list[dict]) -> set:
        governed = {task["UID"]: task["WID"] for task in tasks if task["WID"] is not None and TaskKind.parse(task["Kind"]) is TaskKind.Scheduled}
        if not governed: return set()
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, columns=["TID"], condition=f'"Status" IN ({self._members_(self._ACTIVE_)})', legacy=False)
        return {governed[tid] for tid in frame["TID"].to_list() if tid in governed}

    def _alive_(self, tid: str) -> bool:
        handle = self._services_.get(tid)
        return handle is not None and handle.poll() is None

    def _ready_(self, db: PostgresDatabaseAPI, task: dict, kinds: dict, edges: dict) -> bool:
        if task["WID"] is None: return True
        if task["WID"] not in edges: edges[task["WID"]] = CoordinatorAPI.edges(db, task["WID"])
        for predecessor, successor in edges[task["WID"]]:
            if successor != task["UID"]: continue
            if kinds.get(predecessor) is TaskKind.Service:
                if not self._alive_(predecessor): return False
            elif kinds.get(predecessor) is TaskKind.Scheduled:
                row = self._latest_(db, predecessor)
                if row is None or row["StartedAt"] is None or row["StartedAt"] < self._started_ or row["Status"] in self._ACTIVE_: return False
        return True

    def _service_(self, db: PostgresDatabaseAPI, tasks: list[dict], paused: set) -> None:
        kinds = {task["UID"]: TaskKind.parse(task["Kind"]) for task in tasks}
        edges = {}
        for task in tasks:
            if kinds[task["UID"]] is not TaskKind.Service: continue
            running = self._alive_(task["UID"])
            if task["WID"] in paused:
                if running: self._terminate_(self._services_[task["UID"]]); self._log_.info(lambda task=task: f"Service Suspend: Stopped ({task['Name']}) · Maintenance")
                self._services_.pop(task["UID"], None)
                continue
            if running: continue
            if not self._ready_(db, task, kinds, edges): continue
            self._services_[task["UID"]] = self._spawn_(task["UID"])
            self._log_.info(lambda task=task: f"Service Supervise: Spawned ({task['Name']}) · {task['Path']}")

    def _schedule_(self, db: PostgresDatabaseAPI, tasks: list[dict], now: datetime, budget: int) -> int:
        for task in tasks:
            if budget <= 0: break
            if task["WID"] is not None: continue
            if TaskKind.parse(task["Kind"]) is not TaskKind.Scheduled: continue
            if self._dedup_(db, task["UID"]): continue
            row = self._latest_(db, task["UID"])
            if not self._due_(task["Schedule"], row["StartedAt"] if row else None, now): continue
            self._spawn_(task["UID"])
            budget -= 1
            self._log_.info(lambda task=task: f"Task Schedule: Triggered ({task['Name']}) · {task['Schedule']}")
        return budget

    def _enabled_workflows_(self, db: PostgresDatabaseAPI) -> list[dict]:
        frame = db.select(schema=WorkflowAPI.Schema, table=WorkflowAPI.Table, condition='"Enabled" = :enabled:', parameters={"enabled": True}, legacy=False)
        return frame.to_dicts()

    def _workflow_runs_(self, db: PostgresDatabaseAPI, tids: list) -> list[dict]:
        if not tids: return []
        tokens = ", ".join(f":t{index}:" for index in range(len(tids)))
        parameters = {f"t{index}": tid for index, tid in enumerate(tids)}
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, condition=f'"TID" IN ({tokens})', parameters=parameters, legacy=False)
        return frame.to_dicts()

    def _advance_(self, db: PostgresDatabaseAPI, workflow: dict, members: list[dict], edges: list, now: datetime, budget: int) -> int:
        tids = [member["UID"] for member in members]
        scheduled = {member["UID"] for member in members if TaskKind.parse(member["Kind"]) is TaskKind.Scheduled}
        runs = [run for run in self._workflow_runs_(db, tids) if run["TID"] in scheduled]
        latest = max(runs, key=lambda run: run["StartedAt"] or datetime.min) if runs else None
        current = latest["WorkflowRun"] if latest else None
        grouped = sorted((run for run in runs if run["WorkflowRun"] == current), key=lambda run: (run["StartedAt"] or datetime.min, run["Attempt"] or 0))
        status = {run["TID"]: run["Status"] for run in grouped}
        pending = any(state in self._ACTIVE_ for state in status.values())
        ready = [tid for tid in CoordinatorAPI.eligible(tids, edges, status) if tid in scheduled]
        if current is not None and (pending or ready):
            for tid in ready:
                if budget <= 0: break
                self._spawn_(tid, workflow_run=current)
                budget -= 1
                self._log_.info(lambda workflow=workflow, tid=tid: f"Workflow Advance: Triggered ({workflow['Name']}) · {tid}")
            return budget
        launch = self._launch_ is not None and workflow["UID"] in self._launch_
        if launch or self._due_(workflow["Schedule"], latest["StartedAt"] if latest else None, now):
            if launch: self._launch_.discard(workflow["UID"])
            fresh = uuid.uuid4().hex
            for tid in CoordinatorAPI.eligible(tids, edges, {}):
                if tid not in scheduled: continue
                if budget <= 0: break
                self._spawn_(tid, workflow_run=fresh)
                budget -= 1
                self._log_.info(lambda workflow=workflow, tid=tid: f"Workflow Launch: Started ({workflow['Name']}) · {tid}")
        return budget

    def _workflows_(self, db: PostgresDatabaseAPI, tasks: list[dict], now: datetime, budget: int) -> int:
        for workflow in self._enabled_workflows_(db):
            if budget <= 0: break
            members = [task for task in tasks if task["WID"] == workflow["UID"]]
            if not members: continue
            budget = self._advance_(db, workflow, members, CoordinatorAPI.edges(db, workflow["UID"]), now, budget)
        return budget

    def _tick_(self) -> None:
        now = datetime.now()
        with PostgresDatabaseAPI(database=self._database_) as db:
            self._reap_(db, now)
            tasks = self._tasks_(db)
            if self._launch_ is None: self._launch_ = {task["WID"] for task in tasks if task["WID"] is not None and TaskKind.parse(task["Kind"]) is TaskKind.Service}
            self._service_(db, tasks, self._paused_(db, tasks))
            scheduled = {task["UID"] for task in tasks if TaskKind.parse(task["Kind"]) is TaskKind.Scheduled}
            budget = self._concurrency_ - self._busy_(db, scheduled)
            budget = self._retry_(db, now, budget)
            budget = self._schedule_(db, tasks, now, budget)
            self._workflows_(db, tasks, now, budget)

    def start(self) -> None:
        self._running_ = True
        self._log_.info(lambda: f"Scheduler Start: Running · {self._interval_}s Interval · {self._concurrency_} Concurrency")
        while self._running_:
            try: self._tick_()
            except Exception as error: self._log_.error(lambda: f"Scheduler Tick: Failed · Due to {error}")
            time.sleep(self._interval_)

    def stop(self) -> None:
        self._running_ = False
        for handle in list(self._services_.values()):
            if handle is not None and handle.poll() is None: self._terminate_(handle)
        self._services_.clear()
        self._log_.info(lambda: "Scheduler Stop: Halted · Services Terminated")