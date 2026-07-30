from __future__ import annotations

import os
import sys
import time
import socket
import uuid
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Union

import psutil

from Library.Logging import LoggingAPI
from Library.Logging.Log import LogAPI
from Library.Utility.Path import inspect_temporary, traceback_root
from Library.Scheduler.Workflow import Kind
from Library.Scheduler.Task import TaskAPI, TaskType
from Library.Scheduler.Run import RunAPI, RunEvent, RunStatus
from Library.Database import PostgresDatabaseAPI, QueryAPI

class ExecutorAPI:

    _POLL_: float = 0.2
    _HEARTBEAT_: float = 15.0
    _ROOT_: str = str(traceback_root())
    RUNS: str = str(inspect_temporary("Quant", "Runs"))
    _CONTENT_: int = 8 * 1024 * 1024

    def __init__(self, *, database: str = "Quant") -> None:
        self._database_ = database
        self._log_ = LoggingAPI(database)

    def _open_log_(self, run: RunAPI, task: TaskAPI, path: str) -> Union[str, None]:
        try:
            with PostgresDatabaseAPI(database=self._database_) as db:
                record = LogAPI(
                    UID=uuid.uuid4().hex, Source=task.Name, Level=RunStatus.Running.name, Host=socket.gethostname(),
                    User=run.Auditor, Process=run.PID, Path=path, Content="", Records=0, Dropped=0,
                    Truncated=False, StartedAt=datetime.now(), db=db)
                record.save(by="Scheduler")
                return record.UID
        except Exception as error:
            self._log_.debug(lambda: f"Run Log Open: Failed · {error}")
            return None

    def _close_log_(self, run: RunAPI, path: str) -> None:
        if run.LID is None: return
        try:
            source = Path(path)
            content = source.read_text(encoding="utf-8", errors="replace") if source.exists() else ""
            with PostgresDatabaseAPI(database=self._database_) as db:
                record = LogAPI(UID=run.LID, db=db, autoload=True)
                record.Level, record.Records = run.Status, content.count("\n")
                record.Truncated = len(content) > self._CONTENT_
                record.Content = content[:self._CONTENT_]
                record.StoppedAt = datetime.now()
                record.save(by="Scheduler")
        except Exception as error:
            self._log_.debug(lambda: f"Run Log Close: Failed · {error}")

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
        environment["PYTHONIOENCODING"] = "utf-8"
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
        Path(self.RUNS).mkdir(parents=True, exist_ok=True)
        log = str(Path(self.RUNS) / f"{run.UID}.log")
        run.LID = self._open_log_(run, task, log)
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
        self._close_log_(run, log)
        self._persist_(run)
        self._log_.info(lambda: f"Run Finish: {run.Status} ({task.Name}) · {run.Duration:.2f}s · {peak / 1048576:.1f} MB · Exit {exit_code}")
        return run