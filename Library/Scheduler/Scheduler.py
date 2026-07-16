from __future__ import annotations

import time
import uuid
import subprocess
from datetime import datetime, timedelta
from typing import Union

from croniter import croniter

from Library.Logging import HandlerLoggingAPI
from Library.Utility.Runtime import terminate
from Library.Scheduler.Workflow import WorkflowAPI, Kind
from Library.Scheduler.Task import TaskAPI
from Library.Scheduler.Cycle import CycleAPI
from Library.Scheduler.Run import RunAPI, RunStatus, RunEvent
from Library.Scheduler.Executor import ExecutorAPI
from Library.Scheduler.Coordinator import CoordinatorAPI
from Library.Database import PostgresDatabaseAPI
from Library.Utility.Typing import MISSING, Missing

class SchedulerAPI:

    Channel: str = "Scheduler"

    _INTERVAL_: int = 30
    _CONCURRENCY_: int = 4
    _LEASE_: int = 90
    _OPEN_: tuple = (RunStatus.Running.name, RunStatus.Approving.name, RunStatus.Reviewing.name)

    def __init__(self, *, database: str = "Quant", interval: Union[int, Missing] = MISSING, concurrency: Union[int, Missing] = MISSING) -> None:
        self._database_ = database
        self._interval_ = self._INTERVAL_ if interval is MISSING else interval
        self._concurrency_ = self._CONCURRENCY_ if concurrency is MISSING else concurrency
        self._services_ = {}
        self._spawns_ = {}
        self._crashes_ = {}
        self._issued_ = {}
        self._running_ = False
        self._started_ = datetime.now()
        self._launch_ = None
        self._listener_ = None
        self._log_ = HandlerLoggingAPI(Class=type(self).__name__, Subclass=database)

    def _listen_(self) -> Union[PostgresDatabaseAPI, None]:
        try:
            listener = PostgresDatabaseAPI(database=self._database_)
            listener.connect()
            listener.listen(channel=self.Channel)
            return listener
        except Exception as error:
            self._log_.warning(lambda error=error: f"Scheduler Listen: Failed · Due to {error} · Falling back to {self._interval_}s Polling")
            return None

    def _wait_(self) -> None:
        if self._listener_ is None:
            time.sleep(self._interval_)
            self._listener_ = self._listen_()
            return
        try:
            self._listener_.wait(timeout=self._interval_)
        except Exception:
            self._listener_ = None

    @staticmethod
    def _members_(status: tuple) -> str:
        return ", ".join(f"'{name}'" for name in status)

    @staticmethod
    def _due_(schedule: Union[str, None], last: Union[datetime, None], now: datetime) -> bool:
        if not schedule: return False
        if last is None: return True
        return croniter(schedule, last).get_next(datetime) <= now

    @staticmethod
    def _timely_(schedule: Union[str, None], opened: Union[datetime, None], now: datetime) -> bool:
        if not schedule: return True
        if opened is None: return False
        return croniter(schedule, opened - timedelta(seconds=1)).get_next(datetime) <= now

    def _issue_(self, key: tuple, now: datetime) -> bool:
        last = self._issued_.get(key)
        if last is not None and (now - last).total_seconds() < self._LEASE_: return False
        if len(self._issued_) > 1024: self._issued_ = {k: v for k, v in self._issued_.items() if (now - v).total_seconds() < self._LEASE_}
        self._issued_[key] = now
        return True

    def _spawn_(self, tid: str, cycle: Union[str, None] = None, retry: int = 0) -> subprocess.Popen:
        return ExecutorAPI.spawn(tid, database=self._database_, cycle=cycle, retry=retry)

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
        return row is not None and row["Status"] in RunAPI.Active

    def _is_latest_(self, db: PostgresDatabaseAPI, row: dict) -> bool:
        condition = '"TID" = :tid: AND "StartedAt" > :started:'
        parameters = {"tid": row["TID"], "started": row["StartedAt"]}
        if row["CID"] is None: condition += ' AND "CID" IS NULL'
        else: condition, parameters = condition + ' AND "CID" = :cid:', {**parameters, "cid": row["CID"]}
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, columns=["UID"], condition=condition, limit=1, parameters=parameters, legacy=False)
        return frame.is_empty()

    def _retry_(self, db: PostgresDatabaseAPI, now: datetime, budget: int) -> int:
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, condition='"Status" = :retrying:', parameters={"retrying": RunStatus.Retrying.name}, legacy=False)
        for row in frame.to_dicts():
            if budget <= 0: break
            if not self._is_latest_(db, row): continue
            task = self._task_(db, row["TID"])
            if row["StoppedAt"] is None or row["StoppedAt"] + timedelta(seconds=task.RetryDelay or 0) > now: continue
            retry = (row["Retry"] or 0) + 1
            if not self._issue_((row["CID"], row["TID"], retry), now): continue
            self._spawn_(row["TID"], cycle=row["CID"], retry=retry)
            budget -= 1
            self._log_.info(lambda row=row, retry=retry: f"Run Retry: Dispatched ({row['TID']}) · Retry {retry}")
        return budget

    def _busy_(self, db: PostgresDatabaseAPI, scheduled: set) -> int:
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, columns=["TID"], condition=f'"Status" IN ({self._members_(RunAPI.Busy)})', legacy=False)
        return sum(1 for tid in frame["TID"].to_list() if tid in scheduled)

    def _reap_(self, db: PostgresDatabaseAPI, now: datetime) -> None:
        stale = now - timedelta(seconds=self._LEASE_)
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, condition=f'"Status" IN ({self._members_(RunAPI.Busy)}) AND "Heartbeat" < :stale:', parameters={"stale": stale}, legacy=False)
        for row in frame.to_dicts():
            task = self._task_(db, row["TID"])
            machine = RunAPI.machine()
            machine.perform(RunEvent.Start, None)
            if (row["Retry"] or 0) < (task.MaxRetry or 0): machine.perform(RunEvent.Retry, None)
            else: machine.perform(RunEvent.RequireReview if task.RequiresReview else RunEvent.Fail, None)
            duration = (now - row["StartedAt"]).total_seconds() if row["StartedAt"] else None
            run = RunAPI(UID=row["UID"], CID=row["CID"], TID=row["TID"], Kind=row["Kind"], Status=machine.At.Name, Retry=row["Retry"], PID=row["PID"], Log=row["Log"], StartedAt=row["StartedAt"], StoppedAt=now, Duration=duration, db=db)
            run.save(by="Reaper")
            self._log_.warning(lambda row=row, run=run: f"Run Reap: {run.Status} ({row['UID']}) · Due to stale heartbeat")

    @staticmethod
    def _terminate_(pid: Union[int, None]) -> None:
        terminate(pid)

    def _paused_(self, db: PostgresDatabaseAPI, tasks: list[dict]) -> set:
        governed = {task["UID"]: task["WID"] for task in tasks if task["WID"] is not None and Kind.parse(task["Kind"]) is Kind.Scheduled}
        if not governed: return set()
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, columns=["TID"], condition=f'"Status" IN ({self._members_(RunAPI.Live)})', legacy=False)
        return {governed[tid] for tid in frame["TID"].to_list() if tid in governed}

    def _alive_(self, tid: str) -> bool:
        handle = self._services_.get(tid)
        return handle is not None and handle.poll() is None

    def _ready_(self, db: PostgresDatabaseAPI, task: dict, kinds: dict, edges: dict) -> bool:
        if task["WID"] is None: return True
        if task["WID"] not in edges: edges[task["WID"]] = CoordinatorAPI.edges(db, task["WID"])
        for predecessor, successor in edges[task["WID"]]:
            if successor != task["UID"]: continue
            if kinds.get(predecessor) is Kind.Service:
                if not self._alive_(predecessor): return False
            elif kinds.get(predecessor) is Kind.Scheduled:
                row = self._latest_(db, predecessor)
                if row is None or row["StartedAt"] is None or row["StartedAt"] < self._started_ or row["Status"] in RunAPI.Active: return False
        return True

    def _service_(self, db: PostgresDatabaseAPI, tasks: list[dict], paused: set, now: datetime) -> None:
        kinds = {task["UID"]: Kind.parse(task["Kind"]) for task in tasks}
        edges = {}
        for task in tasks:
            uid = task["UID"]
            if kinds[uid] is not Kind.Service: continue
            running = self._alive_(uid)
            if task["WID"] in paused:
                if running: self._terminate_(self._services_[uid].pid); self._log_.info(lambda task=task: f"Service Suspend: Stopped ({task['Name']}) · Maintenance")
                self._services_.pop(uid, None)
                continue
            if running: continue
            if uid in self._services_:
                lived = (now - self._spawns_.get(uid, now)).total_seconds()
                self._crashes_[uid] = 0 if lived >= self._LEASE_ else self._crashes_.get(uid, 0) + 1
                self._services_.pop(uid, None)
            cap = task["MaxRetry"] or 0
            if cap and self._crashes_.get(uid, 0) > cap:
                if self._crashes_[uid] == cap + 1:
                    self._crashes_[uid] = cap + 2
                    self._log_.error(lambda task=task, cap=cap: f"Service Halt: Stopped ({task['Name']}) · Crashed {cap + 1} Times")
                continue
            if (now - self._spawns_.get(uid, datetime.min)).total_seconds() < (task["RetryDelay"] or 0): continue
            if not self._ready_(db, task, kinds, edges): continue
            self._services_[uid] = self._spawn_(uid)
            self._spawns_[uid] = now
            self._log_.info(lambda task=task: f"Service Supervise: Spawned ({task['Name']}) · {task['Path']}")
        enabled = {task["UID"] for task in tasks}
        for uid in list(self._crashes_):
            if uid not in enabled:
                self._crashes_.pop(uid, None)
                self._spawns_.pop(uid, None)

    def _schedule_(self, db: PostgresDatabaseAPI, tasks: list[dict], now: datetime, budget: int) -> int:
        for task in tasks:
            if budget <= 0: break
            if task["WID"] is not None: continue
            if Kind.parse(task["Kind"]) is not Kind.Scheduled: continue
            if self._dedup_(db, task["UID"]): continue
            row = self._latest_(db, task["UID"])
            if not self._due_(task["Schedule"], row["StartedAt"] if row else None, now): continue
            if not self._issue_((None, task["UID"], 0), now): continue
            self._spawn_(task["UID"])
            budget -= 1
            self._log_.info(lambda task=task: f"Task Schedule: Triggered ({task['Name']}) · {task['Schedule']}")
        return budget

    def _enabled_workflows_(self, db: PostgresDatabaseAPI) -> list[dict]:
        frame = db.select(schema=WorkflowAPI.Schema, table=WorkflowAPI.Table, condition='"Enabled" = :enabled:', parameters={"enabled": True}, legacy=False)
        return frame.to_dicts()

    def _cycle_(self, db: PostgresDatabaseAPI, wid: str) -> Union[dict, None]:
        frame = db.select(schema=CycleAPI.Schema, table=CycleAPI.Table, condition='"WID" = :wid:', order='"StartedAt" DESC', limit=1, parameters={"wid": wid}, legacy=False)
        return None if frame.is_empty() else frame.row(0, named=True)

    def _cycle_runs_(self, db: PostgresDatabaseAPI, cid: str) -> list[dict]:
        frame = db.select(schema=RunAPI.Schema, table=RunAPI.Table, condition='"CID" = :cid:', parameters={"cid": cid}, legacy=False)
        return frame.to_dicts()

    def _record_(self, db: PostgresDatabaseAPI, cycle: dict, status: str, stopped: Union[datetime, None], by: str) -> None:
        CycleAPI(UID=cycle["UID"], WID=cycle["WID"], Kind=cycle["Kind"], Status=status, StartedAt=cycle["StartedAt"], StoppedAt=stopped, db=db).save(by=by)

    def _reset_(self, db: PostgresDatabaseAPI, cycle: dict, now: datetime) -> None:
        for run in self._cycle_runs_(db, cycle["UID"]):
            if run["Status"] not in RunAPI.Active: continue
            self._terminate_(run["PID"])
            failed = RunAPI(UID=run["UID"], CID=run["CID"], TID=run["TID"], Kind=run["Kind"], ExitCode=run["ExitCode"], Retry=run["Retry"], PID=run["PID"], Log=run["Log"], StartedAt=run["StartedAt"], StoppedAt=now, Heartbeat=run["Heartbeat"], db=db)
            failed.Status = RunStatus.Failure.name
            failed.save(by="Reset")
        self._record_(db, cycle, RunStatus.Failure.name, now, "Reset")
        self._log_.warning(lambda cycle=cycle: f"Cycle Reset: Failure ({cycle['UID']}) · Due to overrun")

    def _advance_(self, db: PostgresDatabaseAPI, workflow: dict, members: list[dict], edges: list, now: datetime, budget: int) -> int:
        launch = self._launch_ is not None and workflow["UID"] in self._launch_
        kind = Kind.parse(workflow["Kind"])
        if not isinstance(kind, Kind): kind = Kind.Scheduled if workflow["Schedule"] else Kind.Manual
        cycle = self._cycle_(db, workflow["UID"])
        opened = cycle is not None and cycle["Status"] in self._OPEN_
        if kind is Kind.Service:
            if launch: self._launch_.discard(workflow["UID"])
            if not opened:
                fresh = {"UID": uuid.uuid4().hex, "WID": workflow["UID"], "Kind": Kind.Service.name, "StartedAt": datetime.now()}
                self._record_(db, fresh, RunStatus.Running.name, None, "Scheduler")
                self._log_.info(lambda workflow=workflow: f"Cycle Open: Running ({workflow['Name']}) · Resident")
            return budget
        tids = [member["UID"] for member in members]
        rows = {member["UID"]: member for member in members if Kind.parse(member["Kind"]) is Kind.Scheduled}
        if kind is Kind.Manual and launch:
            self._launch_.discard(workflow["UID"])
            launch = False
        if not rows:
            if launch: self._launch_.discard(workflow["UID"])
            return budget
        waits = {uid: row["Waits"] is not False for uid, row in rows.items()}
        tolerates = {uid: row["Tolerates"] is not False for uid, row in rows.items()}
        due = launch or (kind is Kind.Scheduled and self._due_(workflow["Schedule"], cycle["StartedAt"] if cycle else None, now))
        if opened and due and workflow["Waits"] is False:
            self._reset_(db, cycle, now)
            opened = False
        if opened:
            runs = sorted(self._cycle_runs_(db, cycle["UID"]), key=lambda run: (run["StartedAt"] or datetime.min, run["Retry"] or 0))
            status = {run["TID"]: run["Status"] for run in runs}
            pending = any(state in RunAPI.Active for state in status.values())
            manual = Kind.parse(cycle["Kind"]) is Kind.Manual
            timely = {uid: manual or self._timely_(row["Schedule"], cycle["StartedAt"], now) for uid, row in rows.items()}
            ready = [tid for tid in CoordinatorAPI.eligible(tids, edges, status, waits=waits, tolerates=tolerates) if tid in rows and timely[tid]]
            waiting = any(status.get(uid) is None and not timely[uid] for uid in rows)
            dispatched = 0
            for tid in ready:
                if budget <= 0: break
                if not self._issue_((cycle["UID"], tid, 0), now): continue
                self._spawn_(tid, cycle=cycle["UID"])
                budget -= 1
                dispatched += 1
                self._log_.info(lambda workflow=workflow, tid=tid: f"Cycle Advance: Triggered ({workflow['Name']}) · {tid}")
            if not pending and not dispatched and not ready and not waiting:
                final = RunStatus.Success.name if all(status.get(uid) == RunStatus.Success.name for uid in rows) else RunStatus.Failure.name
                self._record_(db, cycle, final, now, "Scheduler")
                self._log_.info(lambda workflow=workflow, final=final: f"Cycle Close: {final} ({workflow['Name']})")
                return budget
            state = RunStatus.Reviewing.name if RunStatus.Reviewing.name in status.values() else RunStatus.Approving.name if RunStatus.Approving.name in status.values() else RunStatus.Running.name
            if state != cycle["Status"]: self._record_(db, cycle, state, None, "Scheduler")
            return budget
        if due:
            if launch: self._launch_.discard(workflow["UID"])
            start = croniter(workflow["Schedule"], now).get_prev(datetime) if workflow["Schedule"] and not launch else now
            fresh = {"UID": uuid.uuid4().hex, "WID": workflow["UID"], "Kind": Kind.Scheduled.name, "StartedAt": start}
            self._record_(db, fresh, RunStatus.Running.name, None, "Scheduler")
            self._log_.info(lambda workflow=workflow: f"Cycle Open: Running ({workflow['Name']})")
            for tid in CoordinatorAPI.eligible(tids, edges, {}, waits=waits, tolerates=tolerates):
                if tid not in rows: continue
                if not self._timely_(rows[tid]["Schedule"], start, now): continue
                if budget <= 0: break
                if not self._issue_((fresh["UID"], tid, 0), now): continue
                self._spawn_(tid, cycle=fresh["UID"])
                budget -= 1
                self._log_.info(lambda workflow=workflow, tid=tid: f"Cycle Launch: Started ({workflow['Name']}) · {tid}")
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
            if self._launch_ is None: self._launch_ = {task["WID"] for task in tasks if task["WID"] is not None and Kind.parse(task["Kind"]) is Kind.Service}
            self._service_(db, tasks, self._paused_(db, tasks), now)
            scheduled = {task["UID"] for task in tasks if Kind.parse(task["Kind"]) is Kind.Scheduled}
            budget = self._concurrency_ - self._busy_(db, scheduled)
            budget = self._retry_(db, now, budget)
            budget = self._schedule_(db, tasks, now, budget)
            self._workflows_(db, tasks, now, budget)

    def start(self) -> None:
        self._running_ = True
        self._listener_ = self._listen_()
        self._log_.info(lambda: f"Scheduler Start: Running · Push Notifications · {self._interval_}s Fallback · {self._concurrency_} Concurrency")
        while self._running_:
            try: self._tick_()
            except Exception as error: self._log_.error(lambda: f"Scheduler Tick: Failed · Due to {error}")
            self._wait_()

    def stop(self) -> None:
        self._running_ = False
        for handle in list(self._services_.values()):
            if handle is not None and handle.poll() is None: self._terminate_(handle.pid)
        self._services_.clear()
        if self._listener_ is not None:
            try: self._listener_.disconnect()
            except Exception: pass
            self._listener_ = None
        self._log_.info(lambda: "Scheduler Stop: Halted · Services Terminated")