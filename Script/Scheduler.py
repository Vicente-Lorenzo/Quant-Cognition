import os
import sys
import json
import time
import shutil
import subprocess
import importlib.metadata as metadata
from pathlib import Path
from typing import Callable
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent

def find_base() -> Path:
    interpreter = Path(sys.executable).resolve()
    return next((folder for folder in (interpreter.parent, *interpreter.parents) if (folder / "condabin").is_dir()), interpreter.parent)

def find_environment(base: Path) -> Path:
    return base / "envs" / "Quant"

def sibling(environment: Path, suffix: str) -> Path:
    return environment.with_name(f"{environment.name}.{suffix}")

def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def journal(message: str) -> None:
    path = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / ROOT.name / "Temp" / "Logs" / "Launcher.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle: handle.write(f"{stamp()} - {message}\n")

def windowless() -> dict:
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}

def detach(command: list) -> subprocess.Popen:
    if os.name != "nt": return subprocess.Popen(command, cwd=str(ROOT))
    try: return subprocess.Popen(command, cwd=str(ROOT), creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_BREAKAWAY_FROM_JOB)
    except OSError: return subprocess.Popen(command, cwd=str(ROOT), creationflags=subprocess.CREATE_NO_WINDOW)

def execute(command: list, **kwargs) -> subprocess.CompletedProcess:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", **windowless(), **kwargs)
    if result.returncode:
        lines = [line.strip() for line in f"{result.stdout or ''}\n{result.stderr or ''}".splitlines() if line.strip()]
        errors = [line for line in lines if any(word in line.lower() for word in ("error", "critical", "failed"))]
        raise RuntimeError(" · ".join((errors or lines)[-3:]) or f"Exit {result.returncode}")
    return result

def manage(base: Path, arguments: list) -> subprocess.CompletedProcess:
    manager = next((path for path in (base / "Library" / "bin" / "mamba.exe", base / "Scripts" / "conda.exe") if path.is_file()), None)
    if manager is None: raise FileNotFoundError("Mamba or Conda executable not found")
    return execute([str(manager), *arguments], env={**os.environ, "CONDA_PREFIX": str(base), "MAMBA_ROOT_PREFIX": str(base)})

def processes() -> list:
    command = "Get-CimInstance Win32_Process | Select-Object ProcessId, Name, ExecutablePath, CommandLine | ConvertTo-Json -Compress"
    rows = json.loads(execute(["powershell", "-NoProfile", "-NonInteractive", "-Command", command]).stdout or "[]")
    return rows if isinstance(rows, list) else [rows]

def occupants(environment: Path) -> list:
    return [f"{row['Name']} {row['ProcessId']}" for row in processes() if row.get("ExecutablePath") and Path(row["ExecutablePath"]).is_relative_to(environment)]

def daemons(environment: Path) -> list:
    return [f"{row['Name']} {row['ProcessId']}" for row in processes() if row.get("ExecutablePath") and Path(row["ExecutablePath"]).is_relative_to(environment) and "Scheduler.py" in (row.get("CommandLine") or "") and "--daemon" in (row.get("CommandLine") or "")]

def settle(probe: Callable, patience: float) -> list:
    deadline = time.monotonic() + patience
    while (busy := probe()) and time.monotonic() < deadline: time.sleep(2)
    return busy

def remove(path: Path) -> bool:
    def _writable_(function, target, error):
        os.chmod(target, 0o700)
        function(target)
    if path.exists(): shutil.rmtree(path, onerror=_writable_)
    return not path.exists()

def locked(base: Path, successor: Path) -> Path:
    rows = json.loads(manage(base, ["list", "--prefix", str(successor), "--json"]).stdout)
    path = successor / "Upgrade.txt"
    path.write_text("@EXPLICIT\n" + "".join(f"{row['url']}#{row['md5']}\n" for row in rows if row["channel"] != "pypi"), encoding="utf-8")
    return path

