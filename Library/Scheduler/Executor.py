from __future__ import annotations

import os
import sys
import time
import tempfile
import uuid
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Union

import psutil

from Library.Logging import HandlerLoggingAPI
from Library.Utility.Path import traceback_root
from Library.Scheduler.Workflow import Kind
from Library.Scheduler.Task import TaskAPI, TaskType
from Library.Scheduler.Run import RunAPI, RunEvent, RunStatus
from Library.Database import PostgresDatabaseAPI, QueryAPI

class ExecutorAPI:

    _POLL_: float = 0.2
    _HEARTBEAT_: float = 15.0
    _ROOT_: str = str(traceback_root())
    _RUNS_: str = str(Path(tempfile.gettempdir()) / "Quant" / "Runs")

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
    def spawn(tid: str, *, database: str = "Quant", cycle: Union[str, None] = None, retry: int = 0, manual: bool = False) -> subprocess.Popen:
        command = [sys.executable, "-m", "Library.Scheduler.Runner", tid, "--database", database]
        if cycle is not None: command += ["--cycle", cycle]
        if retry: command += ["--retry", str(retry)]
        if manual: command += ["--manual"]
        return subprocess.Popen(command, cwd=ExecutorAPI._ROOT_, env=ExecutorAPI._environment_(), creationflags=subprocess.CREATE_NO_WINDOW)

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

    def run(self, task: TaskAPI, *, cycle: Union[str, None] = None, retry: int = 0, manual: bool = False) -> RunAPI:
        machine = RunAPI.machine()
        artifact = TaskType.parse(task.Type)
        label = artifact.name if isinstance(artifact, TaskType) else str(task.Type)
        kind = Kind.Service.name if Kind.parse(task.Kind) is Kind.Service else Kind.Manual.name if manual else Kind.Scheduled.name
        run = RunAPI(UID=uuid.uuid4().hex, CID=cycle, TID=task.UID, Kind=kind, Status=RunStatus.Waiting.name, Retry=retry, Heartbeat=datetime.now())
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
            process = subprocess.Popen(self._command_(artifact, task.Path), cwd=self._ROOT_, env=self._environment_(), stdout=sink, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            run.PID = os.getpid()
            try: monitor = psutil.Process(process.pid)
            except psutil.Error: monitor = None
            self._persist_(run)
            while process.poll() is None:
                if monitor is not None: peak = self._sample_(monitor, peak)
                now = datetime.now()
                if (now - beat).total_seconds() >= self._HEARTBEAT_:
                    self._beat_(run)
                    beat = now
                time.sleep(self._POLL_)
            if monitor is not None: peak = self._sample_(monitor, peak)
        exit_code = process.returncode
        stopped = datetime.now()
        if exit_code == 0: machine.perform(RunEvent.RequireApproval if task.RequiresApproval else RunEvent.Complete, None)
        elif retry < (task.MaxRetry or 0): machine.perform(RunEvent.Retry, None)
        else: machine.perform(RunEvent.RequireReview if task.RequiresReview else RunEvent.Fail, None)
        run.Status, run.StoppedAt, run.Duration, run.Memory, run.ExitCode, run.Log = machine.At.Name, stopped, (stopped - started).total_seconds(), peak, exit_code, log
        self._persist_(run)
        self._log_.info(lambda: f"Run Finish: {run.Status} ({task.Name}) · {run.Duration:.2f}s · {peak / 1048576:.1f} MB · Exit {exit_code}")
        return run