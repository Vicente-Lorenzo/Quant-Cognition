import os
import re
import sys
import json
import subprocess
from pathlib import Path
from typing import Callable, Union

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Logging import LoggingAPI
from Library.Utility.Datetime import INSTANT, utc_now
from Library.Utility.IO import read_json, read_yaml, remove, write_json
from Library.Utility.Path import traceback_root
from Library.Utility.Runtime import windowless
from Script.Task import attempt

def find_manifest() -> Path:
    return traceback_root() / "Quant.yml"

def find_root() -> Path:
    interpreter = Path(sys.executable).resolve()
    return interpreter.parents[2] if (interpreter.parents[2] / "condabin").is_dir() else interpreter.parent

def find_environment() -> Path:
    return find_root() / "envs" / "Quant"

def sibling(environment: Path, suffix: str) -> Path:
    return environment.with_name(f"{environment.name}.{suffix}")

def find_managers() -> list:
    root = find_root()
    folders = (root / "Scripts", root / "Library" / "bin")
    found = [os.environ.get("MAMBA_EXE")] + [str(path) for folder in folders if (path := folder / "mamba.exe").is_file()]
    found += [os.environ.get("CONDA_EXE")] + [str(path) for folder in folders if (path := folder / "conda.exe").is_file()]
    found += ["mamba", "conda"]
    return list(dict.fromkeys(name for name in found if name))

def run_manager(arguments: list, accept: Union[Callable, None] = None, **kwargs) -> subprocess.CompletedProcess:
    environment = {**os.environ, "MAMBA_ROOT_PREFIX": str(find_root())}
    for manager in find_managers():
        try: result = subprocess.run([manager, *arguments], env=environment, **windowless(), **kwargs)
        except FileNotFoundError: continue
        if accept is None or accept(result): return result
    raise FileNotFoundError("Mamba or Conda executable not found")

def canonical(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")

def tail(result: subprocess.CompletedProcess) -> str:
    lines = [line.strip() for line in f"{result.stdout or ''}\n{result.stderr or ''}".splitlines() if line.strip()]
    errors = [line for line in lines if re.search(r"error|critical|failed", line, re.IGNORECASE)]
    return " · ".join((errors or lines)[-3:]) or f"Exit {result.returncode}"

def execute(command: list, **kwargs) -> subprocess.CompletedProcess:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", **windowless(), **kwargs)
    if result.returncode: raise RuntimeError(tail(result))
    return result

def manage(arguments: list, **kwargs) -> subprocess.CompletedProcess:
    result = run_manager(arguments, capture_output=True, text=True, encoding="utf-8", errors="replace", **kwargs)
    if result.returncode: raise RuntimeError(tail(result))
    return result

def listing(prefix: Path) -> list:
    return json.loads(manage(["list", "--prefix", str(prefix), "--json"]).stdout)

def versions(rows: list) -> dict:
    return {canonical(row["name"]): row["version"] for row in rows}

def declared(manifest: Path) -> tuple:
    entries = read_yaml(manifest).get("dependencies", [])
    conda = [canonical(re.split(r"[=<>!~\s]", entry, maxsplit=1)[0]) for entry in entries if isinstance(entry, str)]
    pip = [item for entry in entries if isinstance(entry, dict) for item in entry.get("pip", []) if not str(item).startswith("-")]
    return conda, pip

def stale(prefix: Path, manifest: Path) -> bool:
    conda, pip = declared(manifest)
    if set(conda) - set(versions(listing(prefix))): return True
    if (json.loads(manage(["update", "--prefix", str(prefix), "--all", "--dry-run", "--json"]).stdout).get("actions") or {}).get("LINK"): return True
    return bool(pip) and bool(json.loads(execute([str(prefix / "python.exe"), "-m", "pip", "install", "--upgrade", "--dry-run", "--quiet", "--report", "-", *pip]).stdout)["install"])

def moved(before: dict, after: dict) -> list:
    return [f"{name} {before.get(name, '-')} → {after.get(name, '-')}" for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)]

def summary(output: str) -> str:
    found = re.findall(r"^(\d+ (?:passed|failed|errors?)\b.*)$", output, re.MULTILINE)
    return found[-1].strip() if found else "No Summary"

def discard(prefix: Path) -> None:
    if not prefix.exists(): return
    run_manager(["env", "remove", "--prefix", str(prefix), "--yes"], capture_output=True)
    remove(prefix, safe=False)

def build(successor: Path, manifest: Path) -> None:
    manage(["env", "create", "--prefix", str(successor), "--file", str(manifest), "--yes"])

def verify(successor: Path) -> str:
    result = run_manager(["run", "--prefix", str(successor), "python", "-m", "pytest", "Tests/", "--ignore=Tests/Bloomberg", "-q", "-p", "no:cacheprovider"], cwd=traceback_root(), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode: raise RuntimeError(f"Tests failed on {successor.name} · {summary(result.stdout)}")
    return summary(result.stdout)

def marker(environment: Path) -> Path:
    return sibling(environment, "next") / "Upgrade.json"

def record(environment: Path, state: dict) -> None:
    write_json(marker(environment), {**state, "Built": utc_now().strftime(INSTANT)}, safe=False)

def report(log, environment: Path) -> None:
    state = read_json(marker(environment)) or {}
    if state.get("State") not in ("Applied", "Restored") or state.get("Reported") is not False: return
    if state["State"] == "Applied": log.warning(lambda: f"Environment Upgrade: Applied · {len(state.get('Moved', []))} Moved · {state.get('Applied')}")
    else: log.error(lambda: f"Environment Upgrade: Failed · {state.get('Reason')}")
    write_json(marker(environment), {**state, "Reported": True}, safe=False)

def describe(environment: Path) -> str:
    state, previous = read_json(marker(environment)) or {}, sibling(environment, "previous")
    upcoming = f"{state['State']} ({len(state.get('Moved', []))} Moved)" if state.get("State") else "None"
    return f"Environment State: Current {environment.name} · Next {upcoming} · Previous {'Kept' if previous.exists() else 'None'}"

def update_environment(log) -> str:
    environment, manifest = find_environment(), find_manifest()
    successor = sibling(environment, "next")
    report(log, environment)
    pending = (read_json(marker(environment)) or {}).get("State") == "Validated"
    try:
        if not stale(successor if pending else environment, manifest): return "Validated · Applied at the next logon" if pending else "Current"
        discard(successor)
        build(successor, manifest)
        changes = moved(versions(listing(environment)), versions(listing(successor)))
        if not changes:
            record(environment, {"State": "Current"})
            return "Current"
        for change in changes: log.warning(lambda change=change: f"Environment Upgrade: Pending · {change}")
        try: outcome = verify(successor)
        except RuntimeError as error:
            record(environment, {"State": "Failed", "Moved": changes, "Summary": str(error)})
            raise
        record(environment, {"State": "Validated", "Moved": changes, "Summary": outcome})
        log.warning(lambda: f"Environment Upgrade: Validated · {len(changes)} Moved · {outcome} · Applied at the next logon")
        return f"Validated · {len(changes)} Moved"
    finally:
        print(describe(environment), flush=True)

def main():
    with LoggingAPI() as log:
        return attempt(log, "Environment", lambda: update_environment(log), detail=find_manifest().name)

if __name__ == "__main__":
    raise SystemExit(main())