import json
import os
import re
import shlex
import shutil
import sys
import time
import socket
import uuid
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Union

import psutil

from Library.Logging import LoggingAPI, StorageAPI, VerboseLevel
from Library.Logging.Log import LogAPI
from Library.Utility.Progress import ProgressAPI
from Library.Utility.Path import inspect_persistent, inspect_temporary, traceback_root
from Library.Utility.File import PruneAPI
from Library.Scheduler.Workflow import Kind
from Library.Scheduler.Task import TaskAPI, TaskType
from Library.Scheduler.Run import RunAPI, RunEvent, RunStatus
from Library.Database import PostgresDatabaseAPI, QueryAPI

class ExecutorAPI:

    _POLL_: float = 0.2
    _HEARTBEAT_: float = 15.0
    _PULSE_: float = 2.0
    _ROOT_: str = str(traceback_root())
    Folder: str = "Runs"
    Runs: str = str(inspect_temporary(Folder))
    Kept: str = str(inspect_persistent(Folder))
    _CONTENT_: int = 8 * 1024 * 1024
    _SCOPE_: str = "--run"
    _STORAGE_: str = "--storage"
    _LOGGED_ = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[.,]\d+ - ")

    @classmethod
    def settle(cls, uid: str) -> Path:
        kept = Path(cls.Kept) / str(uid)
        return kept if kept.is_dir() else Path(cls.Runs) / str(uid)

    @classmethod
    def relocate(cls, uid: str, persist: bool) -> Union[Path, None]:
        source = cls.settle(uid)
        target = (Path(cls.Kept) if persist else Path(cls.Runs)) / str(uid)
        if source == target or not source.is_dir(): return target if target.is_dir() else None
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            PruneAPI.discard(target)
            if target.exists(): raise OSError(f"Run folder not replaceable · {target}")
        shutil.move(str(source), str(target))
        return target

    def __init__(self, *, database: str = "Quant") -> None:
        self._database_ = database
        self._log_ = LoggingAPI(database)

    @classmethod
    def _verbosity_(cls, arguments: Union[str, None]) -> str:
        tokens = cls._tokens_(arguments)
        for index, token in enumerate(tokens[:-1]):
            if token == cls._STORAGE_ and tokens[index + 1] in VerboseLevel.__members__: return tokens[index + 1]
        return StorageAPI._DEFAULT_.name

    @classmethod
    def _sift_(cls, content: str, level: VerboseLevel) -> tuple[str, list]:
        accepted, escaped = [], []
        for line in content.splitlines():
            if ProgressAPI.SENTINEL in line: continue
            if not cls._LOGGED_.match(line):
                if line.strip(): escaped.append(line)
                continue
            marker = next((member for member in VerboseLevel if f" - {member.name} - " in line), None)
            if marker is None or marker.value <= level.value: accepted.append(line)
        return "\n".join(accepted + escaped), escaped

    def _open_log_(self, run: RunAPI, task: TaskAPI, path: str) -> Union[str, None]:
        try:
            with PostgresDatabaseAPI(database=self._database_) as db:
                record = LogAPI(
                    UID=uuid.uuid4().hex,
                    Source=task.Name,
                    Level=self._verbosity_(run.Arguments),
                    Host=socket.gethostname(),
                    User=run.Auditor,
                    Process=run.PID,
                    Path=path,
                    Content="",
                    Records=0,
                    Dropped=0,
                    Truncated=False,
                    StartedAt=datetime.now(),
                    db=db
                )
                record.save(by="Scheduler")
                return record.UID
        except Exception as error:
            self._log_.debug(lambda: f"Run Log Open: Failed · {error}")
            return None

    def _rescue_(self, folder: Path, escaped: list) -> None:
        if not escaped: return
        try:
            with open(folder / "Run.log", "a", encoding="utf-8", newline="\n") as sink:
                sink.write(f"\n--- Escaped Output: {len(escaped)} Lines · Bypassed The Logger ---\n")
                sink.write("\n".join(escaped) + "\n")
            self._log_.warning(lambda: f"Run Output: Escaped · {len(escaped)} Lines · Appended To Run.log")
        except Exception as error:
            self._log_.debug(lambda: f"Run Output Rescue: Failed · {error}")

    def _close_log_(self, run: RunAPI, path: str) -> None:
        source = Path(path)
        raw = source.read_text(encoding="utf-8", errors="replace") if source.exists() else ""
        content, escaped = self._sift_(raw, VerboseLevel[self._verbosity_(run.Arguments)])
        self._rescue_(source.parent, escaped)
        try: source.unlink(missing_ok=True)
        except Exception: pass
        if run.LID is None: return
        try:
            with PostgresDatabaseAPI(database=self._database_) as db:
                record = LogAPI(UID=run.LID, db=db, autoload=True)
                record.Records = content.count("\n")
                record.Truncated = len(content) > self._CONTENT_
                record.Content = content[:self._CONTENT_]
                record.StoppedAt = datetime.now()
                record.save(by="Scheduler")
        except Exception as error:
            self._log_.debug(lambda: f"Run Log Close: Failed · {error}")

    @classmethod
    def _scoped_(cls, arguments: str, folder: str) -> str:
        if not arguments: return arguments
        tokens = shlex.split(arguments, posix=False)
        if cls._SCOPE_ in tokens: return arguments
        return " ".join([*tokens, cls._SCOPE_, f'"{folder}"'])

    @staticmethod
    def _tokens_(arguments: str) -> list[str]:
        tokens = shlex.split(arguments, posix=False) if arguments else []
        return [token[1:-1] if len(token) > 1 and token[0] == token[-1] and token[0] in "\"'" else token for token in tokens]

    @staticmethod
    def _command_(kind: TaskType, path: str, arguments: str = None) -> list[str]:
        extra = ExecutorAPI._tokens_(arguments)
        if kind is TaskType.Batch: return ["cmd", "/c", path, *extra]
        if kind is TaskType.Shell: return ["bash", path, *extra]
        return [sys.executable, path, *extra]

    @staticmethod
    def _environment_() -> dict:
        environment = dict(os.environ)
        previous = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = ExecutorAPI._ROOT_ + (os.pathsep + previous if previous else "")
        environment["PYTHONIOENCODING"] = "utf-8"
        return environment

    @staticmethod
    def spawn(tid: str, *, database: str = "Quant", cycle: Union[str, None] = None, retry: int = 0, manual: bool = False, arguments: Union[str, None] = None) -> subprocess.Popen:
        command = [sys.executable, "-m", "Library.Scheduler.Runner", tid, "--database", database]
        if arguments: command += ["--arguments", arguments]
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
            sql = f'UPDATE {db._target_(run.Schema, run.Table)} SET "Heartbeat" = :heartbeat:, "Progress" = :progress:, "Stage" = :stage:, "Remaining" = :remaining: WHERE "UID" = :uid:'
            db.execute(QueryAPI(sql), [{"heartbeat": run.Heartbeat, "progress": run.Progress, "stage": run.Stage, "remaining": run.Remaining, "uid": run.UID}])

    def _follow_(self, path: str, offset: int, run: RunAPI) -> int:
        try:
            source = Path(path)
            if not source.exists(): return offset
            size = source.stat().st_size
            if size <= offset: return offset
            with open(source, "rb") as handle:
                handle.seek(offset)
                chunk = handle.read(size - offset)
            tail = chunk.rfind(b"\n")
            if tail < 0: return offset
            for line in chunk[:tail].decode("utf-8", errors="replace").splitlines():
                marker = line.find(ProgressAPI.SENTINEL)
                if marker < 0: continue
                record = json.loads(line[marker + len(ProgressAPI.SENTINEL):])
                run.Progress, run.Stage, run.Remaining = record.get("fraction"), record.get("stage"), record.get("remaining")
            return offset + tail + 1
        except Exception:
            return offset

    def run(self, task: TaskAPI, *, cycle: Union[str, None] = None, retry: int = 0, manual: bool = False, arguments: Union[str, None] = None) -> RunAPI:
        machine = RunAPI.machine()
        artifact = TaskType.parse(task.Type)
        label = artifact.name if isinstance(artifact, TaskType) else str(task.Type)
        kind = Kind.Service.name if Kind.parse(task.Kind) is Kind.Service else Kind.Manual.name if manual else Kind.Scheduled.name
        arguments = arguments if arguments is not None else task.Arguments
        run = RunAPI(UID=uuid.uuid4().hex, CID=cycle, TID=task.UID, Kind=kind, Status=RunStatus.Waiting.name, Retry=retry, Arguments=arguments, Heartbeat=datetime.now())
        self._persist_(run)
        machine.perform(RunEvent.Start, None)
        started = datetime.now()
        run.Status, run.StartedAt, run.Heartbeat = machine.At.Name, started, started
        self._persist_(run)
        self._log_.info(lambda: f"Run Launch: Started ({task.Name}) · {label} · {task.Path}")
        folder = Path(self.Runs) / run.UID
        folder.mkdir(parents=True, exist_ok=True)
        log = str(folder / "Console.log")
        run.LID = self._open_log_(run, task, log)
        peak, beat = 0, started
        with open(log, "wb") as sink:
            process = subprocess.Popen(self._command_(artifact, task.Path, self._scoped_(arguments, str(folder))), cwd=self._ROOT_, env=self._environment_(), stdout=sink, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            run.PID = os.getpid()
            try: monitor = psutil.Process(process.pid)
            except psutil.Error: monitor = None
            self._persist_(run)
            cursor, pulse, seen = 0, started, None
            while process.poll() is None:
                if monitor is not None: peak = self._sample_(monitor, peak)
                now = datetime.now()
                cursor = self._follow_(log, cursor, run)
                moved = run.Progress != seen
                if (now - beat).total_seconds() >= self._HEARTBEAT_ or (moved and (now - pulse).total_seconds() >= self._PULSE_):
                    self._beat_(run)
                    beat, pulse, seen = now, now, run.Progress
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