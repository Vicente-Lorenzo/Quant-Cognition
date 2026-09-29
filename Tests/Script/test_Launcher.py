import sys
import json
from pathlib import Path

import pytest

import Script.Scheduler as Launcher
from Library.Logging.File import FileAPI

def _environment_(tmp_path, state: dict = None) -> Path:
    environment = tmp_path / "envs" / "Quant"
    environment.mkdir(parents=True)
    (environment / "Old.txt").write_text("old", encoding="utf-8")
    if state is not None:
        successor = environment.with_name("Quant.next")
        successor.mkdir()
        (successor / "Upgrade.json").write_text(json.dumps(state), encoding="utf-8")
    return environment

def _swappable_(monkeypatch, environment: Path, *, smoke: bool = True) -> list:
    done = []
    def _execute_(command, **kwargs):
        done.append(command[1:3])
        if command[1] == "-c" and not smoke: raise RuntimeError("No module named numpy")
    monkeypatch.setattr(Launcher, "locked", lambda base, successor: successor / "Upgrade.txt")
    monkeypatch.setattr(Launcher, "pinned", lambda successor: ["torch==2.15.0"])
    monkeypatch.setattr(Launcher, "manage", lambda base, arguments: environment.mkdir() or (environment / "New.txt").write_text("new", encoding="utf-8"))
    monkeypatch.setattr(Launcher, "execute", _execute_)
    monkeypatch.setattr(Launcher, "occupants", lambda environment: [])
    monkeypatch.setattr(Launcher, "journal", lambda message: done.append(message))
    return done

def _state_(environment: Path) -> dict:
    return json.loads((environment.with_name("Quant.next") / "Upgrade.json").read_text(encoding="utf-8"))

def test_nothing_is_applied_without_a_validated_successor(monkeypatch, tmp_path):
    environment = _environment_(tmp_path, {"State": "Failed"})
    _swappable_(monkeypatch, environment)
    assert Launcher.upgrade(tmp_path, environment) == "Current"
    assert (environment / "Old.txt").exists()

def test_a_validated_successor_replaces_the_environment_and_keeps_the_previous(monkeypatch, tmp_path):
    environment = _environment_(tmp_path, {"State": "Validated", "Moved": ["a 1 → 2"]})
    done = _swappable_(monkeypatch, environment)
    assert Launcher.upgrade(tmp_path, environment) == "Applied"
    assert (environment / "New.txt").exists() and (environment.with_name("Quant.previous") / "Old.txt").exists()
    state = _state_(environment)
    assert state["State"] == "Applied" and state["Reported"] is False and state["Moved"] == ["a 1 → 2"]
    assert ["-m", "pip"] in done and done[-1].startswith("Environment Upgrade: Applied · 1 Moved")

def test_a_failed_swap_restores_the_environment_under_its_own_name(monkeypatch, tmp_path):
    environment = _environment_(tmp_path, {"State": "Validated"})
    _swappable_(monkeypatch, environment, smoke=False)
    assert Launcher.upgrade(tmp_path, environment) == "Restored"
    assert (environment / "Old.txt").exists() and not environment.with_name("Quant.previous").exists()
    assert _state_(environment)["Reason"] == "Previous environment restored · No module named numpy"

def test_an_occupied_environment_defers_the_upgrade(monkeypatch, tmp_path):
    environment = _environment_(tmp_path, {"State": "Validated"})
    done = _swappable_(monkeypatch, environment)
    monkeypatch.setattr(Launcher, "occupants", lambda environment: ["python.exe 4242"])
    assert Launcher.upgrade(tmp_path, environment, patience=0) == "Deferred"
    assert (environment / "Old.txt").exists() and _state_(environment)["State"] == "Validated"
    assert done == ["Environment Upgrade: Deferred · 1 Processes run from the environment · python.exe 4242"]

def test_the_previous_of_the_last_upgrade_makes_room_for_the_new_one(monkeypatch, tmp_path):
    environment = _environment_(tmp_path, {"State": "Validated"})
    stale = environment.with_name("Quant.previous")
    stale.mkdir()
    (stale / "Older.txt").write_text("older", encoding="utf-8")
    _swappable_(monkeypatch, environment)
    Launcher.upgrade(tmp_path, environment)
    assert sorted(path.name for path in stale.iterdir()) == ["Old.txt"]
    assert sorted(path.name for path in environment.parent.iterdir()) == ["Quant", "Quant.next", "Quant.previous"]

def test_a_failed_upgrade_keeps_the_previous_record_under_its_own_name(monkeypatch, tmp_path):
    environment = _environment_(tmp_path, {"State": "Validated"})
    kept = environment.with_name("Quant.previous")
    kept.mkdir()
    (kept / "Older.txt").write_text("older", encoding="utf-8")
    _swappable_(monkeypatch, environment, smoke=False)
    assert Launcher.upgrade(tmp_path, environment) == "Restored"
    assert (environment / "Old.txt").exists() and (kept / "Older.txt").exists()
    assert sorted(path.name for path in environment.parent.iterdir()) == ["Quant", "Quant.next", "Quant.previous"]

