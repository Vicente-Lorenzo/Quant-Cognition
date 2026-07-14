from __future__ import annotations

import os
import sys
import time
import uuid
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Union

import psutil

from Library.Logging import HandlerLoggingAPI
from Library.Utility.Path import traceback_root
from Library.Scheduler.Task import TaskAPI, TaskType
from Library.Scheduler.Run import RunAPI, RunEvent, RunStatus
from Library.Database import PostgresDatabaseAPI, QueryAPI

class ExecutorAPI:

    _POLL_: float = 0.2
    _HEARTBEAT_: float = 15.0
    _ROOT_: str = str(traceback_root())
    _RUNS_: str = str(traceback_root() / "Runs")

    def __init__(self, *, database: str = "Quant") -> None:
        self._database_ = database
        self._log_ = HandlerLoggingAPI(Class=type(self).__name__, Subclass=database)

    @staticmethod
    def _command_(kind: TaskType, path: str) -> list[str]:
        if kind is TaskType.Batch: return ["cmd", "/c", path]
        if kind is TaskType.Shell: return ["bash", path]
        return [sys.executable, path]

    @staticmethod
    def _environment_() -> dict:
        environment = dict(os.environ)
        previous = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = ExecutorAPI._ROOT_ + (os.pathsep + previous if previous else "")
        return environment

    @staticmethod
    def spawn(tid: str, *, database: str = "Quant", workflow_run: Union[str, None] = None, attempt: int = 1) -> subprocess.Popen:
        command = [sys.executable, "-m", "Library.Scheduler.Runner", tid, "--database", database]
        if workflow_run is not None: command += ["--workflow-run", workflow_run]
        if attempt != 1: command += ["--attempt", str(attempt)]
        return subprocess.Popen(command, cwd=ExecutorAPI._ROOT_, env=ExecutorAPI._environment_())

    @staticmethod
    def _sample_(monitor: psutil.Process, peak: int) -> int:
        try:
            total = monitor.memory_info().rss
            for child in monitor.children(recursive=True):
                try: total += child.memory_info().rss
                except psutil.Error: pass
            return max(peak, total)
        except psutil.Error:
            return peak

    def _persist_(self, run: RunAPI) -> None:
        with PostgresDatabaseAPI(database=self._database_) as db:
            run._db_ = db
            run.save(by="Scheduler")
        run._db_ = None

    def _beat_(self, run: RunAPI) -> None:
        run.Heartbeat = datetime.now()
        with PostgresDatabaseAPI(database=self._database_) as db:
            sql = f'UPDATE {db._target_(run.Schema, run.Table)} SET "Heartbeat" = :heartbeat: WHERE "UID" = :uid:'
            db.execute(QueryAPI(sql), [{"heartbeat": run.Heartbeat, "uid": run.UID}])

    def run(self, task: TaskAPI, *, workflow_run: Union[str, None] = None, attempt: int = 1) -> RunAPI:
        machine = RunAPI.machine()
        kind = TaskType.parse(task.Type)
        label = kind.name if isinstance(kind, TaskType) else str(task.Type)
        run = RunAPI(UID=uuid.uuid4().hex, TID=task.UID, WorkflowRun=workflow_run, Status=RunStatus.Waiting.name, Attempt=attempt, Heartbeat=datetime.now())
        self._persist_(run)
        machine.perform(RunEvent.Start, None)
        started = datetime.now()
        run.Status, run.StartedAt, run.Heartbeat = machine.At.Name, started, started
        self._persist_(run)
        self._log_.info(lambda: f"Run Launch: Started ({task.Name}) · {label} · {task.Path}")
        Path(self._RUNS_).mkdir(parents=True, exist_ok=True)
        log = str(Path(self._RUNS_) / f"{run.UID}.log")
        peak, beat = 0, started
        with open(log, "wb") as sink:
            process = subprocess.Popen(self._command_(kind, task.Path), cwd=self._ROOT_, env=self._environment_(), stdout=sink, stderr=subprocess.STDOUT)
            monitor = psutil.Process(process.pid)
            while process.poll() is None:
                peak = self._sample_(monitor, peak)
                now = datetime.now()
                if (now - beat).total_seconds() >= self._HEARTBEAT_:
                    self._beat_(run)
                    beat = now
                time.sleep(self._POLL_)
            peak = self._sample_(monitor, peak)
        exit_code = process.returncode
        finished = datetime.now()
        if exit_code == 0: machine.perform(RunEvent.RequireApproval if task.RequiresApproval else RunEvent.Complete, None)
        elif attempt < (task.MaxAttempts or 1): machine.perform(RunEvent.Retry, None)
        else: machine.perform(RunEvent.RequireReview if task.RequiresReview else RunEvent.Fail, None)
        run.Status, run.FinishedAt, run.Duration, run.Memory, run.ExitCode, run.Log = machine.At.Name, finished, (finished - started).total_seconds(), peak, exit_code, log
        self._persist_(run)
        self._log_.info(lambda: f"Run Finish: {run.Status} ({task.Name}) · {run.Duration:.2f}s · {peak / 1048576:.1f} MB · Exit {exit_code}")
        return run