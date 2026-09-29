import sys
import json
import time
import threading
import subprocess
from pathlib import Path
from typing import Union

from Library.Credential import VaultAPI
from Library.Database import PostgresDatabaseAPI
from Library.Database.Query import QueryAPI
from Library.Logging import LoggingAPI
from Library.Spotware import SpotwareAPI
from Library.Spotware.Token import TokenAPI
from Library.Utility.Progress import Phase, ProgressAPI
from Library.Utility.Runtime import terminate, windowless
from Library.Utility.Typing import MISSING, Missing

class DataServiceAPI:

    def __init__(self, *, database: str = "Quant", credential: str = "cTrader ID", vault: Union[str, Missing] = MISSING) -> None:
        self._database_ = database
        self._credential_ = credential
        self._keeper_ = database if vault is MISSING else vault
        self._vault_ = VaultAPI(database=self._keeper_, refreshers={"Spotware": TokenAPI.refresh})
        self._token_: Union[str, None] = None
        self._stop_ = threading.Event()
        self._ready_ = False
        self._log_ = LoggingAPI(database)

    def _values_(self) -> dict:
        values = self._vault_.resolve(service="Spotware", name=self._credential_, by=self._vault_.administrator())
        if values is None: raise LookupError(f"Credential Resolve: Failed · No Spotware · {self._credential_} credential in the vault")
        return values

    def _stored_(self) -> Union[str, None]:
        return TokenAPI.plain(self._values_().get("AccessToken"))

    def _renew_(self) -> str:
        administrator = self._vault_.administrator()
        row = next((row for row in self._vault_.credentials(service="Spotware", by=administrator) if row["Name"] == self._credential_), None)
        if row is None: raise LookupError(f"Credential Renew: Failed · No Spotware · {self._credential_} credential in the vault")
        with PostgresDatabaseAPI(database=self._keeper_) as db:
            db.executeone(QueryAPI("SELECT pg_advisory_lock(hashtext(:key:))"), key=f"Credential Renew {row['UID']}")
            try:
                stored = self._stored_()
                if stored == self._token_: self._vault_.rotate(row["UID"])
                self._token_ = self._stored_()
            finally: db.executeone(QueryAPI("SELECT pg_advisory_unlock(hashtext(:key:))"), key=f"Credential Renew {row['UID']}")
        return self._token_

    def accounts(self, *, live: bool = False) -> list[dict]:
        return [account for account in self._values_().get("Accounts") or [] if bool(account.get("Live")) == live]

    def client(self, account: int) -> SpotwareAPI:
        values = self._values_()
        self._token_ = TokenAPI.plain(values.get("AccessToken"))
        return SpotwareAPI.of(values, account=account, renew=self._renew_)

    def ready(self, detail: str = "") -> None:
        if self._ready_: return
        self._ready_ = True
        ProgressAPI.phase(Phase.Running)
        self._log_.info(lambda: f"Service Readiness: [Initializing] → (Caught Up) → [Running]{f' · {detail}' if detail else ''}")

    def stop(self) -> None:
        self._stop_.set()

    def stopped(self, timeout: Union[float, None] = None) -> bool:
        return self._stop_.wait(timeout) if timeout else self._stop_.is_set()

    def work(self) -> None:
        raise NotImplementedError

    def serve(self) -> int:
        try:
            self.work()
            return 0
        except KeyboardInterrupt:
            return 0
        except Exception as error:
            self._log_.failure(lambda error=error: f"Service Operation: Failed · {error}")
            return 1
        finally:
            ProgressAPI.phase(Phase.Terminating)

class SupervisorAPI(DataServiceAPI):

    def __init__(self, *, script: Path, flag: str, name: str, database: str = "Quant", credential: str = "cTrader ID", vault: Union[str, Missing] = MISSING, interval: float = 30.0, backoff: float = 60.0) -> None:
        super().__init__(database=database, credential=credential, vault=vault)
        self._script_ = script
        self._flag_ = flag
        self._name_ = name
        self._interval_ = interval
        self._backoff_ = backoff
        self._workers_: dict = {}
        self._crashes_: dict = {}
        self._ready_workers_: set = set()
        self._lock_ = threading.Lock()

    def tracked(self) -> dict:
        raise NotImplementedError

    def report(self, tracked: dict) -> None:
        return None

    def live(self, tracked: dict) -> int:
        with self._lock_: return len(set(tracked) & self._ready_workers_)

    def _forward_(self, key: int, process: subprocess.Popen) -> None:
        for line in process.stdout:
            marker = line.find(ProgressAPI.SENTINEL)
            if marker >= 0:
                try: record = json.loads(line[marker + len(ProgressAPI.SENTINEL):])
                except ValueError: continue
                if record.get("phase") == Phase.Running.name:
                    with self._lock_: self._ready_workers_.add(key)
                continue
            with self._lock_:
                sys.stdout.write(line)
                sys.stdout.flush()

    def _spawn_(self, key: int, label: str) -> None:
        command = [sys.executable, str(self._script_), self._flag_, str(key), "--database", self._database_]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **windowless())
        threading.Thread(target=self._forward_, args=(key, process), name=f"{self._name_} {label}", daemon=True).start()
        self._workers_[key] = process
        self._log_.info(lambda: f"{self._name_} Worker: Spawned ({label}) · {key}")

    def _halt_(self, key: int) -> None:
        terminate(self._workers_.pop(key).pid)
        with self._lock_: self._ready_workers_.discard(key)

    def _supervise_(self) -> None:
        tracked = self.tracked()
        for key in [key for key in self._workers_ if key not in tracked]:
            self._halt_(key)
            self._log_.info(lambda key=key: f"{self._name_} Worker: Stopped · {key} Untracked")
        clock = time.monotonic()
        for key, label in tracked.items():
            if key in self._workers_:
                process = self._workers_[key]
                if process.poll() is None: continue
                self._workers_.pop(key)
                with self._lock_: self._ready_workers_.discard(key)
                self._crashes_[key] = (self._crashes_.get(key, (0, 0.0))[0] + 1, clock)
                self._log_.warning(lambda label=label, code=process.returncode: f"{self._name_} Worker: Exited ({label}) · Exit {code} · Restarting")
            crashes, last = self._crashes_.get(key, (0, 0.0))
            if crashes and clock - last < min(self._backoff_ * crashes, 900.0): continue
            self._spawn_(key, label)
        if self.live(tracked) == len(tracked): self.ready(f"{len(tracked)} Workers Caught Up")
        self.report(tracked)

    def work(self) -> None:
        try:
            while True:
                try: self._supervise_()
                except Exception as error: self._log_.warning(lambda error=error: f"{self._name_} Supervision: Failed · {error}")
                if self.stopped(self._interval_): break
        finally:
            for key in list(self._workers_): self._halt_(key)