def test_a_half_built_environment_that_cannot_be_deleted_is_moved_aside(monkeypatch, tmp_path):
    environment = _environment_(tmp_path)
    previous = environment.with_name("Quant.previous")
    environment.rename(previous)
    environment.mkdir()
    monkeypatch.setattr(Launcher, "remove", lambda path: False)
    Launcher.restore(environment, previous)
    assert (environment / "Old.txt").exists()
    assert [path.name.split(" ")[0] for path in environment.parent.iterdir() if path.name != "Quant"] == ["Quant.failed"]

def test_a_launch_outside_the_base_interpreter_hands_over_to_it(monkeypatch, tmp_path):
    base, started = tmp_path / "conda", []
    (base / "condabin").mkdir(parents=True)
    monkeypatch.setattr(Launcher, "find_base", lambda: base)
    monkeypatch.setattr(sys, "prefix", str(base / "envs" / "Quant"))
    monkeypatch.setattr(Launcher, "detach", lambda command: started.append(command))
    monkeypatch.setattr(Launcher, "upgrade", lambda base, environment: pytest.fail("Upgraded from inside the environment"))
    assert Launcher.launch() == 0
    assert started == [[str(base / Path(sys.executable).name), str(Path(Launcher.__file__).resolve())]]

def _launchable_(monkeypatch, tmp_path, *, upgrade, running: list = ()) -> tuple:
    base, events = tmp_path / "conda", []
    (base / "condabin").mkdir(parents=True)
    monkeypatch.setattr(Launcher, "find_base", lambda: base)
    monkeypatch.setattr(sys, "prefix", str(base))
    monkeypatch.setattr(Launcher, "upgrade", upgrade)
    monkeypatch.setattr(Launcher, "daemons", lambda environment: list(running))
    monkeypatch.setattr(Launcher, "settle", lambda probe, patience: events.append(("settle", patience)) or probe())
    monkeypatch.setattr(Launcher, "detach", lambda command: events.append(command))
    monkeypatch.setattr(Launcher, "journal", lambda message: events.append(message))
    return base, events

def test_a_launch_upgrades_first_then_starts_the_scheduler_from_the_environment(monkeypatch, tmp_path):
    base, events = _launchable_(monkeypatch, tmp_path, upgrade=lambda base, environment: "Current")
    assert Launcher.launch() == 0
    assert events == [("settle", 30.0), [str(base / "envs" / "Quant" / "pythonw.exe"), str(Path(Launcher.__file__).resolve()), "--daemon"], "Scheduler Launch: Started · Environment Current"]

def test_the_scheduler_starts_even_when_the_upgrade_step_breaks(monkeypatch, tmp_path):
    def _broken_(base, environment): raise RuntimeError("PowerShell unavailable")
    base, events = _launchable_(monkeypatch, tmp_path, upgrade=_broken_)
    assert Launcher.launch() == 0
    assert events[0] == "Environment Upgrade: Failed · PowerShell unavailable" and events[-1] == "Scheduler Launch: Started · Environment Failed"

def test_a_second_launch_never_starts_a_second_scheduler(monkeypatch, tmp_path):
    base, events = _launchable_(monkeypatch, tmp_path, upgrade=lambda base, environment: "Current", running=["pythonw.exe 4512"])
    assert Launcher.launch() == 0
    assert events == [("settle", 30.0), "Scheduler Launch: Skipped · Already Running · pythonw.exe 4512"]

def test_only_a_daemon_counts_as_a_running_scheduler(monkeypatch):
    environment = Path("C:/conda/envs/Quant")
    rows = [{"Name": "pythonw.exe", "ProcessId": 1, "ExecutablePath": "C:/conda/envs/Quant/pythonw.exe", "CommandLine": "pythonw.exe Script/Scheduler.py --daemon"},
            {"Name": "pythonw.exe", "ProcessId": 2, "ExecutablePath": "C:/conda/envs/Quant/pythonw.exe", "CommandLine": "pythonw.exe Script/Scheduler.py"},
            {"Name": "bash.exe", "ProcessId": 3, "ExecutablePath": "C:/Git/bin/bash.exe", "CommandLine": "bash -c 'grep Scheduler.py --daemon'"},
            {"Name": "System", "ProcessId": 4, "ExecutablePath": None, "CommandLine": None}]
    monkeypatch.setattr(Launcher, "processes", lambda: rows)
    assert Launcher.daemons(environment) == ["pythonw.exe 1"]

def test_the_base_is_the_conda_root_above_any_environment(monkeypatch, tmp_path):
    base = tmp_path / "conda"
    (base / "condabin").mkdir(parents=True)
    (base / "envs" / "Quant").mkdir(parents=True)
    monkeypatch.setattr(sys, "executable", str(base / "envs" / "Quant" / "pythonw.exe"))
    assert Launcher.find_base() == base.resolve()
    monkeypatch.setattr(sys, "executable", str(base / "pythonw.exe"))
    assert Launcher.find_base() == base.resolve()

def test_the_launcher_writes_its_log_beside_the_frameworks_logs(monkeypatch, tmp_path):
    written = []
    monkeypatch.setattr(Path, "open", lambda self, *args, **kwargs: written.append(self) or open(tmp_path / "Launcher.log", *args, **kwargs))
    monkeypatch.setattr(Path, "mkdir", lambda self, *args, **kwargs: None)
    Launcher.journal("Scheduler Launch: Started")
    assert written == [FileAPI.folder() / "Launcher.log"]