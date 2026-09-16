import os
import sys
import subprocess
from pathlib import Path
from typing import Callable, Union

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Logging import LoggingAPI
from Library.Utility.Path import traceback_root
from Library.Utility.Runtime import windowless
from Setup.Task import attempt

def find_manifest() -> Path:
    return traceback_root() / "Quant.yml"

def find_root() -> Path:
    interpreter = Path(sys.executable).resolve()
    return interpreter.parents[2] if (interpreter.parents[2] / "condabin").is_dir() else interpreter.parent

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

def update_environment():
    return run_manager(["env", "update", "--name", "Quant", "--file", str(find_manifest()), "--prune"], check=True, stdout=sys.stdout, stderr=sys.stderr)

def main():
    with LoggingAPI() as log:
        return attempt(log, "Environment", update_environment, detail=find_manifest().name)

if __name__ == "__main__":
    raise SystemExit(main())