def pinned(successor: Path) -> list:
    return sorted(f"{dist.metadata['Name']}=={dist.version}" for dist in metadata.distributions(path=[str(successor / "Lib" / "site-packages")]) if dist.metadata.get("Name") and (dist.read_text("INSTALLER") or "").strip() == "pip")

def restore(environment: Path, previous: Path) -> None:
    if environment.exists() and not remove(environment): os.rename(environment, sibling(environment, f"failed {stamp().replace(':', '-')}"))
    os.rename(previous, environment)

def swap(base: Path, environment: Path, successor: Path) -> None:
    specification, pins = locked(base, successor), pinned(successor)
    previous, retired = sibling(environment, "previous"), sibling(environment, f"retired {stamp().replace(':', '-')}")
    if previous.exists(): os.rename(previous, retired)
    try:
        os.rename(environment, previous)
        try:
            manage(base, ["create", "--prefix", str(environment), "--file", str(specification), "--yes"])
            if pins: execute([str(environment / "python.exe"), "-m", "pip", "install", "--no-deps", "--quiet", *pins])
            execute([str(environment / "python.exe"), "-c", "import Library.Scheduler.Tray, Library.Spotware, Library.System.Main, Library.Web.App"], cwd=ROOT)
        except Exception as error:
            restore(environment, previous)
            raise RuntimeError(f"Previous environment restored · {error}") from error
    except Exception:
        if retired.exists() and not previous.exists(): os.rename(retired, previous)
        raise
    remove(retired)

def read(marker: Path) -> dict:
    try: return json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {}

def write(marker: Path, state: dict) -> None:
    marker.write_text(json.dumps(state, indent=4), encoding="utf-8")

def upgrade(base: Path, environment: Path, patience: float = 60.0) -> str:
    marker = sibling(environment, "next") / "Upgrade.json"
    state = read(marker)
    if state.get("State") != "Validated": return "Current"
    busy = settle(lambda: occupants(environment), patience)
    if busy:
        journal(f"Environment Upgrade: Deferred · {len(busy)} Processes run from the environment · {' · '.join(busy)}")
        return "Deferred"
    clock = time.monotonic()
    try:
        swap(base, environment, marker.parent)
        write(marker, {**state, "State": "Applied", "Applied": stamp(), "Reported": False})
        journal(f"Environment Upgrade: Applied · {len(state.get('Moved', []))} Moved · {time.monotonic() - clock:.0f}s")
        return "Applied"
    except Exception as error:
        write(marker, {**state, "State": "Restored", "Reason": str(error), "Applied": stamp(), "Reported": False})
        journal(f"Environment Upgrade: Failed · {error}")
        return "Restored"

def daemon() -> int:
    sys.path.insert(0, str(ROOT))
    from Library.Logging import LoggingAPI
    from Library.Scheduler.Scheduler import SchedulerAPI
    from Library.Scheduler.Tray import TrayAPI
    if sys.stdout is None or sys.stderr is None: TrayAPI.redirect(TrayAPI._LOG_)
    return TrayAPI.main(LoggingAPI(), lambda: SchedulerAPI().start())

def launch() -> int:
    base = find_base()
    if Path(sys.prefix).resolve() != base.resolve():
        detach([str(base / Path(sys.executable).name), str(Path(__file__).resolve())])
        return 0
    environment = find_environment(base)
    try: outcome = upgrade(base, environment)
    except Exception as error:
        outcome = "Failed"
        journal(f"Environment Upgrade: Failed · {error}")
    try: running = settle(lambda: daemons(environment), 30.0)
    except Exception: running = []
    if running:
        journal(f"Scheduler Launch: Skipped · Already Running · {' · '.join(running)}")
        return 0
    detach([str(environment / "pythonw.exe"), str(Path(__file__).resolve()), "--daemon"])
    journal(f"Scheduler Launch: Started · Environment {outcome}")
    return 0

def main() -> int:
    return daemon() if "--daemon" in sys.argv else launch()

if __name__ == "__main__":
    raise SystemExit(main())